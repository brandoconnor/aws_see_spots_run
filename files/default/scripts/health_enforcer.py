#!/usr/bin/env python

import argparse
import boto
import sys
import time
from AWS_see_spots_run_common import *
from boto import ec2
from boto.ec2 import autoscale, elb
from boto.exception import BotoServerError, EC2ResponseError
from boto.ec2.autoscale import LaunchConfiguration
from math import ceil

def main(args):
    global verbose
    global dry_run
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    for region in [ r.name for r in boto.ec2.regions() if r.name not in args.excluded_regions ]:
        try:
            print_verbose('Starting pass on %s' % region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)
            as_groups = get_SSR_groups(as_conn)
            minutes_multiplier = 60
            for as_group in as_groups:
                as_group = reload_as_group(as_group)
                print_verbose("Checking %s" % as_group.name)
                demand_expiration = get_tag_dict_value(as_group, 'SSR_config')['demand_expiration']
                healthy_zones = get_healthy_zones(as_group, args.min_health_threshold )
                if demand_expiration != False:
                    if demand_expiration < int(time.time()):
                        if len(healthy_zones) >= get_min_AZs(as_group):
                            print_verbose('Woot! We can move back to spots at original bid price.')
                            modify_as_group_AZs(as_group, healthy_zones)
                            modify_price(as_group, get_tag_dict_value(as_group, 'SSR_config')['original_bid'])
                            set_tag_dict_value(as_group, 'SSR_config', 'demand_expiration', False)
                            # kill all demand instances that were created
                            ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
                            all_ec2_instances = ec2_conn.get_all_instances()
                            print_verbose("Looking at %s instances for potential termination", len(as_group.instances))
                            for instance in as_group.instances:
                                if not [ i for i in all_ec2_instances if i.instances[0].id == instance.instance_id ][0].instances[0].spot_instance_request_id and not dry_run:
                                    as_conn.terminate_instance(instance.instance_id, decrement_capacity=False)
                        else:
                            print_verbose('Extending the life of demand instances as we cant fulfill with spots still')
                            set_tag_dict_value(as_group, 'SSR_config', 'demand_expiration', int(time.time()) + (args.demand_expiration * minutes_multiplier))
                
                elif sorted(as_group.availability_zones) != sorted(healthy_zones):
                    as_group = reload_as_group(as_group)
                    print_verbose("Healthy zones and zones in use dont match")
                    if len(healthy_zones) >= get_min_AZs(as_group):
                        print_verbose('Modifying zones accordingly.')
                        modify_as_group_AZs(as_group, healthy_zones)
                    
                    else:
                        print_verbose("Bid will need to be modified as we can't meet AZ minimum of %s" % str(get_min_AZs(as_group)))
                        best_bid = find_best_bid_price(as_group)
                        print_verbose("Best possible bid given AZ minimum is %s" % str(best_bid))
                        if best_bid:
                            modify_price(as_group, best_bid)
                        else:
                            print_verbose("Moving to ondemand.")
                            modify_price(as_group, None, minutes_multiplier, args.demand_expiration)
                            set_tag_dict_value(as_group, 'SSR_config', 'demand_expiration', int(time.time()) + (args.demand_expiration * minutes_multiplier))
                            modify_as_group_AZs(as_group, get_usable_zones(as_group))
                else:
                    print_verbose('No actions to take on this ASG.')
            print_verbose('Done with pass on %s' % region)


        except EC2ResponseError as e:
            handle_exception(e)

        except Exception as e:
            handle_exception(e)
            return 1

    print_verbose("All regions complete")


def get_min_AZs(as_group):
    return int(get_tag_dict_value(as_group, 'SSR_config')['min_AZs'])


def get_rounded_price(price):
    return ceil(price * 100) / 100.0


def find_best_bid_price(as_group):
    try:
        prices = get_current_spot_prices(as_group)
        print_verbose(prices) #XXX still working through some issues here
        if len(prices) != len(get_usable_zones(as_group)):
            raise Exception ("Different number of AZs found than expected. Prices = %s\nAZs = %s" % (str(prices), str(get_usable_zones(as_group))))
        best_bid = sorted(prices, key=lambda price: price.price)[int(get_min_AZs(as_group)) - 1].price #XXX this approach is potentially flawed
        print_verbose('best_bid=', best_bid)
        max_bid = get_max_bid(as_group)
        print_verbose('best_bid=', best_bid)
        if get_rounded_price(best_bid) >= get_rounded_price(max_bid):
            return False # since ondemand instances are faster to spin up and more available, if demand and max_bid are equal, ondemand wins out.
        else:
            return get_rounded_price(best_bid)
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_max_bid(as_group):
    try:
        demand_price = get_ondemand_price(get_launch_config(as_group))
        original_bid = get_tag_dict_value(as_group, 'SSR_config')['original_bid']
        if get_rounded_price(demand_price) <= get_rounded_price(original_bid):
            return original_bid
        else:
            return demand_price
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_healthy_zones(as_group, min_health_threshold):
    AZ_status = get_tag_dict_value(as_group, 'AZ_status')
    zone_prefix = as_group.availability_zones[0][:-1]
    return [ zone_prefix + t for t in AZ_status if AZ_status[t]['use'] and AZ_status[t]['health'].count(0) >= min_health_threshold ]


def get_usable_zones(as_group):
    AZ_status = get_tag_dict_value(as_group, 'AZ_status')
    zone_prefix = as_group.availability_zones[0][:-1]
    return [ zone_prefix + t for t in AZ_status if AZ_status[t]['use'] ]


def modify_price(as_group, new_bid, minutes_multiplier=None, demand_expiration=None):
    try:
        as_group = reload_as_group(as_group)
        as_conn = boto.ec2.autoscale.connect_to_region(as_group.connection.region.name)
        old_launch_config = get_launch_config(as_group)
        new_launch_config_name = old_launch_config.name[:-12] + 'SSR' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(9))
        
        launch_config = LaunchConfiguration(
            image_id = old_launch_config.image_id,
            key_name = old_launch_config.key_name,
            security_groups = old_launch_config.security_groups,
            user_data = old_launch_config.user_data,
            instance_type = old_launch_config.instance_type,
            kernel_id = old_launch_config.kernel_id,
            ramdisk_id = old_launch_config.ramdisk_id,
            block_device_mappings = old_launch_config.block_device_mappings,
            instance_monitoring = old_launch_config.instance_monitoring.enabled,
            instance_profile_name = old_launch_config.instance_profile_name,
            ebs_optimized = old_launch_config.ebs_optimized,
            associate_public_ip_address = old_launch_config.associate_public_ip_address,
            volume_type = old_launch_config.volume_type,
            delete_on_termination = old_launch_config.delete_on_termination,
            iops = old_launch_config.iops,
            use_block_device_types = old_launch_config.use_block_device_types,
            spot_price = new_bid, # new values
            name = new_launch_config_name,
            )

        new_launch_config = as_conn.create_launch_configuration(launch_config)
        print_verbose("Created LC %s with price %s." % (launch_config.name, new_bid))
        as_groups = [ a for a in as_group.connection.get_all_groups() if old_launch_config.name == a.launch_config_name ]
        for as_group in as_groups:
            as_group.launch_config_name = launch_config.name
            if not dry_run:
                print_verbose("Applying new LC to ASG %s" % as_group.name)
                as_group.update()
                set_tag_dict_value(as_group, 'SSR_config', 'LC_name', launch_config.name[-155:])
                if not new_bid:
                    set_tag_dict_value(as_group, 'SSR_config', 'demand_expiration', int(time.time()) + (demand_expiration * minutes_multiplier ))
                    modify_as_group_AZs(as_group, get_usable_zones(as_group))

        print_verbose("Autoscaling group launch configuration update complete.")
        old_launch_config.delete()

    except Exception as e:
        handle_exception(e)
        sys.exit(1)   


def match_AZs_on_elbs(as_group):
    try:
        elb_conn = boto.ec2.elb.connect_to_region(as_group.connection.region.name)
        for elb_name in as_group.load_balancers:
            elb = elb_conn.get_all_load_balancers(elb_name)[0]
            if not sorted(elb.availability_zones) == sorted(as_group.availability_zones):
                print_verbose("AZs for ELB don't match that of the as_group. Aligning them now.")
                if not dry_run:
                    elb.enable_zones(as_group.availability_zones)

    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def modify_as_group_AZs(as_group, healthy_zones):
    try:
        as_group = reload_as_group(as_group)
        as_group.availability_zones = healthy_zones
        print_verbose("Updating with AZs %s" % healthy_zones)
        if not dry_run:
            as_group.update()
            if as_group.load_balancers:
                match_AZs_on_elbs(as_group)

    except BotoServerError as e:
        if e.error_code == 'Throttling':
            print_verbose('Pausing for AWS throttling...')
            sleep(1)
        modify_as_group_AZs(as_group, healthy_zones)   
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_ondemand_price(launch_config):
    try:
        region = launch_config.connection.region.name
        ec2_conn = boto.ec2.connect_to_region(region)
        image = ec2_conn.get_image(launch_config.image_id)

        url = get_price_url(launch_config)
        resp = requests.get(url)
        json_str = str(resp.text.split('callback(')[1])[:-2] # need to remove comments and callback syntax before parsing the broken json
        prices_dict = demjson.decode(json_str)['config']['regions']

        regional_prices_json = [ r for r in prices_dict if r['region'] == region ][0]['instanceTypes']
        instance_class_prices_json = [ r for r in regional_prices_json if launch_config.instance_type in [ e['size'] for e in r['sizes'] ] ][0]['sizes']
        price = float([ e for e in instance_class_prices_json if e['size'] == launch_config.instance_type ][0]['valueColumns'][0]['prices']['USD'])
        print_verbose("On demand price for %s in %s is %s" % (launch_config.instance_type, region, price))
        return price

    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_price_url(launch_config):
    # nabbed URL list from https://github.com/iconara/ec2pricing/blob/master/public/app/ec2pricing/config.js
    base_url = 'http://a0.awsstatic.com/pricing/1/ec2/'

    previous_gen_types = ['m1', 'm2', 'c2', 'cc2', 'cg1', 'cr1', 'hi1']
    if launch_config.instance_type.split('.')[0] in previous_gen_types:
        base_url += 'previous-generation/'

    ec2_conn = boto.ec2.connect_to_region(launch_config.connection.region.name)
    image = ec2_conn.get_image(launch_config.image_id)

    if image.platform == 'windows':
        base_url += 'mswin'
    elif 'SUSE Linux Enterprise Server' in image.description:
        base_url += 'sles'
    else:
        base_url += 'linux'
    url = base_url + '-od.min.js'
    return url


def reload_as_group(as_group):
    try:
        return as_group.connection.get_all_groups([as_group.name])[0]

    except BotoServerError as e:
        if e.error_code == 'Throttling':
            print_verbose('Pausing for AWS throttling...')
            sleep(1)
            return reload_as_group(as_group)

    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def set_tag_dict_value(as_group, tag_key, val_key, value):
    as_group = reload_as_group(as_group)
    tag_val = get_tag_dict_value(as_group, tag_key)
    tag_val[val_key] = value
    create_tag(as_group, tag_key, tag_val)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    parser.add_argument('-e', '--excluded_regions', default=['cn-north-1', 'us-gov-west-1'], nargs='*', type=str, help='Space separated AWS regions to exclude. Default= cn-north-1 us-gov-west-1')
    parser.add_argument('-m', '--min_health_threshold', default=3, type=int, choices=[1,2,3], help='Minimum number of good (0) checks against an AZ before its considered healthy. Default=3')
    parser.add_argument('-x', '--demand_expiration', default=50, type=int, help='Length of time in minutes we should let an ASG operate with on demand before checking for spot availability. Default=50')
    sys.exit(main(parser.parse_args()))

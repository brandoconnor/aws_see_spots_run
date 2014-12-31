#!/usr/bin/env python
# health_enforcer.py
#XXX implement dry_run and verbose stuffs

import argparse
import boto
import sys
import time
from AWS_see_spots_run_common import *
from boto import ec2
from boto.ec2 import autoscale, elb
from boto.exception import BotoServerError, EC2ResponseError
from boto.ec2.autoscale import LaunchConfiguration

def main(args):
    global verbose
    global dry_run
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    for region in [ r.name for r in boto.ec2.regions() if r.name not in args.excluded_regions ]:
        try:
            print_verbose('Starting pass on %s' % region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)
            as_groups = get_SSR_groups(as_conn)
            for as_group in as_groups:
                print_verbose("Checking %s" % as_group.name)
                demand_expiration = get_tag_dict_value(as_group, 'SSR_config')['demand_expiration']
                zone_prefix = as_group.availability_zones[0][:-1]
                healthy_zones = [ zone_prefix + a for a in get_healthy_zones(as_group) ]
                if demand_expiration != 0:
                    if demand_expiration < int(time.time()):
                        if len(viable_zones) >= args.min_healthy_AZs:
                            print_verbose('Woot! We can move back to spots at original bid price.')
                            modify_as_group_AZs(as_group, healthy_zones)
                            modify_price(as_group, get_tag_dict_value(as_group, 'SSR_config')['original_bid'])
                            set_tag_dictionary_value(as_group, 'SSR_config', 'demand_expiration', False)
                            # kill all demand instances that were created
                            ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
                            all_ec2_instances = ec2_conn.get_all_instances()
                            print_verbose("Looking at %s instances for potential termination", len(as_group.instances))
                            for instance in as_group.instances:
                                if not [ i for i in all_ec2_instances if i.instances[0].id == instance.instance_id ][0].instances[0].spot_instance_request_id and not dry_run:
                                    as_conn.terminate_instance(instance.instance_id, decrement_capacity=False)
                    else:
                        print_verbose('extending the life of demand instances as we cant fulfill with spots still')
                        set_tag_dictionary_value(as_group, 'SSR_config', 'demand_expiration', int(time.time()) + (args.demand_expiration * 60) )
                
                as_group = reload_as_group(as_group)
                if not sorted(as_group.availability_zones) == sorted(healthy_zones):
                    print_verbose("Healthy zones and zones in use dont match", healthy_zones, '!=', as_group.availability_zones)
                    if len(healthy_zones) >= args.min_healthy_AZs:
                        print_verbose('Modifying zones accordingly.')
                        modify_as_group_AZs(as_group, healthy_zones)
                    else:
                        print_verbose('Bid will need to be modified')
                        best_bid = find_best_bid_price(as_group, args.min_healthy_AZs)
                        print_verbose("best bid possible given AZ minimum is", best_bid)
                        if best_bid:
                            modify_price(as_group, best_bid)
                        else:
                            print_verbose("Moving to ondemand.")
                            modify_price(as_group, None) # maybe an empty string needed instead
                            set_tag_dictionary_value(as_group, 'SSR_config', 'demand_expiration', int(time.time()) + (args.demand_expiration * 60))
                            # allow all usable AZs in both as_group and ELB
                            modify_as_group_AZs(as_group, get_usable_zones(as_group))
                else:
                    print_verbose('No further actions to take.')
            print_verbose('Done with pass on %s' % region)


        except EC2ResponseError as e:
            handle_exception(e)

        except Exception as e:
            handle_exception(e)
            return 1

    print_verbose("All regions complete")


def reload_as_group(as_group):
    return as_group.connection.get_all_groups([as_group.name])[0]


def find_best_bid_price(as_group, min_healthy_AZs):
    try:
        prices = get_current_spot_prices(as_group)
        best_bid = sorted(prices, key=lambda price: price.price)[min_healthy_AZs - 1].price
        max_bid = get_max_bid(as_group)
        if float(best_bid) > float(max_bid):
            return False
        else:
            return best_bid
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_max_bid(as_group):
    try:
        demand_price = get_ondemand_price(get_launch_config(as_group))
        original_bid = get_tag_dict_value(as_group, 'SSR_config')['original_bid']
        if float(demand_price) < float(original_bid):
            return original_bid
        else:
            return demand_price
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_healthy_zones(as_group):
    AZ_status = get_tag_dict_value(as_group, 'AZ_status')
    return [ t for t in AZ_status if AZ_status[t]['use'] and AZ_status[t]['health'].count(0) >= 2 ]


def get_usable_zones(as_group):
    AZ_status = get_tag_dict_value(as_group, 'AZ_status')
    return [ t for t in AZ_status if AZ_status[t]['use'] ]


def set_tag_dictionary_value(as_group, tag_key, val_key, value):
    tag_val = get_tag_dict_value(as_group, tag_key)
    tag_val[val_key] = value
    create_tag(as_group, tag_key, val_key)


def modify_price(as_group, new_bid):
    try:
        as_conn = boto.ec2.autoscale.connect_to_region(as_group.connection.region.name)
        old_launch_config = get_launch_config(as_group)
        new_launch_config_name = old_launch_config.name[:-13] + 'SSR' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

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
        as_groups = [ a for a in as_group.connection.get_all_groups() if old_launch_config.name == a.launch_config_name ]
        for as_group in as_groups:
            #setattr(as_group, launch_config_name, launch_config.name)
            print(as_group)
            as_group.launch_config_name = launch_config.name
            if not dry_run:
                print_verbose("Created LC %s with price %s and applying to ASG %s" %
                        (launch_config.name , new_bid, as_group.name))
                as_group.update()
            else:
                print_verbose("Created LC %s with price %s but NOT applying to ASG %s" %
                        (launch_config.name , new_bid, as_group.name))

        print_verbose("Autoscaling group launch configuration update complete.")
        old_launch_config.delete()

    except EC2ResponseError as e:
        handle_exception(e)

    except BotoServerError as e:
        handle_exception(e)

    except Exception as e:
        handle_exception(e)
        return 1


def match_AZs_on_elbs(as_group):
    try:
        elb_conn = boto.ec2.elb.connect_to_region(as_group.connection.region.name)
        for elb_name in as_group.load_balancers:
            elb = elb_conn.get_all_load_balancers(elb_name)[0]
            if not elb.availability_zones == as_group.availability_zones:
                print_verbose("AZs for ELB don't match that of the as_group. Aligning them now.")
                if not dry_run:
                    elb.enable_zones(as_group.availability_zones)

    except Exception as e:
        handle_exception(e)
        return 1


def modify_as_group_AZs(as_group, healthy_zones):
    try:
        as_group.availability_zones = healthy_zones
        print_verbose("Updating %s with AZs %s" % (as_group.name, healthy_zones))
        if not dry_run:
            as_group.update()
            if as_group.load_balancers:
                match_AZs_on_elbs(as_group)

    except Exception as e:
        handle_exception(e)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    parser.add_argument('-e', '--excluded_regions', default=['cn-north-1', 'us-gov-west-1'], nargs='*', type=str, help='Space separated AWS regions to exclude. Default= cn-north-1 us-gov-west-1')
    parser.add_argument('-m', '--min_healthy_AZs', default=3, type=int, help="Minimum default number of AZs before alternative launch approaches are tried. Default=3")
    parser.add_argument('-x', '--demand_expiration', default=50, type=int, help='Length of time in minutes we should let an ASG operate with on demand before checking for spot availability. Default=50')
    sys.exit(main(parser.parse_args()))

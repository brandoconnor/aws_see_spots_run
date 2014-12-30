#!/usr/bin/env python3
# health_enforcer.py
#
import argparse
import boto
import sys
import time
from boto import ec2
from boto.ec2 import autoscale
from AWS_see_spots_run_common import *
from boto.exception import BotoServerError, EC2ResponseError

#TODO: write code to determine if any 1 or 2 AZs with high prices can be nixed
# this script should either do some tagging or initialize the tagging scripts on certain conditions

def main(args):
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    for region in [ r.name for r in boto.ec2.regions() if r.name not in args.excluded_regions ]:
        try:
            print_verbose('Starting pass on %s' % region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)
            as_groups = get_SSR_groups(as_conn)
            for as_group in as_groups:
                demand_expiration = get_tag_dict_value(as_group, 'SSR_config')['demand_expiration']
                if demand_expiration != 0:
                    if demand_expiration < int(time.time()):
                        #XXX should probably get these from tags instead
                        viable_zones = [ p.availability_zones for p in get_current_spot_prices(as_group) if p.price * 1.1 < get_tag_dict_value(as_group, 'SSR_config')['original_bid'] ]
                        if len(viable_zones) >= min_healthy_AZs:
                            # DO IT! move back to spots using original_price on the LC for AZs in viable_zones
                            
                            # then
                            set_tag_dictionary_value(as_group, 'SSR_config', 'demand_expiration', False)
                            # call price_monitor
                        else:
                            set_tag_dictionary_value(as_group, 'SSR_config', 'demand_expiration', int(time.time()) + (args.demand_expiration * 60) )
                AZ_status = get_tag_dict_value(as_group, 'AZ_status')

                good_AZs =  [ t for t in AZ_status if AZ_status[t]['use'] and AZ_status[t]['health'].count(0) >= 2 ] ]
                # another direction
                # can we match this set of good AZs to ELB and AZ (is len(good_AZs better than or equal to AZ_min))
                ## yes: do it and be done
                ## no: find a bid price that will work for AZ min under ondemand
                
                # test: does this ASG have any bad AZs?
                ## yes: can we remove bad AZ(s) wihtout violating min AZ rule?
                ### yes: remove AZ(s) and continue
                ### no: find bid price that will work for AZ min while also under ondemand
                #### price found: raise price, set AZs to use and give a price check heartbeat.
                #### no price found: move to ondemand, set a tag within the config with epoch for check to kill these



            print_verbose('Done with pass on %s' % region)


        except EC2ResponseError as e:
            handle_exception(e)
            pass

        except Exception as e:
            handle_exception(e)
            return 1



def set_tag_dictionary_value(as_group, tag_key, val_key, value):
    tag_val = get_tag_dict_value(as_group, tag_key)
    tag_val[val_key] = value
    create_tag(as_group, tag_key, val_key)


def modify_price(as_group, new_bid):
    try:
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
        pass

    except BotoServerError as e:
        handle_exception(e)
        pass

    except:
        handle_exception(e)
        return 1


def match_AZs_on_elbs(as_group):
    try:
        elb_conn = boto.ec2.elb.connect_to_region(as_group.connection.region.name)
        for elb_name in as_group.load_balancers:
            elb = elb_conn.get_all_load_balancers(elb_name)
            if not elb.availability_zones == as_group.availability_zones:
                print_verbose("AZs for ELB don't match that of the as_group. Aligning them now.")
                if not dry_run:
                    elb.enable_zones(as_group.availability_zones)

    except Exception as e:
        handle_exception(e)
        return 1


def modify_as_group_AZs(as_group, good_AZs):
    try:
        as_group.availability_zones = good_AZs
        print_verbose("Updating %s with AZs %s" % (as_group.name, good_AZs))
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
    parser.add_argument('-m', '--min_healthy_AZs', default=3, help="Minimum default number of AZs before alternative launch approaches are tried. Default=3")
    parser.add_argument('-e', '--excluded_regions', default=['cn-north-1', 'us-gov-west-1'], nargs='*', type=str, help='Space separated AWS regions to exclude. Default= cn-north-1 us-gov-west-1')
    parser.add_argument('-x', '--demand_expiration', default=50, type=int, help='Length of time in minutes we should let an ASG operate with on demand before checking for spot availability. Default=50)
    sys.exit(main(parser.parse_args()))

#!/usr/bin/env python
'''
Tagger runs on a periodic basis to tag autoscaling groups, providing the persistence
needed for spot management.

All values aside from AZ_status should be a set just once. If a user wants to
override a tag value, that will be honored and not overridden by SSR.
'''
import argparse
import ast
import boto
import sys
import time
from AWS_see_spots_run_common import *
from boto import ec2
from boto.ec2 import autoscale
from boto.ec2.autoscale import Tag
from boto.exception import BotoServerError, EC2ResponseError


def main(args):
    global verbose
    global dry_run
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    for region in [ r.name for r in boto.ec2.regions() if r.name not in args.excluded_regions ]:
        try:
            print_verbose('Starting pass on %s' % region)
            ec2_conn = boto.ec2.connect_to_region(region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)
            all_groups = as_conn.get_all_groups()
            spot_LCs = [ e for e in as_conn.get_all_launch_configurations() if e.spot_price ]
            SSR_managed_demand_groups = [ g for g in all_groups if get_tag_dict_value(g, 'SSR_config') and get_tag_dict_value(g, 'SSR_config')['demand_expiration'] != False ]
            spot_LC_groups = [ g for g in as_conn.get_all_groups() if g.launch_config_name in [ s.name for s in spot_LCs ] ]
            all_groups = spot_LC_groups + SSR_managed_demand_groups
            for as_group in all_groups:
                print_verbose("Evaluating %s" % as_group.name)
                # this latter condition happens if for whatever reason the tag value (a dict) can't be interpreted by ast.literal_eval()
                if not [ t for t in as_group.tags if t.key == 'SSR_config' ] or not get_tag_dict_value(as_group, 'SSR_config'):
                    print_verbose('Tags not found. Applying now.')
                    init_as_group_tags(as_group, args.min_healthy_AZs)

                elif [ t for t in as_group.tags if t.key == 'SSR_config' and not get_tag_dict_value(as_group, 'SSR_config')['enabled'] ]:
                    print_verbose('SSR_config not enabled.')

                elif [ t for t in as_group.tags if t.key == 'SSR_config' and get_tag_dict_value(as_group, 'SSR_config')['enabled'] ]:
                    print_verbose('SSR management enabled. Verifying all config values in place.')
                    config_keys = ['enabled', 'original_bid', 'LC_name', 'min_AZs', 'demand_expiration', ] #NOTE: add a false entry here to start afresh with SSR tags

                    # Checking 2 things here:
                    ## 1. all config keys exist: they could change (keys added) and in some cases during dev, it's helpful to create them afresh
                    ## 2. if launch config name changed for the group this indicates an update of the LC via cloudformation and the SSR_config tag should be reset
                    if not verify_tag_dict_keys(as_group, 'SSR_config', config_keys) or not get_tag_dict_value(as_group, 'SSR_config')['LC_name'] == as_group.launch_config_name[-155:]:
                        init_as_group_tags(as_group, args.min_healthy_AZs)

                    zones = [ z.name[-1] for z in ec2_conn.get_all_zones() ]
                    if not verify_tag_dict_keys(as_group, 'AZ_status', zones):
                        init_AZ_status(as_group)
                else:
                    raise Exception("SSR_enabled tag found for %s but isn't a valid value." % (as_group.name,))

            print_verbose('Done with pass on %s' % region)

        except EC2ResponseError as e:
            handle_exception(e)

        except BotoServerError as e:
            handle_exception(e)

        except Exception as e:
            handle_exception(e)
            return 1

    print_verbose("All regions complete")


def init_as_group_tags(as_group, min_healthy_AZs):
    try:
        config = get_launch_config(as_group)
        init_AZ_status(as_group) #XXX needed?
        config_dict = {
                'enabled': True,
                'original_bid': get_bid(as_group), #XXX will this work when LC_name changes due to CFN change?
                'min_AZs': min_healthy_AZs,
                'LC_name': as_group.launch_config_name[-155:], # LC name size can be up to 255 chars (also tag value max length). Final chars should be unique so we cut this short
                "demand_expiration": False, #XXX this cannot change if LCs change due to shift to ondemand. Possibly create a function
                }
        create_tag(as_group, 'SSR_config', config_dict)
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def init_AZ_status(as_group):
    try:
        potential_zones = get_potential_AZs(as_group)
        ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
        all_zones = ec2_conn.get_all_zones()
        epoch_time = int(time.time())
        zone_dict = {}
        for zone in all_zones:
            if zone.name in potential_zones:
                zone_dict[zone.name[-1]] = {"use": True, "health": [0,0,0]}
            else:
                zone_dict[zone.name[-1]] = {"use": False, "health": [0,0,0]}
        return create_tag(as_group, "AZ_status", zone_dict)
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def verify_tag_dict_keys(as_group, tag_name, key_list):
    if not get_tag_dict_value(as_group, tag_name) or not all(key in get_tag_dict_value(as_group, tag_name).keys() for key in key_list):
        print_verbose("Tag not found or not all expected keys found for %s. Initializing." % tag_name)
        return False
    else:
        print_verbose("Expected keys found for %s." % tag_name)
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    parser.add_argument('-e', '--excluded_regions', default=['cn-north-1', 'us-gov-west-1'], nargs='*', type=str, help='Space separated AWS regions to exclude. Default= cn-north-1 us-gov-west-1')
    parser.add_argument('-m', '--min_healthy_AZs', default=3, help="Minimum default number of AZs before alternative launch approaches are tried. Default=3")
    sys.exit(main(parser.parse_args()))

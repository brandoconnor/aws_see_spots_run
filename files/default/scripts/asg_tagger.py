#!/usr/bin/env python
'''
Tagger runs on a periodic basis to tag autoscaling groups, providing the persistence
needed for spot management.

All values (aside from AZ_status) should be a set just once. If a user wants to
override a tag value, that will be honored and not overridden by ssr.
'''
import argparse
import os
import sys

import boto
from aws_ssr_common import (create_tag, dry_run_necessaries, get_bid,
                            get_launch_config, get_potential_azs,
                            get_tag_dict_value, handle_exception,
                            print_verbose)
from boto.exception import BotoServerError, EC2ResponseError


def main(args):
    global verbose
    global dry_run
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    for region in [r.name for r in boto.ec2.regions() if r.name not in args.excluded_regions]:
        try:
            print_verbose(
                os.path.basename(__file__), 'info', 'Starting pass on %s' % region)
            ec2_conn = boto.ec2.connect_to_region(region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)

            all_groups = as_conn.get_all_groups()
            spot_lcs = [
                e for e in as_conn.get_all_launch_configurations() if e.spot_price]
            # these need to be pulled from the same all_groups list or
            # duplicate objects will be seen as distinct.
            spot_lc_groups = [
                g for g in all_groups if g.launch_config_name in [s.name for s in spot_lcs]]
            previously_ssr_managed_groups = [g for g in all_groups if get_tag_dict_value(
                g, 'ssr_config') and get_tag_dict_value(g, 'ssr_config')['enabled'] is True]

            all_groups = list(
                set(spot_lc_groups + previously_ssr_managed_groups))
            for as_group in all_groups:
                print_verbose(
                    os.path.basename(__file__), 'info', "Evaluating %s" % as_group.name)

                # this latter condition can happen when tag value (a dict)
                # can't be interpreted by ast.literal_eval()
                if args.reset_tags or not [t for t in as_group.tags if t.key == 'ssr_config'] or not get_tag_dict_value(as_group, 'ssr_config'):
                    print_verbose(os.path.basename(
                        __file__), 'info', 'Tags not found or reset tags option flagged. Adding all tags anew now.')
                    init_ssr_config_tag(as_group, args.min_healthy_AZs)
                    init_az_status_tag(as_group)

                elif [t for t in as_group.tags if t.key == 'ssr_config' and not get_tag_dict_value(as_group, 'ssr_config')['enabled']]:
                    print_verbose(
                        os.path.basename(__file__), 'info', 'ssr_config DISABLED. Doing nothing.')

                elif [t for t in as_group.tags if t.key == 'ssr_config' and get_tag_dict_value(as_group, 'ssr_config')['enabled']]:
                    print_verbose(os.path.basename(
                        __file__), 'info', 'ssr management enabled. Verifying all config values in place.')
                    config_keys = [
                        'enabled', 'original_bid', 'LC_name', 'min_AZs', 'demand_expiration']

                    if not verify_tag_dict_keys(as_group, 'ssr_config', config_keys) or \
                            not get_tag_dict_value(as_group, 'ssr_config')['LC_name'] == as_group.launch_config_name[-155:]:
                        # this would indicate a change to the LC outside of ssr
                        # scope. In that case, we need to disable ssr via tag
                        # deletion.
                        if not get_launch_config(as_group).spot_price:
                            del_ssr_tags(as_group)
                            continue
                        else:
                            init_ssr_config_tag(as_group, args.min_healthy_AZs)

                    zones = [z.name[-1] for z in ec2_conn.get_all_zones()]
                    if not verify_tag_dict_keys(as_group, 'AZ_status', zones):
                        init_az_status_tag(as_group)

                else:
                    raise Exception(
                        "ssr_enabled tag found for %s but isn't a valid value." % (as_group.name,))

            print_verbose(
                os.path.basename(__file__), 'info', 'Done with pass on %s' % region)

        except EC2ResponseError as e:
            handle_exception(e)

        except BotoServerError as e:
            handle_exception(e)

        except Exception as e:
            handle_exception(e)
            return 1

    print_verbose(os.path.basename(__file__), 'info', "All regions complete")


def del_ssr_tags(as_group):
    return as_group.connection.delete_tags([t for t in as_group.tags if t.key == 'AZ_status' or t.key == 'ssr_config'])


def init_ssr_config_tag(as_group, min_healthy_azs):
    try:
        config_dict = {
            'enabled': True,
            'original_bid': get_bid(as_group),
            'min_AZs': min_healthy_azs,
            # LC name size can be up to 255 chars (also tag value max length).
            # Final chars should be unique so we cut this short
            'LC_name': as_group.launch_config_name[-155:],
            'demand_expiration': False,
        }
        create_tag(as_group, 'ssr_config', config_dict)
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def init_az_status_tag(as_group):
    try:
        potential_zones = get_potential_azs(as_group)
        ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
        all_zones = ec2_conn.get_all_zones()
        zone_dict = {}
        for zone in all_zones:
            if zone.name in potential_zones:
                zone_dict[zone.name[-1]] = {"use": True, "health": [0, 0, 0]}
            else:
                zone_dict[zone.name[-1]] = {"use": False, "health": [0, 0, 0]}
        return create_tag(as_group, "AZ_status", zone_dict)
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def verify_tag_dict_keys(as_group, tag_name, key_list):
    if not get_tag_dict_value(as_group, tag_name) or not all(key in get_tag_dict_value(as_group, tag_name).keys() for key in key_list):
        print_verbose(os.path.basename(
            __file__), 'warn', "Tag not found or not all expected keys found for %s. Initializing." % tag_name)
        return False
    else:
        print_verbose(
            os.path.basename(__file__), 'info', "Expected keys found for %s." % tag_name)
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true',
                        default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true',
                        default=False, help="Print output. Default=False")
    parser.add_argument('-e', '--excluded_regions', default=['cn-north-1', 'us-gov-west-1'], nargs='*',
                        type=str, help='Space separated aws regions to exclude. Default= cn-north-1 us-gov-west-1')
    parser.add_argument('-m', '--min_healthy_AZs', default=1,
                        help="Minimum default number of AZs before alternative launch approaches are tried. Default=3")
    parser.add_argument('-r', '--reset_tags', action='store_true',
                        default=False, help="Reset tags for all relevant as_groups. Default=False")
    sys.exit(main(parser.parse_args()))

#!/usr/bin/env python3
'''
Tagger should be run on a periodic basis (default once an hour) to tag new ASGs
that spring into existence and correct situations where tags are missing

All values aside from AZ_status should be a set just once. If a user wants to
override a tag value, that will be honored and not overridden by automation.

Only 10 tags are allowed per as_group so these need to be used sparingly.
Keys should be:
~148 chars
SSR_config = { 'SSR_enabled': True/False, 'original_bid': '.01', 'min_AZs': '3', 'LC_name': 'launch_config_name'}
This could be condensed into a single, parsable value with ALL AZs but we'd need to be smarter about chars used
<individual_AZ> = { 'use':True,'health':[1, 0, 1],#} # 'last_update':'epoch'} epoch not needed?

#TODO: implement:
demand_expiration = epoch_time_to_check_if_demand_can_be_killed (set in attr default 55m)

details for above:
original_bid = .10 (price during initial tagging - only set once)
spot_LC_name = launch_config_name (if this changes, update all other tags, disable SSR if no longer spot)
min_azs = 3 (set in default attributes)

also possible:
AZ_status = { 'us-east-1a':{see individual_AZ below},'us-east-1b':{},'us-east-1c':{},'...':'...'}

Are these needed? - would be useful for debugging
last_mod_time = set when change happens (across all code and on tag_init)
last_mod_type = action taken last
'''
#XXX do I need to "re-get" an ASG at any point here after tagging?
#TODO: actually implement dry_run in tagging

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
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    excluded_regions = ['cn-north-1', 'us-gov-west-1'] #TODO: make this list an attribute in the chef recipe
    for region in [ r.name for r in boto.ec2.regions() if r.name not in excluded_regions ]:
        try:
            print_verbose('Starting pass on %s' % region)
            ec2_conn = boto.ec2.connect_to_region(region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)
            all_groups = as_conn.get_all_groups()
            spot_LCs = [ e for e in as_conn.get_all_launch_configurations() if e.spot_price ]
            for launch_config in spot_LCs:
                spot_LC_groups = [ g for g in all_groups if g.launch_config_name == launch_config.name ]
                for as_group in spot_LC_groups:
                    if not [ t for t in as_group.tags if t.key == 'SSR_config' ]:
                        print_verbose('Group %s is a candidate for SSR management. Applying all tags...' % as_group.name)
                        init_as_group_tags(as_group, args.min_healthy_AZs)

                    elif [ t for t in as_group.tags if t.key == 'SSR_config' and not get_tag_dict_value(as_group, 'SSR_config')['enabled'] ]:
                        print_verbose('Not managing group %s as SSR_enabled set to false.' % as_group.name)

                    elif [ t for t in as_group.tags if t.key == 'SSR_config' and get_tag_dict_value(as_group, 'SSR_config')['enabled'] ]:
                        print_verbose('Group %s is SSR managed. Verifying all config values in place.' % as_group.name)
                        config_keys = ['enabled', 'original_bid', 'LC_name', 'min_AZs', ]
                        if not verify_tag_dict_keys(as_group, 'SSR_config', config_keys):
                            init_as_group_tags(as_group, args.min_healthy_AZs)

                        zones = [ z.name[-1] for z in ec2_conn.get_all_zones() ]
                        if not verify_tag_dict_keys(as_group, 'AZ_status', zones):
                            init_AZ_status(as_group)
                    else:
                        raise Exception("SSR_enabled tag found for %s but isn't a valid value." % (as_group.name,))

            print_verbose('Done with pass on %s' % region)

        except EC2ResponseError as e:
            handle_exception(e)
            pass

        except BotoServerError as e:
            handle_exception(e)
            pass

        except Exception as e:
            handle_exception(e)
            return 1

    print_verbose("All regions complete")


def init_as_group_tags(as_group, min_AZs):
    try:
        config = get_launch_config(as_group)
        init_AZ_status(as_group)
        config_dict = {
                'enabled': True,
                'original_bid': get_bid(as_group),
                'min_AZs': min_AZs,
                'LC_name': as_group.launch_config_name,
                }
                #"demand_expiration": None, # when the group switches to ondemand, set this to epoch_now + default['attr'] mins
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
                zone_dict[zone.name[-1]] = {"use": True, "health": [0,0,0]} #, "last_update": epoch_time })
            else:
                zone_dict[zone.name[-1]] = {"use": False, "health": [0,0,0]}
        create_tag(as_group, "AZ_status", zone_dict)
        return True
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_AZ_tag(as_group, AZ):
    return [ tag for tag in as_group.tags if tag.key == AZ ][0].value


def set_health(as_group, AZ, health):
    AZ_status = get_AZ_tag(as_group, AZ)
    AZ_status['health'].pop()
    AZ_status['health'].insert(0, health)
    tag = Tag(key=AZ,
            value=AZ_status,
            resource_id=as_group.name)
    as_group.connection.create_or_update_tags(tag)


def create_tag(as_group, key, value):
    try:
        as_tag = Tag(key=key,
                    value=value,
                    resource_id=as_group.name)
        print_verbose("Creating tag for %s." % key)
        if not dry_run:
            return as_group.connection.create_or_update_tags([as_tag])
        else:
            return True
    except BotoServerError as e: # this often indicates tag limit has been exceeded
        handle_exception(e)
        set_SSR_disabled(as_group)
        delete_tag(as_group, 'AZ_status')


def delete_tag(as_group, tag_key):
    tag_list = [ t for t in as_group.tags if t.key in tag_key ]
    as_group.connection.delete_tags(tag_list)


def set_SSR_disabled(as_group): #TODO: implement
    pass


def verify_tag_dict_keys(as_group, tag_name, key_list):
    if not get_tag_dict_value(as_group, tag_name) or not all(key in get_tag_dict_value(as_group, tag_name).keys() for key in key_list):
        print_verbose("Tag not found or not all expected keys found for %s. Initializing." % tag_name)
        return False
    else:
        print_verbose("All expected keys found for %s." % tag_name)
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    parser.add_argument('-m', '--min_healthy_AZs', default=3, help="Minimum default number of AZs before alternative launch approaches are tried. Default=3")
    sys.exit(main(parser.parse_args()))

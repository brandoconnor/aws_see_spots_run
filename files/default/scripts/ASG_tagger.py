#!/usr/bin/env python27
'''
Tagger should be run on a periodic basis (default once an hour) to tag new ASGs
that spring into existence and correct situations where tags are missing

All keys aside from AZ_info should be a set just once. If a user wants to
override a tag value, that will be honored and not overridden by automation.

Keys should be:
SSR_enabled = True/False - can be forced to False in attrs.
AZ_info = { 'us-east-1a':{see individual_AZ below},'us-east-1b':{},'us-east-1c':{},'...':'...'}
original_bid = .10 (price during initial tagging - only set once)
max_bid =  on demand price.
spot_LC_name = launch_config_name (if this changes, update all other tags, disable SSR if no longer spot)
demand_expiration = epoch_time_to_check_if_demand_can_be_killed (set in attr default 55m)
min_azs = 3 (set in default attributes) - how to customize this for some AZs? Maybe don't correct this value if tag is changed.

also possible:
<individual_AZ> = { 'use':True,'health':[1, 0, 1],'last_update':'epoch'}

Are these needed? - would be useful for debugging
last_mod_time = set when change happens (across all code and on tag_init)
last_mod_type = action taken last

Potential feature:
instance_types = [ original_first_choice, m1.next_choice, ect. ] # json or ordered list? maybe give default?
max_price = can be overidden with a json blob in attributes for each instance_type in each region.
'''
import argparse
import ast
import boto
import sys
import time
from AWS_see_spots_run_common import *
from get_prices import get_ondemand_price
from boto import ec2
from boto.ec2 import autoscale
from boto.ec2.autoscale import Tag
from boto.exception import EC2ResponseError


def main(args):
    verbose = dry_run_necessaries(args.dry_run, args.verbose)
    for region in boto.ec2.regions():
        try:
            as_conn = boto.ec2.autoscale.connect_to_region(region.name)
            all_groups = as_conn.get_all_groups()
            spot_LCs = [ e for e in as_conn.get_all_launch_configurations() if e.spot_price ]
            for launch_config in spot_LCs:
                spot_LC_groups = [ g for g in all_groups if g.launch_config_name == launch_config.name ]
                for as_group in spot_LC_groups:
                    print_verbose(as_group.name, verbose)
                    if not [ t for t in as_group.tags if t.key == 'SSR_enabled' ]:
                        # this group does not have the SSR_enabled tag indicator
                        ## default it to True and set all tags
                        print_verbose('Group %s is a candidate for SSR management. Applying all tags...' % as_group.name, verbose)
                        init_as_group_tags(as_group, args.min_healthy_AZs)

                    elif [ t for t in as_group.tags if t.key == 'SSR_enabled' and t.value == 'False' ]:
                        print_verbose('Not managing group as SSR_enabled set to false.' % as_group.name, verbose)

                    elif [ t for t in as_group.tags if t.key == 'SSR_enabled' and t.value == 'True' ]:
                        #TODO: verify all tags exist for this ASG, if not, re init all... might be better to just reinit missing tags
                        print_verbose('Group %s is SSR managed. Verifying all tags in place.', verbose)
                        if not all_tags_exist():
                            init_as_group_tags(as_group, args.min_healthy_AZs)
                    else:
                        raise Exception("SSR_enabled tag found for %s but isn't a valid value." % as_group.name)

            print_verbose('Done with pass on %s' % region.name ,verbose)

        except EC2ResponseError, e:
            handle_exception(e)
            pass

        except Exception, e:
            handle_exception(e)
            return 1


def init_as_group_tags(as_group, min_AZs):
    config = get_launch_config(as_group)
    init_AZ_info(as_group)
    config_dict = {
            "SSR_enabled": True,
            "original_bid": get_bid(as_group),
            "max_bid": get_ondemand_price(as_group, verbose),
            "spot_LC_name": as_group.launch_config_name,
            "demand_expiration": None, # when the group switches to ondemand, set this to epoch_now + default['attr'] mins
            "min_healthy_AZs": min_AZs
            }
    for k,v in config_dict:
        create_tag(as_group, k, v)


def init_AZ_info(as_group):
    potential_zones = get_potential_AZs(as_group)
    ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
    all_zones = ec2_conn.get_all_zones()

    epoch_time = int(time.time())

    for zone in all_zones:
        if zone.name in potential_zones:
            create_tag(as_group, zone.name, {"use": True, "health": [0,0,0], "last_update": epoch_time })
        else:
            create_tag(as_group, zone.name, {"use": False, "health": [0,0,0], "last_update": epoch_time })


def set_health(as_group, AZ, health):
    # like exit codes 0 is healthy, 1 is unhealthy
    pass


def create_tag(as_group, key, value):
    as_tag = Tag(key=key,
                value=value,
                resource_id=as_group.name)
    return as_group.connection.create_or_update_tags([as_tag])
    # as_conn.connection.get_all_groups(names=[as_group.name])[0] # or return refreshed group?
    # return group


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    parser.add_argument('-m', '--min_healthy_AZs', default=3, help="Minimum default number of AZs before alternative launch approaches are tried. Default=3")
    sys.exit(main(parser.parse_args()))

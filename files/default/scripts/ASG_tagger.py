#!/usr/bin/env python27
'''
Keys should be:
SSR_enabled = True/False - can be forced to False in attrs. Checked every time.
AZ_info = { 'A':{see individual_AZ below},'B':{},'C':{},'D':{},'E':{} }
original_bid = .10 (price during initial tagging - only set once)
max_bid = determined by either json in attributes OR on demand price (verfied each pass)
spot_LC_name = launch_config_name (if this changes, update all other tags, disable SSR if no longer spot)
demand_expiration = epoch_time_to_check_if_demand_can_be_killed (set in attr default 55m)
min_azs = num (attr set default=3)

also possible:
<individual_AZ> = { 'use':True,'health':[1, 0, 1],'last_update':'epoch'}

Are these needed?
last_mod_time = set when change happens (across all code and on tag_init)
last_mod_type = action taken last

Potential feature:
instance_types = [ original_first_choice, m1.next_choice, ect. ] # json or ordered list? maybe give default?
'''
import argparse
import ast
import boto
import sys
from AWS_see_spots_run_common import *
from ec2instancespricing import get_ec2_ondemand_instances_prices
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
            for LC in spot_LCs:
                spot_LC_groups = [ g for g in all_groups if g.launch_config_name == LC.name ]
                for as_group in spot_LC_groups:
                    print_verbose(as_group.name, verbose)
                    if not [ t for t in as_group.tags if t.key == 'SSR_enabled' ]:
                        # this group does not have the SSR_enabled tag indicator
                        ## default it to True and set all tags
                        print_verbose('Group %s is a candidate for SSR management. Applying all tags...' % (as_group.name) , verbose)
                        config_dict = {
                                "SSR_enabled": True,
                                "AZ_info": check_group_AZs(as_conn,as_group.launch_config_name),
                                "original_bid": get_bid(as_group.launch_configuration_name),
                                "max_bid": get_max_bid(as_group.launch_config_name), # with LC name we can get LC, find instance type and determine the on_demand price
                                "spot_LC_name": as_group.launch_config_name,
                                "demand_expiration": None, # when the first ondemand instance is spun up, set this to now+55 mins (epoch + 3300)
                                "min_AZs": 3, # find a way to make this configurable. Perhaps this script could be a template OR a passed arg
                                }
                        for k,v in config_dict: 
                            create_tag()
                    elif [ t for t in as_group.tags if t.key == 'SSR_enabled' and t.value == 'False' ]:
                        # a group that we shouldn't manage
                        print_verbose('Not managing group as SSR_enabled set to false.' % as_group.name, verbose)
                        pass
                    elif [ t for t in as_group.tags if t.key == 'SSR_enabled' and t.value == 'True' ]:
                        # this is an SSR managed ASG, verify tags are correct and manage
                        # these groups could be found just by searching all ASGs for this key value pair. Easier than going through the iteration.
                        print_verbose('Group %s is SSR managed. Verifying tags or skipping?', verbose)
                        pass
                    else:
                        raise Exception("SSR_enabled tag found for %s but isn't a valid value." % as_group.name)

            print_verbose('Done with pass on %s' % region.name ,verbose)

        except EC2ResponseError, e:
            handle_exception(e)
            pass

        except Exception, e:
            handle_exception(e)
            return 1


def check_group_AZs(as_conn, lc_name):
    config = as_conn.get_all_launch_configurations([lc_name])[0]
    get_ec2_ondemand_instances_prices(filter_region=None, filter_instance_type=None, filter_os_type=None, use_cache=False)
    
    config.spot_price
    # return { 'A': { 'use':True, 'health':[0, 0, 1], 'last_update':'epoch'}, 'B': '...' }
    return True


def get_health(as_conn as_group, AZ):
    # returns True or False depending on health (2/3 health checks == 0)
    pass


def set_health(as_conn, as_group, AZ, status):
    # like exit codes 0 is healthy, 1 is unhealthy
    pass


def create_tag(as_conn, as_group_name, key, value):
    as_tag = Tag(key=key,
                value=value,
                resource_id=as_group_name)
    return as_conn.create_or_update_tags([as_tag])
    #as_conn.get_all_groups(names=[as_group_name])[0] # or return refreshed group?
    #return group


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    sys.exit(main(parser.parse_args()))

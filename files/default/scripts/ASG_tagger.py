#!/usr/bin/env python27
#XXX test on various python distributions
'''
Keys should be:
- SSR_enabled = True/False - can be forced to False in attrs. Checked every time.
- AZ_exclusions/valid_AZs = find a way to list AZs to never include (verified and reset every time)
- instance_types = [ original_first_choice, m1.next_choice, ect. ] # json or ordered list? maybe give default?
- original_price = .10 (price during initial tagging - only set once)
- max_price = 4x ondemand (determined by either json blob OR max possible price)
- last_mod_time = set when change happens (across all code and on tag_init)
- last_mod_type = action taken last
- spot_LC = launch_config_name or id (when this changes, update all other tags, disable SSR if no longer spot)
'''
import argparse
import ast
import boto
import boto.utils
import sys
from AWS_see_spots_run_common import *
from boto import utils, ec2
from boto.ec2 import autoscale
from boto.ec2.autoscale import Tag # ?
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
                        pass
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



def create_tag(as_conn, as_group, key, value):
    as_tag = Tag(key=key,
                value=value,
                resource_id=as_group.name)
    return as_conn.create_or_update_tags([as_tag])
    #as_conn.get_all_groups(as_group.name)[0] # or return refreshed group?
    #return group


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    sys.exit(main(parser.parse_args()))

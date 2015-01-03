#!/usr/bin/env python
'''
Kills stale spot requests which are unlikely to be fulfilled,
allowing the request to shift a more viable AZ through SSR.
'''
import argparse
import boto.ec2
import json
import sys
from AWS_see_spots_run_common import *
from boto.exception import EC2ResponseError
from boto.ec2 import autoscale
from datetime import datetime, timedelta

def main(args):
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    for region in [ r.name for r in boto.ec2.regions() if r.name not in args.excluded_regions ]:
        try:
            ec2_conn = boto.ec2.connect_to_region(region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)
            as_groups = as_conn.get_all_groups()
            all_spot_lcs = [ l for l in as_conn.get_all_launch_configurations() if l.spot_price ]
            pending_requests = []
            bad_statuses = json.loads('{"status-code": ["capacity-not-available", "capacity-oversubscribed", "price-too-low", "not-scheduled-yet", "launch-group-constraint", "az-group-constraint", "placement-group-constraint", "constraint-not-fulfillable" ]}')
            pending_requests.append(ec2_conn.get_all_spot_instance_requests(filters=bad_statuses))
            oldest_time = datetime.utcnow() - timedelta(minutes=args.minutes)
            # flattening the list of lists here
            pending_requests = [ item for sublist in pending_requests for item in sublist ]
            health_tags = []
            for request in pending_requests:
                if oldest_time > datetime.strptime(request.create_time, "%Y-%m-%dT%H:%M:%S.000Z"):
                    print_verbose("Bad request found. Identifying LC and associated ASGs to tag AZ health.")
                    launch_config = [ lc for lc in all_spot_lcs 
                            if request.price == lc.spot_price and 
                            request.launch_specification.instance_type == lc.instance_type and
                            request.launch_specification.instance_profile['name'] == lc.instance_profile_name and
                            request.launch_specification.image_id == lc.image_id ][0] # This could be made hella specific if we want to go that route
                    offending_as_groups = [ g for g in as_groups if g.launch_config_name == launch_config.name ]
                    bad_AZ = request.launch_group.split(request.region.name)[1][0]
                    health_dict = { bad_AZ : 1 }
                    for as_group in offending_as_groups:
                        health_tags.append(set_new_AZ_status_tag(as_group, health_dict))
                    print_verbose("Killing spot request %s." % str(request.id))
                    if not args.dry_run:
                        request.cancel()
                        update_tags(as_conn, health_tags)
                    else:
                        print_verbose("PSYCH! Dry run.")
                else:
                    print_verbose("Request %s not older than %s minutes. Continuing..." % (request.id, str(args.minutes)))
            print_verbose("Region %s pass complete." % region)

        except EC2ResponseError as e:
            handle_exception(e)

        except Exception as e:
            handle_exception(e)
            return 1

    print_verbose("All regions complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    parser.add_argument('-e', '--excluded_regions', default=['cn-north-1', 'us-gov-west-1'], nargs='*', type=str, help='Space separated AWS regions to exclude. Default= cn-north-1 us-gov-west-1')
    parser.add_argument('-m', '--minutes', type=int, default=10, help="Minutes before a spot request is considered stale. Default: 10")
    sys.exit(main(parser.parse_args()))

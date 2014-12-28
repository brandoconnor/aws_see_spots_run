#!/usr/bin/env python3
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
from datetime import datetime, timedelta


def main(args):
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    excluded_regions = ['cn-north-1', 'us-gov-west-1'] #TODO: make this list an attribute in the chef recipe
    for region in [ r.name for r in boto.ec2.regions() if r.name not in excluded_regions ]:
        try:
            ec2_conn = boto.ec2.connect_to_region(region)
            pending_requests = []
            bad_statuses = json.loads('{"status-code": ["capacity-not-available", "capacity-oversubscribed", "price-too-low", "not-scheduled-yet", "launch-group-constraint", "az-group-constraint", "placement-group-constraint", "constraint-not-fulfillable" ]}')
            pending_requests.append(ec2_conn.get_all_spot_instance_requests(filters=bad_statuses))
            oldest_time = datetime.utcnow() - timedelta(minutes=args.minutes)
            # flattening the list of lists here
            print pending_requests
            pending_requests = [ item for sublist in pending_requests for item in sublist ]
            for request in pending_requests:
                if oldest_time > datetime.strptime(request.create_time, "%Y-%m-%dT%H:%M:%S.000Z"):
                    print_verbose("Killing spot request %s." % str(request.id))
                    # there doesnt appear to be a way to trace a spot request back to the AZ that requested it
                    ## otherwise I'd consider adding a failed health check to this AZ for the as_group
                    if not args.dry_run:
                        request.cancel()
                    else:
                        print_verbose("PSYCH! Dry run.")
                else:
                    print_verbose("Request %s not older than %s minutes. Continuing..." % (request.id, str(args.minutes)))
            print_verbose("Region %s pass complete." % region)

        except EC2ResponseError as e:
            handle_exception(e)
            pass

        except Exception as e:
            handle_exception(e)
            return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-m', '--minutes', type=int, default=10, help="Minutes before a spot request is considered stale. Default: 10")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    sys.exit(main(parser.parse_args()))

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
from datetime import datetime, timedelta


def main(args):
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    for region in [ r.name for r in boto.ec2.regions() if r.name not in args.excluded_regions ]:
        try:
            ec2_conn = boto.ec2.connect_to_region(region)
            pending_requests = []
            bad_statuses = json.loads('{"status-code": ["capacity-not-available", "capacity-oversubscribed", "price-too-low", "not-scheduled-yet", "launch-group-constraint", "az-group-constraint", "placement-group-constraint", "constraint-not-fulfillable" ]}')
            pending_requests.append(ec2_conn.get_all_spot_instance_requests(filters=bad_statuses))
            oldest_time = datetime.utcnow() - timedelta(minutes=args.minutes)
            # flattening the list of lists here
            pending_requests = [ item for sublist in pending_requests for item in sublist ]
            for request in pending_requests:
                if oldest_time > datetime.strptime(request.create_time, "%Y-%m-%dT%H:%M:%S.000Z"):
                    print_verbose("Killing spot request %s." % str(request.id))
                    #XXX there doesnt appear to be a way to trace a spot request back to the AZ that requested it
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

        except Exception as e:
            handle_exception(e)
            return 1

    print_verbose("All regions complete")


def probably_throwaway_code():
    offending_AZ = Counter([ json.loads(a.Details)['Availability Zone'] for a in g.get_activities() if
                        a.status_code != 'Successful' and
                        'cancelled' in a.status_message and
                        a.end_time > datetime.utcnow() - timedelta(minutes=60) ] ).most_common(1)

    if offending_AZ and offending_AZ[0][1] >= 3: # relies on order of the tuple returned
        ## alter instance type to one one larger of the same family
        good_AZs = get_healthy_AZs(as_group)
        offending_AZ = offending_AZ[0][0]
        if offending_AZ in good_AZs:
            good_AZs.remove(offending_AZ)
        if len(good_AZs) >= 2:
            as_group.availability_zones = good_AZs

    else:
        good_AZs = get_healthy_AZs(as_group) # get them via tag and json parsing
        good_AZs.sort()
        live_AZs = as_group.availability_zones
        live_AZs.sort()
        # maybe add back ASGs in a good state
        print_verbose("No bad AZs %s using %s." % (ASG.name, LC.instance_type))
        if good_AZs != live_AZs:
            print_verbose("Current AZs %s but should be %s" % (live_AZs, good_AZs))




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    parser.add_argument('-e', '--excluded_regions', default=['cn-north-1', 'us-gov-west-1'], nargs='*', type=str, help='Space separated AWS regions to exclude. Default= cn-north-1 us-gov-west-1')
    parser.add_argument('-m', '--minutes', type=int, default=10, help="Minutes before a spot request is considered stale. Default: 10")
    sys.exit(main(parser.parse_args()))

#!/usr/bin/env python
'''
Kills stale spot requests which are unlikely to be fulfilled,
allowing the request to shift a more viable AZ.
'''
import argparse
import boto.ec2
import datetime
import json
import sys
from AWS_see_spots_run_common import *
from boto.exception import EC2ResponseError

def main(args):
    verbose = dry_run_necessaries(args.dry_run, args.verbose)
    for region in boto.ec2.regions():
        try:
            ec2_conn = boto.ec2.connect_to_region(region.name)
            pending_requests = []
            bad_statuses = json.loads('{"status-code": ["capacity-not-available", "capacity-oversubscribed", "price-too-low", "not-scheduled-yet", "launch-group-constraint", "az-group-constraint", "placement-group-constraint", "constraint-not-fulfillable" ]}')
            pending_requests.append(ec2_conn.get_all_spot_instance_requests(filters=bad_statuses))
            oldest_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=args.minutes)
            # flattening the list of lists here
            pending_requests = [item for sublist in pending_requests for item in sublist]
            for request in pending_requests:
                if oldest_time > datetime.datetime.strptime(request.create_time, "%Y-%m-%dT%H:%M:%S.000Z"):
                    print_verbose("Killing spot request %s." % str(request.id), verbose)
                    if not args.dry_run:
                        request.cancel()
                    else:
                        print_verbose("PSYCH! Dry run.", verbose)
                else:
                    print_verbose("Request %s not older than %s minutes. Continuing..." % (request.id, str(args.minutes)), verbose)
            print_verbose("Region %s pass complete." % region.name, verbose)

        except EC2ResponseError, e:
            handle_exception(e)
            pass

        except Exception, e:
            handle_exception(e)
            return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-m', '--minutes', type=int, default=10, help="Minutes before a spot request is considered stale. Default: 10")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    sys.exit(main(parser.parse_args()))

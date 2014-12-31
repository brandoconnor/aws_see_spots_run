#!/usr/bin/env python
#
# TODO: add a blurb up here
#

import argparse
import ast
import boto
from boto import ec2
import sys
from AWS_see_spots_run_common import *
from boto.ec2 import autoscale
from boto.exception import BotoServerError, EC2ResponseError


def main(args):
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    for region in [ r.name for r in boto.ec2.regions() if r.name not in args.excluded_regions ]:
        try:
            print_verbose('Starting pass on %s' % region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)
            as_groups = get_SSR_groups(as_conn)
            health_tags = []
            for as_group in as_groups:
                bid = get_bid(as_group)
                current_prices = get_current_spot_prices(as_group)
                health_dict = {}
                if current_prices:
                    print_verbose("Checking prices for %s" % as_group.name)
                    for price in current_prices:
                        if price.price > bid:# * 1.1: #NOTE: bid must be 10% higher than the price in order to remain unchanged (make this configurable?)
                            health_dict[price.availability_zone[-1]] = 1
                        else:
                            health_dict[price.availability_zone[-1]] = 0
                    health_tags.append(get_new_health_tag(as_group, health_dict))
            if health_tags and not dry_run:
                update_tags(as_conn, health_tags)
                print_verbose("All tags updated!")

            print_verbose('Done with pass on %s' % region)


        except EC2ResponseError as e:
            handle_exception(e)

        except Exception as e:
            handle_exception(e)
            return 1

    print_verbose("All regions complete")


def update_tags(as_conn, health_tags):
    try:
        as_conn.create_or_update_tags(health_tags)
    except Exception as e:
        handle_exception(e)
        sleep(1)
        update_tags(as_conn, health_tags)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    parser.add_argument('-e', '--excluded_regions', default=['cn-north-1', 'us-gov-west-1'], nargs='*', type=str, help='Space separated AWS regions to exclude. Default= cn-north-1 us-gov-west-1')
    sys.exit(main(parser.parse_args()))

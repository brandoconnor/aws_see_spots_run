#!/usr/bin/env python
'''
Updates health tags for every ssr managed ASG, comparing the LC's bid price to each AZ
for that LC's instance type.
'''
import argparse
import os
import sys

import boto
from boto.exception import EC2ResponseError

from aws_ssr_common import (dry_run_necessaries, get_bid,
                            get_current_spot_prices, get_ssr_groups,
                            handle_exception, print_verbose,
                            update_az_health_list_tag, update_tags)


def main(args):
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    for region in [r.name for r in boto.ec2.regions() if r.name not in args.excluded_regions]:
        try:
            print_verbose(
                os.path.basename(__file__), 'info', 'Starting pass on %s' % region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)
            as_groups = get_ssr_groups(as_conn)
            health_tags = []
            for as_group in as_groups:
                bid = get_bid(as_group)
                current_prices = get_current_spot_prices(as_group)
                health_dict = {}
                if current_prices:
                    print_verbose(
                        os.path.basename(__file__), 'info', "Updating health for %s" % as_group.name)
                    for price in current_prices:
                        # * 1.1: #NOTE: potential feature to require a price buffer here?
                        if price.price > bid:
                            health_dict[price.availability_zone[-1]] = 1
                        else:
                            health_dict[price.availability_zone[-1]] = 0
                    health_tags.append(
                        update_az_health_list_tag(as_group, health_dict))
            if health_tags and not dry_run:
                update_tags(as_conn, health_tags)
                print_verbose(
                    os.path.basename(__file__), 'info', "All tags updated!")

            print_verbose(
                os.path.basename(__file__), 'info', 'Done with pass on %s' % region)

        except EC2ResponseError as e:
            handle_exception(e)

        except Exception as e:
            handle_exception(e)
            return 1

    print_verbose(os.path.basename(__file__), 'info', "All regions complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true',
                        default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true',
                        default=False, help="Print output. Default=False")
    parser.add_argument('-e', '--excluded_regions', default=['cn-north-1', 'us-gov-west-1'], nargs='*',
                        type=str, help='Space separated aws regions to exclude. Default= cn-north-1 us-gov-west-1')
    sys.exit(main(parser.parse_args()))

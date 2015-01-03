#!/usr/bin/env python

import argparse
import boto
import sys
from AWS_see_spots_run_common import *
from boto.ec2 import autoscale
from boto.exception import BotoServerError, EC2ResponseError
from time import sleep

def main(args):
    global verbose
    global dry_run
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    for region in [ r.name for r in boto.ec2.regions() if r.name not in args.excluded_regions ]:
        try:
            print_verbose('Starting pass on %s' % region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)
            all_launch_configs = as_conn.get_all_launch_configurations()
            as_groups = as_conn.get_all_groups()

            for launch_config in all_launch_configs:
                if not [ g for g in as_groups if g.launch_config_name == launch_config.name ]:
                    print_verbose("Launch config %s looks to be abandoned." % launch_config.name)
                    if not dry_run:
                        print_verbose("DESTROY!")
                        kill_with_fire(launch_config)

            print_verbose('Done with pass on %s' % region)

        except Exception as e:
            handle_exception(e)
            sys.exit(1)


def kill_with_fire(launch_config):
    try:
        launch_config.delete()
    except BotoServerError as e:
        if e.error_code == 'Throttling':
            print_verbose('Pausing for AWS throttling...')
            sleep(1)
            return kill_with_fire(launch_config)
        else:
            handle_exception(e)
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    parser.add_argument('-e', '--excluded_regions', default=['cn-north-1', 'us-gov-west-1'], nargs='*', type=str, help='Space separated AWS regions to exclude. Default= cn-north-1 us-gov-west-1')
    sys.exit(main(parser.parse_args()))

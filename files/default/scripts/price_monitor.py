#!/usr/bin/env python3
# price_monitor.py
#
#TODO: write code to determine if any 1 or 2 AZs with high prices can be nixed

import boto
from boto import ec2
import sys
from AWS_see_spots_run_common import *
from get_prices import *


def main(args):
    (verbose, dry_run) = dry_run_necessaries(args.dry_run, args.verbose)
    excluded_regions = ['cn-north-1', 'us-gov-west-1'] #TODO: make this list an attribute in the chef recipe
    for region in [ r.name for r in boto.ec2.regions() if r.name not in excluded_regions ]:
        try:
            print_verbose('Starting pass on %s' % region)
            as_conn = boto.ec2.autoscale.connect_to_region(region)
            as_groups = get_SSR_groups(as_conn)
            for as_group in as_groups:
                bid = get_bid(as_group)
                current_prices = get_current_spot_prices(as_group)
                for price in current_prices:
                    if price.price > bid * 1.1: #NOTE: bid must be 10% higher than the price in order to remain unchanged (make this configurable?)
                        print("price of %s in AZ %s is too high. Marking AZ as unhealthy." % price.availability_zone)
                        set_health(as_group, price.availability_zone, 1)
                    else:
                        set_health(as_group, price.availability_zone, 0)

                get_as_group_health(as_group)

            print_verbose('Done with pass on %s' % region)


        # demand_price = get_ondemand_price(get_launch_config(as_group))
        # switch_to_demand()
        # modify_price(as_group, price.price * 1.1)
        # good_AZs = []
        # raise_price = False
        # mod_AZs = False

        except EC2ResponseError as e:
            handle_exception(e)
            pass

        except Exception as e:
            handle_exception(e)
            return 1


def wasted():
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
    parser.add_argument('-m', '--min_healthy_AZs', default=3, help="Minimum default number of AZs before alternative launch approaches are tried. Default=3")
    sys.exit(main(parser.parse_args()))

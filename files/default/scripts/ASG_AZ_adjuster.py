# A script to manage autoscaling groups on spot instances. These ASGs can get into states where
# scale up actions are repeatedly tried and cancelled due to high prices or lingering requests for
# other reasons. This script will notice that situation and take action to remove bad AZs from the
# ASG in question.

import argparse
import boto
import json
import sys
from AWS_see_spots_run_common import *
from boto import ec2
from boto.ec2 import autoscale
from boto.exception import EC2ResponseError, BotoServerError
from collections import Counter
from datetime import datetime, timedelta


def main(args):
    verbose = dry_run_necessaries(args.dry_run, args.verbose)
    for region in boto.ec2.regions():
        try:
            as_conn = boto.ec2.autoscale.connect_to_region(region.name)
            ec2_conn = boto.ec2.connect_to_region(region.name)
            all_ASGs = as_conn.get_all_groups()
            # TODO: a lot of this work can be replaced with looking for ASGs with tags provided
            spot_LCs = [ e for e in as_conn.get_all_launch_configurations() if e.spot_price ]
            for launch_config in spot_LCs:
                try:
                    product_description = ec2_conn.get_image(LC.image_id).platform
                except:
                    continue
                LC_ASGs = [ g for g in all_ASGs if g.launch_config_name == launch_config.name ]
                for as_group in LC_ASGs:
                    # grab top AZ of last unsuccessful activities in the past x minutes (30m)
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
                            print("Updating %s with AZs %s and not %s" % (as_group.name, good_AZs, offending_AZ), verbose)
                            if not args.dry_run:
                                as_group.update()
                        else:
                            print_verbose("Not enough AZs left on %s to kill willy nilly. Keeping %s which contains %s." % (ASG.name, good_AZs, offending_AZ), verbose)
                    else:
                        good_AZs = get_healthy_AZs(as_group) # get them via tag and json parsing
                        good_AZs.sort()
                        live_AZs = as_group.availability_zones
                        live_AZs.sort()
                        # maybe add back ASGs in a good state
                        print_verbose("No bad AZs %s using %s." % (ASG.name, LC.instance_type), verbose)
                        if good_AZs != live_AZs:
                            print_verbose("Current AZs %s but should be %s" % (live_AZs, good_AZs), verbose)
            print_verbose("Region %s pass complete." % region.name, verbose)

        except EC2ResponseError, e:
            handle_exception(e)
            pass

        except BotoServerError, e:
            handle_exception(e)
            pass

        except Exception, e:
            handle_exception(e)
            return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    sys.exit(main(parser.parse_args()))

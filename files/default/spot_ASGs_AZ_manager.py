#!/usr/bin/env python27
'''
A script to manage autoscaling groups on spot instances. These ASGs can get into states where
scale up actions are repeatedly tried and cancelled due to high prices or lingering requests for
other reasons. This script will notice that situation and take action to remove bad AZs from the
ASG in question.
'''
import os
import json
import sys
from boto import utils, ec2
from boto.ec2 import autoscale
import boto
import boto.utils
from datetime import datetime, timedelta
from collections import Counter

region = boto.utils.get_instance_metadata()['placement']['availability-zone'][:-1]
as_conn = boto.ec2.autoscale.connect_to_region(region)
ec2_conn = boto.ec2.connect_to_region(region)

def main():
    try:
        all_ASGs = as_conn.get_all_groups()
        spot_LCs = [ e for e in as_conn.get_all_launch_configurations() if e.spot_price ]
        for LC in spot_LCs:
            bid_price = LC.spot_price
            instance_type = LC.instance_type
            LC_ASGs = [ g for g in all_ASGs if g.launch_config_name == LC.name ]

            for ASG in LC_ASGs:
                # grab top AZ of last unsuccessful activities in the past x minutes (30m)
                worst_AZ = Counter([ json.loads(a.Details)['Availability Zone'] for a in g.get_activities() if
                        a.status_code != 'Successful' and
                        'cancelled' in a.status_message and
                        a.end_time > datetime.utcnow() - timedelta(minutes=60) ] ).most_common(1)

                if worst_AZ and worst_AZ[0][1] >= 3: # relies on order of the tuple
                    # this could be made very robust and complicated if necessary. For instance, we could...
                    ## alter our bid price according prices across all AZs (above all but a crazy price)
                    ## alter instance type to one one larger of the same family
                    good_AZs = get_AZs(LC.instance_type, LC.spot_price)
                    worst_AZ = worst_AZ[0][0]
                    if worst_AZ in good_AZs:
                        good_AZs.remove(worst_AZ)
                    if len(good_AZs) >= 2:
                        ASG.availability_zones = good_AZs
                        print("Updating %s with AZs %s and not %s" % (ASG.name, good_AZs, worst_AZ))
                        #ASG.update()
                    else:
                        print("Not enough AZs left on %s to kill willy nilly. Keeping %s which contains %s." % (ASG.name, good_AZs, worst_AZ))
                else:
                    good_AZs = get_AZs(LC.instance_type, LC.spot_price)
                    good_AZs.sort()
                    live_AZs = ASG.availability_zones
                    live_AZs.sort()
                    # maybe add back ASGs in a good state
                    print("No bad AZs %s using %s." % (ASG.name, LC.instance_type))
                    if good_AZs != live_AZs:
                        print("Current AZs %s\nbut should be %s" % (live_AZs, good_AZs))

    except Exception, e:
        print e
        return 1


def get_AZs(instance_type, bid_price): #XXX remove this instance_type default and pass this along
    start_time = datetime.utcnow() - timedelta(minutes=5) #XXX need utc here?
    start_time = start_time.isoformat()
    end_time = datetime.utcnow().isoformat()
    prices = ec2_conn.get_spot_price_history(product_description='Linux/UNIX', end_time=end_time, start_time=start_time, instance_type=instance_type)
    AZs = [ sp.availability_zone for sp in prices if sp.price < bid_price ]
    return list(set(AZs))


if __name__ == "__main__":
    sys.exit(main())

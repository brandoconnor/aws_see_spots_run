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


def match_AZs_on_elbs(as_group, dry_run, verbose):
    try:
        elb_conn = boto.ec2.elb.connect_to_region(as_group.connection.region.name)
        for elb_name in as_group.load_balancers:
            elb = elb_conn.get_all_load_balancers(elb_name)
            if not elb.availability_zones == as_group.availability_zones:
                print_verbose("AZs for ELB don't match that of the as_group. Aligning them now.", verbose)
                if not dry_run:
                    elb.enable_zones(as_group.availability_zones)

    except Exception, e:
        handle_exception(e)
        return 1



def modify_as_group_AZs(as_group, good_AZs, dry_run, verbose):
    try:
        as_group.availability_zones = good_AZs
        print("Updating %s with AZs %s" % (as_group.name, good_AZs), verbose)
            if not dry_run:
                as_group.update()
                if as_group.load_balancers:
                    match_AZs_on_elbs(as_group)
    
    except Exception, e:
        handle_exception(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python27
'''
Changes the bid price to either specified value or 
This is the only script of the bunch that isn't run on a schedule.
'''
import boto
import json
import sys
from AWS_see_spots_run_common import *
from boto import utils, ec2
from boto.ec2 import autoscale
from  boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.exception import EC2ResponseError, BotoServerError

def recreate_LC(as_conn, LC_name, new_price, dry_run, verbose):
    try:
        launch_config = as_conn.get_all_launch_configurations(names=[LC_name])[0]
        user_data = launch_config.user_data
        
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
    sys.exit(main()) 

#!/usr/bin/python

import boto
import json
import random
import requests
import string
import sys
from AWS_see_spots_run_common import *
from boto.exception import EC2ResponseError, BotoServerError


def get_ondemand_price(region, os_class, instance_type):
    ondemand_urls = {
            'linux': 'https://a0.awsstatic.com/pricing/1/deprecated/ec2/linux-od.json',
            'mswin' 'https://a0.awsstatic.com/pricing/1/deprecated/ec2/sles-od.json',
            'sles': 'https://a0.awsstatic.com/pricing/1/deprecated/ec2/sles-od.json',
            'rhel': 'https://a0.awsstatic.com/pricing/1/deprecated/ec2/rhel-od.json',
            }
    resp = requests.get(ondemand_urls(os_class[instance_type])
    try:
        ec2_conn

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

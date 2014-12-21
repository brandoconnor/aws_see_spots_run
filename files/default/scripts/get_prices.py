#!/usr/bin/python
# get_prices.py
#
#

import boto
# import json #XXX necessary?
import requests
import sys
from AWS_see_spots_run_common import *


def get_price_url(os_class): # valid for mswin, sles, rhel, linux XXX is there a way to provide list of valid options for a python method?
    # prev and current gen might matter for these links
    ## try https://a0.awsstatic.com/pricing/0/deprecated/ec2/linux-od.json
    return 'https://a0.awsstatic.com/pricing/1/deprecated/ec2/%s-od.json' % os_class


def get_ondemand_price(as_conn, region, launch_config_name, verbose):
    os_class_map = {} # how do LCs give these? I think AMIs have them so get LC.image_id and search for that image.platform. Map from there
    prev_gen_price_map = {'us-east-1': {'m1.small': .01, 'm2.xlarge': .33 } } #TODO: fill this in or find another way
    try:
        # this is super ugly and at some point will likely not work due to deprecation
        # fall back on a manually maintained dictionary for all if absolutely necessary. Demand prices don't vary so often.
        # use a dictionary or find another automation method

        previous_gen_types = ['m1', 'm2', 'c2']
        if instance_size.split('.')[0] in previous_gen_types:
            print_verbose("Previous gen on demand prices not implemented yet", verbose)
            return .01
        else:
            json_blob = requests.get(get_price_url(os_class()).json()
            # this code feels gross
            regional_prices_json = [ r for r in json_blob['config']['regions'] if r['region'] == region ][0]['instanceTypes']
            instance_class_prices_json = [ r for r in regional_prices_json if instance_size in [ e['size'] for e in r['sizes'] ] ][0]['sizes']
            price = float([ e for e in instance_class_prices_json['sizes'] if e['size'] == instance_size ][0]['valueColumns'][0]['prices']['USD'])
            print_verbose("On demand price for %s in %s is %s" % (instance_size, region, price), verbose) #XXX should verbose make it here?
            return price

    except Exception, e:
        handle_exception(e)
        sys.exit(1)

def main():
    pass


if __name__ == "__main__":
    sys.exit(main())

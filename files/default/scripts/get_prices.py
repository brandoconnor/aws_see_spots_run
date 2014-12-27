#!/usr/bin/env python
# get_prices.py
#

import boto
from boto import ec2
import requests
import sys
import demjson
from AWS_see_spots_run_common import *
from datetime import datetime, timedelta


def get_current_spot_prices(as_group):
    try:
        ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)

        start_time = datetime.now() - timedelta(minutes=5)
        start_time = start_time.isoformat()
        end_time = datetime.now().isoformat()
        image = get_image(as_group)
        if image.platform == 'windows':
            os_type = 'Windows'
        elif 'SUSE Linux Enterprise Server' in image.description:
            os_type = 'SUSE Linux'
        else:
            os_type = 'Linux/UNIX'
        if as_group.vpc_zone_identifier:
            os_type += ' (Amazon VPC)'

        prices = ec2_conn.get_spot_price_history(
                product_description=os_type, 
                end_time=end_time, 
                start_time=start_time, 
                instance_type= get_launch_config(as_group).instance_type
                )
        return prices # returns a list of ALL spot prices for all AZs

    except:
        handle_exception(sys.exc_info()[0])
        sys.exit(1)


def get_price_url(launch_config):
    # nabbed URL list from https://github.com/iconara/ec2pricing/blob/master/public/app/ec2pricing/config.js
    base_url = 'http://a0.awsstatic.com/pricing/1/ec2/'

    previous_gen_types = ['m1', 'm2', 'c2', 'cc2', 'cg1', 'cr1', 'hi1']
    if launch_config.instance_type.split('.')[0] in previous_gen_types:
        base_url += 'previous-generation/'

    image = ec2_conn.get_image(launch_config.image_id)

    if image.platform == 'windows':
        base_url += 'mswin'
    elif 'SUSE Linux Enterprise Server' in image.description:
        base_url += 'sles'
    else:
        base_url += 'linux'
    url = base_url + '-od.min.js'
    return url


def get_ondemand_price(launch_config, verbose):
    try:
        region = launch_config.connection.region.name
        ec2_conn = boto.ec2.connect_to_region(region)
        image = ec2_conn.get_all_images([launch_config.image_id])[0]

        url = get_price_url(as_conn.get_launch_config(as_group))
        resp = requests.get(url)
        json_str = str(resp.text.split('callback(')[1])[:-2] # need to remove comments and callback syntax before parsing the broken json
        price_dict = demjson.decode(json_str)['config']['regions']

        regional_prices_json = [ r for r in prices_dict if r['region'] == region ][0]['instanceTypes']
        instance_class_prices_json = [ r for r in regional_prices_json if instance_size in [ e['size'] for e in r['sizes'] ] ][0]['sizes']
        price = float([ e for e in instance_class_prices_json['sizes'] if e['size'] == instance_size ][0]['valueColumns'][0]['prices']['USD'])
        print_verbose("On demand price for %s in %s is %s" % (instance_size, region, price), verbose)
        return price

    except Exception, e:
        handle_exception(e, True)
        sys.exit(1)


def main():
    pass


if __name__ == "__main__":
    sys.exit(main())

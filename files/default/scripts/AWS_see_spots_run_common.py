#!/usr/bin/env python3
'''
Common functions used throughout this cookbook's codebase.
'''
from datetime import datetime, timedelta
import sys
import ast
import boto
from boto import ec2
import requests
import demjson

# common
def dry_run_necessaries(d, v):
    global verbose
    global dry_run
    verbose = False
    dry_run = False
    if d:
        print("This is a dry run. Actions will not be executed and output is verbose.")
        verbose = True
        dry_run = True
    elif v:
        verbose = True
    return verbose, dry_run


def print_verbose(*args):
   if verbose:
        for arg in args:
            print(arg)


def handle_exception(exception):
    exc_traceback = sys.exc_info()[2]
    print("Exception caught on line %s of %s: %s" % 
            (exc_traceback.tb_lineno, exc_traceback.tb_frame.f_code.co_filename, str(exception)))


def get_launch_config(as_group):
    as_group.connection
    return as_group.connection.get_all_launch_configurations(names=[as_group.launch_config_name])[0]


def get_image(as_group):
    try:
        launch_config = get_launch_config(as_group)
        ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
        image = ec2_conn.get_image(launch_config.image_id)
        return image
    except Exception as e:
        handle_exception(e)
        sys.exit(1)
###

# only needed by tagger
def get_tag_dict_value(as_group, tag_key):
    try:
        return ast.literal_eval([ t for t in as_group.tags if t.key == tag_key ][0].value)
    except:
        return False


def get_potential_AZs(as_group):
    try:
        ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
        all_zones = ec2_conn.get_all_zones()
        prices = get_current_spot_prices(as_group)
        return [ z.name for z in all_zones if z.name in list(set([ p.availability_zone for p in prices ])) and z.state == 'available' ]
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_bid(as_group):
    config = get_launch_config(as_group)
    return config.spot_price

###

# only needed by monitor(?)
def get_healthy_AZs(as_group):
    # just parse tags to fetch this
    pass

# for getting specific AZs health. XXX is this needed?
def get_AZ_health(as_group, AZ):
    # returns True or False depending on health (2/3 health checks == 0)
    pass


def get_SSR_groups(as_conn):
    return [ g for g in as_conn.get_all_groups() if [ t for t in g.tags if t.key == 'SSR_enabled' and t.value == 'True' ] ]


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

    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_price_url(launch_config, ec2_conn):
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
        image = ec2_conn.get_image(launch_config.image_id)

        url = get_price_url(launch_config, ec2_conn)
        resp = requests.get(url)
        json_str = str(resp.text.split('callback(')[1])[:-2] # need to remove comments and callback syntax before parsing the broken json
        prices_dict = demjson.decode(json_str)['config']['regions']

        regional_prices_json = [ r for r in prices_dict if r['region'] == region ][0]['instanceTypes']
        instance_class_prices_json = [ r for r in regional_prices_json if launch_config.instance_type in [ e['size'] for e in r['sizes'] ] ][0]['sizes']
        price = float([ e for e in instance_class_prices_json if e['size'] == launch_config.instance_type ][0]['valueColumns'][0]['prices']['USD'])
        print_verbose("On demand price for %s in %s is %s" % (launch_config.instance_type, region, price))
        return price

    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def main():
    pass


if __name__ == "__main__":
    sys.exit(main())

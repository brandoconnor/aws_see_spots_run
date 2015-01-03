'''
Common functions used throughout this cookbook's codebase.
'''
import ast
import boto
import demjson
import random
import requests
import string
import sys
from boto import ec2
from boto.ec2.autoscale import Tag
from boto.exception import BotoServerError
from datetime import datetime, timedelta
from time import sleep
#if sys.version_info[0] == 2:
#    from __future__ import print_function

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
    try:
        return as_group.connection.get_all_launch_configurations(names=[as_group.launch_config_name])[0]
    except BotoServerError as e:
        if e.error_code == 'Throttling':
            print_verbose('Pausing for AWS throttling...')
            sleep(1)
            return get_launch_config(as_group)
        else:
            handle_exception(e)
            sys.exit(1)


def get_image(as_group):
    try:
        launch_config = get_launch_config(as_group)
        ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
        image = ec2_conn.get_image(launch_config.image_id)
        return image

    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def create_tag(as_group, key, value):
    try:
        tag = Tag(key=key,
                    value=value,
                    resource_id=as_group.name)
        print_verbose("Creating tag for %s." % key)
        if dry_run:
            return True
        return as_group.connection.create_or_update_tags([tag])

    except BotoServerError as e: # this often indicates tag limit has been exceeded
        if e.error_code == 'Throttling':
            print_verbose('Pausing for AWS throttling...')
            sleep(1)
            return create_tag(as_group, key, value)
        else:
            handle_exception(e)
            sys.exit(1)


def reload_as_group(as_group):
    try:
        return as_group.connection.get_all_groups([as_group.name])[0]

    except BotoServerError as e:
        if e.error_code == 'Throttling':
            print_verbose('Pausing for AWS throttling...')
            sleep(1)
            return reload_as_group(as_group)

    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def set_tag_dict_value(as_group, tag_key, val_key, value):
    as_group = reload_as_group(as_group)
    tag_val = get_tag_dict_value(as_group, tag_key)
    tag_val[val_key] = value
    create_tag(as_group, tag_key, tag_val)


def get_tag_dict_value(as_group, tag_key):
    try:
        return ast.literal_eval([ t for t in as_group.tags if t.key == tag_key ][0].value)
    except:
        return False # this value needs to be tested each time


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
    try:
        config = get_launch_config(as_group)
        if config.spot_price:
            return config.spot_price
        else:
            return get_tag_dict_value(as_group, 'SSR_config')['original_bid']
    except BotoServerError as e:
        if e.error_code == 'Throttling':
            print_verbose('Pausing for AWS throttling...')
            sleep(1)
            return get_bid(as_group)
        else:
            handle_exception(e)
            sys.exit(1)


def get_AZ_health_list(as_group, AZ):
    return get_tag_dict_value(as_group, 'AZ_status')[AZ]['health']


def set_new_AZ_status_tag(as_group, health_dict):
    try:
        health_values = get_tag_dict_value(as_group, 'AZ_status')
        for k,v in health_dict.items():
            health_values[k]['health'].pop()
            health_values[k]['health'].insert(0, v)
        print_verbose(health_values)
        tag = Tag(key='AZ_status',
                value=health_values,
                resource_id=as_group.name)
        return tag
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_SSR_groups(as_conn):
    try:
        return [ g for g in as_conn.get_all_groups() if 
                [ t for t in g.tags if t.key == 'SSR_config' and get_tag_dict_value(g, 'SSR_config') and get_tag_dict_value(g, 'SSR_config')['enabled'] ] ]
    except BotoServerError as e:
        if e.error_code == 'Throttling':
            print_verbose('Pausing for AWS throttling...')
            sleep(1)
            return get_SSR_groups(as_conn)
        else:
            handle_exception(e)
            sys.exit(1)


def get_ondemand_price(launch_config):
    try:
        region = launch_config.connection.region.name
        ec2_conn = boto.ec2.connect_to_region(region)
        image = ec2_conn.get_image(launch_config.image_id)

        url = get_price_url(launch_config)
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
                instance_type=get_launch_config(as_group).instance_type
                )
        return prices

    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_price_url(launch_config):
    # nabbed URL list from https://github.com/iconara/ec2pricing/blob/master/public/app/ec2pricing/config.js
    base_url = 'http://a0.awsstatic.com/pricing/1/ec2/'

    previous_gen_types = ['m1', 'm2', 'c2', 'cc2', 'cg1', 'cr1', 'hi1']
    if launch_config.instance_type.split('.')[0] in previous_gen_types:
        base_url += 'previous-generation/'

    ec2_conn = boto.ec2.connect_to_region(launch_config.connection.region.name)
    image = ec2_conn.get_image(launch_config.image_id)

    if image.platform == 'windows':
        base_url += 'mswin'
    elif 'SUSE Linux Enterprise Server' in image.description:
        base_url += 'sles'
    else:
        base_url += 'linux'
    url = base_url + '-od.min.js'
    return url


def main():
    pass


if __name__ == "__main__":
    sys.exit(main())

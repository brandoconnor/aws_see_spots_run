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
from collections import Counter
#if sys.version_info[0] == 2:
#    from __future__ import print_function
#XXX move these functions into scripts where not shared

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
    try:
        return as_group.connection.get_all_launch_configurations(names=[as_group.launch_config_name])[0]
    except Exception as e:
        handle_exception(e)
        sleep(1)
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


def create_tag(as_group, key, value):
    sleep(1) #XXX simplest way to avoid throttling problems
    try:
        tag = Tag(key=key,
                    value=value,
                    resource_id=as_group.name)
        print_verbose("Creating tag for %s." % key)
        if dry_run:
            return True
        return as_group.connection.create_or_update_tags([tag])

    except BotoServerError as e: # this often indicates tag limit has been exceeded
        handle_exception(e)

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
    try:
        config = get_launch_config(as_group)
        if config.spot_price:
            return config.spot_price
        else:
            return get_tag_dict_value(as_group, 'SSR_config')['original_bid']
    except Exception as e:
        handle_exception(e)
        sleep(1)
        config = get_launch_config(as_group)
        if config.spot_price:
            return config.spot_price
        else:
            return get_tag_dict_value(as_group, 'SSR_config')['original_bid']
###

# only needed by monitor(?)
def get_healthy_AZs(as_group):
    # just parse tags to fetch this
    pass


# XXX is this needed?
def get_AZ_health_list(as_group, AZ):
    return get_tag_dict_value(as_group, 'AZ_status')[AZ]['health']


def get_new_health_tag(as_group, health_dict):
    try:
        health_values = get_tag_dict_value(as_group, 'AZ_status')
        for k,v in health_dict.items(): 
            health_values[k]['health'].pop()
            health_values[k]['health'].insert(0, v)
        print_verbose(health_values)
        tag = Tag(key='AZ_status',
                value=health_values,
                resource_id=as_group.name)
        #as_group.connection.create_or_update_tags([tag])
        return tag
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_SSR_groups(as_conn):
    return [ g for g in as_conn.get_all_groups() if [ t for t in g.tags if t.key == 'SSR_config' and get_tag_dict_value(g, t.key)['enabled'] ] ]



def throttle_check():
    if throttled:
        sleep(1)


def get_current_spot_prices(as_group):
    try:
        ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)

        start_time = datetime.now() - timedelta(minutes=0)
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


def get_ondemand_price(launch_config, verbose):
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
        return prices # returns a list of ALL spot prices for all AZs

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


def get_ondemand_price(launch_config):
    try:
        region = launch_config.connection.region.name
        ec2_conn = boto.ec2.connect_to_region(region)
        image = ec2_conn.get_all_images([launch_config.image_id])[0]

        url = get_price_url(get_launch_config(as_group))
        resp = requests.get(url)
        json_str = str(resp.text.split('callback(')[1])[:-2] # need to remove comments and callback syntax before parsing the broken json
        price_dict = demjson.decode(json_str)['config']['regions']

        regional_prices_json = [ r for r in prices_dict if r['region'] == region ][0]['instanceTypes']
        instance_class_prices_json = [ r for r in regional_prices_json if instance_size in [ e['size'] for e in r['sizes'] ] ][0]['sizes']
        price = float([ e for e in instance_class_prices_json['sizes'] if e['size'] == instance_size ][0]['valueColumns'][0]['prices']['USD'])
        print_verbose("On demand price for %s in %s is %s" % (instance_size, region, price))
        return price

    except Exception as e:
        handle_exception(e)
        sys.exit(1)



def probably_throwaway_code():
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


def main():
    pass


if __name__ == "__main__":
    sys.exit(main())

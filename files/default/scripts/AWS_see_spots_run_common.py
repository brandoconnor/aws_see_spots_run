#!/usr/bin/env python27
'''
Common functions used throughout this cookbook's codebase.
'''
from datetime import datetime, timedelta
import sys
import ast
import boto
from boto import ec2

def dry_run_necessaries(dry_run, verbose):
    if dry_run:
        print("This is a dry run. Actions will not be executed and output is verbose.")
        verbose = True
    return verbose


def print_verbose(message, verbose):
    if verbose:
        print(message)


def handle_exception(exception):
    exc_traceback = sys.exc_info()[2]
    print_verbose("Exception caught on line %s of %s: %s" % 
            (exc_traceback.tb_lineno, exc_traceback.tb_frame.f_code.co_filename, str(exception)), True)


def get_tag_list(as_group, tag_key):
    # tag values always come back as unicode. This will return a native list.
    # XXX: still needed?
    return ast.literal_eval([ t for t in as_group.tags if t.key == tag_key ][0].value)


def get_tag_json(as_group, tag_key):
    # tag values always come back as unicode. This will return native json.
    # return ast.literal_eval([ t for t in ASG.tags if t.key == tag_key ][0].value)
    # TODO: implement
    return True


def get_potential_AZs(as_group):
    ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
    all_zones = ec2_conn.get_all_zones()
    prices = get_spot_prices(as_group)
    return [ z.name for z in all_zones if z.name in list(set([ p.availability_zone for p in prices ])) and z.state == 'available' ]


def get_healthy_AZs(as_group):
    # just parse tags to fetch this
    pass


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

    except Exception, e:
        handle_exception(e)
        sys.exit(1)


def get_launch_config(as_group):
    return as_group.connection.get_all_launch_configurations(names=[as_group.launch_config_name])[0]


def get_image(as_group):
    launch_config = get_launch_config(as_group)
    ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
    image = ec2_conn.get_all_images([launch_config.image_id])[0]
    return image


def get_bid(as_group):
    config = get_launch_config(as_group)
    return config.spot_price


def get_AZ_health(as_group, AZ):
    # returns True or False depending on health (2/3 health checks == 0)
    pass

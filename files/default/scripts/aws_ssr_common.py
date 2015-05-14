'''
Common functions used throughout this cookbook's codebase.
'''
import ast
import collections
import logging
import os
import sys
from datetime import datetime, timedelta
from time import sleep

import boto
from boto.ec2.autoscale import Tag
from boto.exception import BotoServerError

verbose = False  # keeping the linter happy
dry_run = False


def dry_run_necessaries(d, v):
    global verbose
    global dry_run
    if d:
        print(
            "This is a dry run. Actions will not be executed and output is verbose.")
        verbose = True
        dry_run = True
    elif v:
        verbose = True
    return verbose, dry_run


def set_up_logging():
    logger = logging.getLogger(__name__)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)
    return logger


def print_verbose(filename, log_lvl, *args):
    if verbose:
        log_lvl_map = {"info": 20, "warn": 30, "err": 40, "crit": 50}
        for arg in args:
            logger.log(log_lvl_map[log_lvl], filename + " - " + str(arg))


def handle_exception(exception):
    exc_traceback = sys.exc_info()[2]
    print_verbose(os.path.basename(__file__), 'err', "Exception caught on line %s of %s: %s" %
                  (exc_traceback.tb_lineno, exc_traceback.tb_frame.f_code.co_filename, str(exception)))


def get_launch_config(as_group):
    try:
        return as_group.connection.get_all_launch_configurations(names=[as_group.launch_config_name])[0]
    except BotoServerError as e:
        throttle_response(e)
        return get_launch_config(as_group)


def get_image(as_group):
    try:
        launch_config = get_launch_config(as_group)
        ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
        image = ec2_conn.get_image(launch_config.image_id)
        return image
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def throttle_response(e):
    if e.error_code == 'Throttling':
        print_verbose(
            os.path.basename(__file__), 'warn', 'Pausing for AWS throttling...')
        sleep(1)
    else:
        handle_exception(e)
        sys.exit(1)


def update_tags(as_conn, health_tags):
    try:
        as_conn.create_or_update_tags(health_tags)
    except BotoServerError as e:
        throttle_response(e)
        update_tags(as_conn, health_tags)


def create_tag(as_group, key, value):
    try:
        tag = Tag(key=key, value=value, resource_id=as_group.name)
        print_verbose(
            os.path.basename(__file__), 'info', "Creating tag for %s." % key)
        if dry_run:
            return True
        return as_group.connection.create_or_update_tags([tag])

    # this often indicates tag limit has been exceeded
    except BotoServerError as e:
        throttle_response(e)
        return create_tag(as_group, key, value)


def get_tag_dict_value(as_group, tag_key):
    try:
        return ast.literal_eval([t for t in as_group.tags if t.key == tag_key][0].value)
    except Exception as e:
        handle_exception(e)
        return False  # this value needs to be tested each time


def get_bid(as_group):
    try:
        config = get_launch_config(as_group)
        if config.spot_price:
            return config.spot_price
        else:
            return get_tag_dict_value(as_group, 'ssr_config')['original_bid']
    except BotoServerError as e:
        throttle_response(e)
        return get_bid(as_group)
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def update_az_health_list_tag(as_group, health_dict):
    try:
        health_values = get_tag_dict_value(as_group, 'AZ_status')
        for k, v in health_dict.items():
            health_values[k]['health'].pop()
            health_values[k]['health'].insert(0, v)
        print_verbose(os.path.basename(__file__), 'info', health_values)
        tag = Tag(
            key='AZ_status', value=health_values, resource_id=as_group.name)
        return tag
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def mark_asg_az_disabled(as_group, zone):
    try:
        health_values = get_tag_dict_value(as_group, 'AZ_status')
        health_values[zone]['use'] = False
        print_verbose(os.path.basename(__file__), 'info', health_values)
        tag = Tag(
            key='AZ_status', value=health_values, resource_id=as_group.name)
        return tag
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_ssr_groups(as_conn):
    try:
        return [g for g in as_conn.get_all_groups() if
                [t for t in g.tags if t.key == 'ssr_config' and get_tag_dict_value(g, 'ssr_config') and get_tag_dict_value(g, 'ssr_config')['enabled']]]
    except BotoServerError as e:
        throttle_response(e)
        return get_ssr_groups(as_conn)


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
        for AZ in [x for x, y in collections.Counter([p.availability_zone for p in prices]).items() if y > 1]:
            old_duplicates = [p for p in prices if p.availability_zone == AZ]
            old_duplicates.sort(key=lambda x: x.timestamp)
            for dup in old_duplicates[:1]:
                prices.remove(dup)
        return prices

    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def get_potential_azs(as_group):
    try:
        ec2_conn = boto.ec2.connect_to_region(as_group.connection.region.name)
        all_zones = ec2_conn.get_all_zones()
        prices = get_current_spot_prices(as_group)
        return [z.name for z in all_zones if z.name in list(set([p.availability_zone for p in prices])) and z.state == 'available']
    except Exception as e:
        handle_exception(e)
        sys.exit(1)


def main():
    pass


if __name__ == "__main__":
    sys.exit(main())
else:
    global logger
    logger = set_up_logging()

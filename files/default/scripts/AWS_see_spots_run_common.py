#!/usr/bin/env python3
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
    return ast.literal_eval([ t for t in as_group.tags if t.key == tag_key ][0].value)


def get_tag_json(as_group, tag_key):
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



def get_launch_config(as_group):
    as_group.connection
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


def get_SSR_groups(as_conn):
    return [ g for g in as_conn.get_all_groups() if [ t for t in g.tags if t.key == 'SSR_enabled' and t.value == 'True' ] ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help="Verbose minus action. Default=False")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Print output. Default=False")
    parser.add_argument('-m', '--min_healthy_AZs', default=3, help="Minimum default number of AZs before alternative launch approaches are tried. Default=3")
    sys.exit(main(parser.parse_args()))

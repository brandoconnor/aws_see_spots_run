#!/usr/bin/env python27
'''
Common functions used throughout this cookbook's codebase.
'''
from datetime import datetime, timedelta
import sys
import ast


def dry_run_necessaries(dry_run, verbose):
    if dry_run:
        print("This is a dry run. Actions will not be executed and output is verbose.")
        verbose = True
    return verbose


def print_verbose(message, verbose):
    if verbose:
        print message


def handle_exception(exception):
    exc_traceback = sys.exc_info()[2]
    print_verbose("Exception caught on line %s of %s: %s" % 
            (exc_traceback.tb_lineno, exc_traceback.tb_frame.f_code.co_filename, str(exception)), True)


def get_tag_list(ASG, tag_key):
    # tag values always come back as unicode. This will return a native list.
    # XXX: still needed?
    return ast.literal_eval([ t for t in ASG.tags if t.key == tag_key ][0].value)


def get_tag_json(ASG, tag_key):
    # tag values always come back as unicode. This will return native json.
    # return ast.literal_eval([ t for t in ASG.tags if t.key == tag_key ][0].value)
    # TODO: implement
    return True

def get_AZs(instance_type, bid_price, product_description, ec2_conn):
    start_time = datetime.utcnow() - timedelta(minutes=5)
    start_time = start_time.isoformat()
    end_time = datetime.utcnow().isoformat()
    prices = ec2_conn.get_spot_price_history(product_description=product_description, end_time=end_time, start_time=start_time, instance_type=instance_type)
    print(instance_type, bid_price, prices) #XXX remove when dev is done
    AZs = [ sp.availability_zone for sp in prices if sp.price < bid_price ]
    return list(set(AZs))


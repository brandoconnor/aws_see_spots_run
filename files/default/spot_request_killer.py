#!/usr/bin/env python27
'''
Script kills old spot request which are unlikely to be fulfilled and stick,
thus potentially shifting the request to a more sustainable AZ.
'''
import argparse
import boto.ec2
import sys
import datetime


def main(args):
    try:
        for region in [ 'us-east-1', 'us-west-2' ]:
            ec2_conn = boto.ec2.connect_to_region(region)
            pending_requests = []
            for status in ['capacity-not-available', 'capacity-oversubscribed', 'price-too-low', 'not-scheduled-yet', 'launch-group-constraint', 'az-group-constraint', 'placement-group-constraint', 'constraint-not-fulfillable' ]:
                pending_requests.append(ec2_conn.get_all_spot_instance_requests(filters={'status-code': status}))
            oldest_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=args.minutes)
            # flattening the list of lists here
            pending_requests = [item for sublist in pending_requests for item in sublist]
            for request in pending_requests:
                if oldest_time > datetime.datetime.strptime(request.create_time, "%Y-%m-%dT%H:%M:%S.000Z"):
                    print "Killing request %s" % str(request.id)
                    request.cancel()
                else:
                    print "Request %s not older than %s minutes. Passing." % (str(request.id), str(args.minutes))
                    pass
            print "Region %s pass complete." % region

    except Exception, e:
        print "Exception caught: %s" % str(e)
        sys.exit(1)

    exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Arrrrrrrgs.")
    parser.add_argument('-m', '--minutes', type=int, default=6, help="Minutes before a spot request is considered stale. Default: 10")
    parser.add_argument('-r', '--region', default='us-east-1', help="AWS region to use. Default=us-east-1")
    sys.exit(main(parser.parse_args()))

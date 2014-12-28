#
# Cookbook Name:: AWS_see_spots_run
# Attributes:: default
#

default['AWS_see_spots_run']['exec_path'] = '/usr/local/bin/'

# all ['interval'] attributes are measured in minutes
default['AWS_see_spots_run']['spot_request_killer']['interval'] = 5
default['AWS_see_spots_run']['spot_request_killer']['minutes_before_stale'] = 10

default['AWS_see_spots_run']['price_monitor']['interval'] = 10

default['AWS_see_spots_run']['ASG_tagger']['demand_expiration'] = 55
default['AWS_see_spots_run']['ASG_tagger']['min_healthy_AZs'] = 3

default['AWS_see_spots_run']['excluded_regions'] = [ 'cn-north-1', 'us-gov-west-1' ]

# future feature:
# a maximum bid for any given node class is automatically set to the on demand price but this can be raised manually.
## This automatic cap can be overridden below:
## need to pass this as an argument to the price_adjuster.py
#
# default['AWS_see_spots_run']['price_cap'] = { 'us-east-1' => { 'm3.medium' => '.24' } }

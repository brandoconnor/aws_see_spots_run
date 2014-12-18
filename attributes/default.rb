#
# Cookbook Name:: AWS_see_spots_run
# Attributes:: default
#

default['AWS_see_spots_run']['exec_path'] = '/usr/local/bin/'

default['AWS_see_spots_run']['spot_request_killer_interval'] = 5
default['AWS_see_spots_run']['spot_request_killer']['minutes_before_stale'] = 6
# maybe this calls the price adjuster
default['AWS_see_spots_run']['ASG_AZ_adjuster_interval'] = 30

default['AWS_see_spots_run']['price_adjuster_interval'] = 10

# a maximum bid for any given node class is automatically set to 4x the on demand price as this limit is AWS imposed.
## This automatic cap can be overridden below:
## need to pass this as an argument to the price_adjuster.py
default['AWS_see_spots_run']['price_cap'] = { 'us-east-1' => { 'm3.medium' => '.24' } }

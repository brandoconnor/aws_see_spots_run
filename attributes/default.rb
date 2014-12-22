#
# Cookbook Name:: AWS_see_spots_run
# Attributes:: default
#

# all _interval attributes here are measured in minutes
default['AWS_see_spots_run']['exec_path'] = '/usr/local/bin/'

default['AWS_see_spots_run']['spot_request_killer_interval'] = 5
default['AWS_see_spots_run']['sr_killer_minutes_before_stale'] = 10

default['AWS_see_spots_run']['spot_price_monitor_interval'] = 10

default['AWS_see_spots_run']['check_demand_instances_to_kill_interval'] = 55

# when minimum is reached, price will be increased until minimum is met or we move to demand
default['AWS_see_spots_run']['min_healthy_AZs'] = 3

# future feature:
# a maximum bid for any given node class is automatically set to the on demand price but this can be raised manually.
## This automatic cap can be overridden below:
## need to pass this as an argument to the price_adjuster.py
#
# default['AWS_see_spots_run']['price_cap'] = { 'us-east-1' => { 'm3.medium' => '.24' } }

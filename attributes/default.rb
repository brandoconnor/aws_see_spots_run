#
# Cookbook Name:: AWS_see_spots_run
# Attributes:: default
#

default['AWS_see_spots_run']['exec_path'] = '/usr/local/bin/'
default['AWS_see_spots_run']['excluded_regions'] = 'cn-north-1 us-gov-west-1'

default['AWS_see_spots_run']['spot_request_killer']['interval'] = 2
default['AWS_see_spots_run']['spot_request_killer']['minutes_before_stale'] = 8

default['AWS_see_spots_run']['price_monitor']['interval'] = 5

default['AWS_see_spots_run']['ASG_tagger']['interval'] = 30
default['AWS_see_spots_run']['ASG_tagger']['min_healthy_AZs'] = 1

default['AWS_see_spots_run']['health_enforcer']['interval'] = 10
default['AWS_see_spots_run']['health_enforcer']['demand_expiration'] = 50
default['AWS_see_spots_run']['health_enforcer']['min_health_threshold'] = 3 # the number of healthy responses (0's) required to call an AZ healthy (options: 3, 2, 1)

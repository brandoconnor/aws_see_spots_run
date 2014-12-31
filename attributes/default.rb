#
# Cookbook Name:: AWS_see_spots_run
# Attributes:: default
#

default['AWS_see_spots_run']['exec_path'] = '/usr/local/bin/'
default['AWS_see_spots_run']['min_healthy_AZs'] = 3
default['AWS_see_spots_run']['excluded_regions'] = [ 'cn-north-1', 'us-gov-west-1','us-east-1' ] #XXX include east-1 when everything is solid

default['AWS_see_spots_run']['spot_request_killer']['interval'] = 5
default['AWS_see_spots_run']['spot_request_killer']['minutes_before_stale'] = 10

default['AWS_see_spots_run']['price_monitor']['interval'] = 10

default['AWS_see_spots_run']['ASG_tagger']['interval'] = 30

default['AWS_see_spots_run']['health_enforcer']['interval'] = 10
default['AWS_see_spots_run']['health_enforcer']['demand_expiration'] = 50


#
# Cookbook Name:: aws_see_spots_run
# Recipe:: cron_jobs
#
# Copyright 2015, DreamBox Learning, Inc.
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

include_recipe 'aws_see_spots_run::packages'
exclude_regions = "-e #{node['aws_see_spots_run']['excluded_regions']}"
exec_path = "#{node['aws_see_spots_run']['exec_path']}/"

cron 'asg_tagger' do
  command "#{exec_path}asg_tagger.py #{exclude_regions} -m #{node['aws_see_spots_run']['asg_tagger']['min_healthy_AZs']}"
  minute "*/#{node['aws_see_spots_run']['asg_tagger']['interval']}"
end

cron 'spot_request_killer' do
  command "#{exec_path}spot_request_killer.py #{exclude_regions} -m #{node['aws_see_spots_run']['spot_request_killer']['minutes_before_stale']}"
  minute "*/#{node['aws_see_spots_run']['spot_request_killer']['interval']}"
end

cron 'spot_health_enforcer' do
  command "#{exec_path}health_enforcer.py #{exclude_regions} -x #{node['aws_see_spots_run']['health_enforcer']['demand_expiration']} -m #{node['aws_see_spots_run']['health_enforcer']['min_health_threshold']}"
  minute "*/#{node['aws_see_spots_run']['health_enforcer']['interval']}"
end

cron 'spot_price_monitor' do
  command "#{exec_path}price_monitor.py #{exclude_regions}"
  minute "*/#{node['aws_see_spots_run']['price_monitor']['interval']}"
end

cron 'remove_old_launch_configs' do
  command "#{exec_path}remove_old_launch_configs.py #{exclude_regions}"
  hour '0'
end

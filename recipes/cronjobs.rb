#
# Cookbook Name:: AWS_see_spots_run
# Recipe:: cronjobs
#
# Copyright 2014, DreamBox Learning, Inc.
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
#


include_recipe  "cronwrappy"
cron_wrapper = node['cronwrappy']['wrapper_exec']

include_recipe  "python::pip"

python_packages = ['argparse','boto','requests', 'demjson',]
python_packages.each do |pkg|
  python_pip pkg
end

remote_directory "scripts" do
  path node['AWS_see_spots_run']['exec_path']
  files_mode 0755
  files_backup 0
end

cron "ASG_tagger" do
  command "#{cron_wrapper} -v -d -f ASG_tagger -c 'python27 #{node['AWS_see_spots_run']['exec_path']}ASG_tagger.py -e #{node['AWS_see_spots_run']['excluded_regions']} -m #{node['AWS_see_spots_run']['ASG_tagger']['min_healthy_AZs']} -v'"
  minute "*/#{node['AWS_see_spots_run']['ASG_tagger']['interval']}"
end

cron "spot_request_killer" do
  command "#{cron_wrapper} -v -d -f spot_request_killer -c 'python27 #{node['AWS_see_spots_run']['exec_path']}spot_request_killer.py -e #{node['AWS_see_spots_run']['excluded_regions']} -m #{node['AWS_see_spots_run']['spot_request_killer']['minutes_before_stale']} -v'"
  minute "*/#{node['AWS_see_spots_run']['spot_request_killer']['interval']}"
end

cron "spot_health_enforcer" do
  command "#{cron_wrapper} -v -d -f spot_health_enforcer -c 'python27 #{node['AWS_see_spots_run']['exec_path']}health_enforcer.py -e #{node['AWS_see_spots_run']['excluded_regions']} -x #{node['AWS_see_spots_run']['health_enforcer']['demand_expiration']} -m #{node['AWS_see_spots_run']['health_enforcer']['min_health_threshold']} -v'"
  minute "*/#{node['AWS_see_spots_run']['health_enforcer']['interval']}"
end

cron "spot_price_monitor" do
  command "#{cron_wrapper} -v -d -f spot_price_monitor -c 'python27 #{node['AWS_see_spots_run']['exec_path']}price_monitor.py -e #{node['AWS_see_spots_run']['excluded_regions']} -v'"
  minute "*/#{node['AWS_see_spots_run']['price_monitor']['interval']}"
end

cron "remove_old_launch_configs" do
  command "#{cron_wrapper} -v -d -f remove_old_launch_configs -c 'python27 #{node['AWS_see_spots_run']['exec_path']}remove_old_launch_configs.py -e #{node['AWS_see_spots_run']['excluded_regions']} -v'"
  hour "0"
end

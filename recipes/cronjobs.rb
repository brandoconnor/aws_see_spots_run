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

include_recipe  "python::pip"

python_packages = ['argparse','boto','requests', 'demjson', 'ast' ]
python_packages.each do |pkg|
    python_pip pkg do
        action  :install
    end
end

remote_directory "scripts" do
    path            node['AWS_see_spots_run']['exec_path']
    files_mode      0755
    files_backup    0
end

cron "ASG_tagger" do
  command "#{node['AWS_see_spots_run']['exec_path']}ASG_tagger.py -e #{node['AWS_see_spots_run']['excluded_regions']} -m #{node['AWS_see_spots_run']['min_healthy_AZs']}"
  minute "*/#{node['AWS_see_spots_run']['ASG_tagger']['interval']}"
end

cron "spot_request_killer" do
  command "#{node['AWS_see_spots_run']['exec_path']}spot_request_killer.py -e #{node['AWS_see_spots_run']['excluded_regions']} -m #{node['AWS_see_spots_run']['spot_request_killer']['minutes_before_stale']}"
  minute "*/#{node['AWS_see_spots_run']['spot_request_killer']['interval']}"
end

cron "spot_health_enforcer" do
  command "#{node['AWS_see_spots_run']['exec_path']}health_enforcer.py -e #{node['AWS_see_spots_run']['excluded_regions']} -x #{node['AWS_see_spots_run']['health_enforcer']['demand_expiration']} -m #{node['AWS_see_spots_run']['min_healthy_AZs']}"
  minute "*/#{node['AWS_see_spots_run']['health_enforcer']['interval']}"
end

cron "spot_price_monitor" do
  command "#{node['AWS_see_spots_run']['exec_path']}price_monitor.py -e #{node['AWS_see_spots_run']['excluded_regions']}"
  minute "*/#{node['AWS_see_spots_run']['price_monitor']['interval']}"
end

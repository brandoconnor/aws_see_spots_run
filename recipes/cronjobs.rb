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

remote_directory "scripts" do
    path            node['AWS_see_spots_run']['exec_path']
    files_mode      0755
    files_backup    0
end

cron "ASG_AZ_adjuster" do
  command "#{node['AWS_see_spots_run']['exec_path']}ASG_AZ_adjuster.py"
  minute node['AWS_see_spots_run'][ 'ASG_adjuster_interval']
end

cron "spot_request_killer" do
  command "#{node['AWS_see_spots_run']['exec_path']}spot_request_killer.py -m #{node['AWS_see_spots_run']['spot_request_killer']['minutes_before_stale']}"
  minute node['AWS_see_spots_run'][ 'spot_request_killer_interval']
end

#cron "price_adjuster" do
#  command "#{node['AWS_see_spots_run']['exec_path']}price_adjuster.py "
#  minute node['AWS_see_spots_run'][ 'price_adjuster_interval']
#end
#
#cron "ASG_tagger" do
#  command "#{node['AWS_see_spots_run']['exec_path']}ASG_tagger.py "
#  minute node['AWS_see_spots_run'][ 'price_adjuster_interval']
#end

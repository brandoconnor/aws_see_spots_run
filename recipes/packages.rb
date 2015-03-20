#
# Cookbook Name:: aws_see_spots_run
# Recipe:: packages
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

include_recipe 'python::pip'

python_packages = %w(argparse boto requests demjson)
python_packages.each do |pkg|
  python_pip pkg
end

remote_directory 'scripts' do
  path node['aws_see_spots_run']['exec_path']
  files_mode 0755
  files_backup 0
end

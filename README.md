# AWS_see_spots_run Cookbook

## Description

A chef cookbook to manage Amazon Web Services spot instances within autoscaling groups via Chef, cron jobs, AWS APIs, glitter, and magic.

See the [wiki](https://github.com/dreamboxlearning/AWS_see_spots_run/wiki) for details. AWS_SSR is officially released [on the chef supermarket](https://supermarket.chef.io/cookbooks/aws_see_spots_run).

## Attributes
<table>
  <tr>
    <th>Key</th>
    <th>Type</th>
    <th>Description</th>
    <th>Default</th>
  </tr>
  <tr>
    <td><tt>['AWS_see_spots_run']['exec_path']</tt></td>
    <td><tt>['AWS_see_spots_run']['excluded_regions']</tt></td>
    <td><tt>['AWS_see_spots_run']['spot_request_killer']['interval']</tt></td>
    <td><tt>['AWS_see_spots_run']['spot_request_killer']['minutes_before_stale']</tt></td>
    <td><tt>['AWS_see_spots_run']['price_monitor']['interval']</tt></td>
    <td><tt>['AWS_see_spots_run']['ASG_tagger']['interval']</tt></td>
    <td><tt>['AWS_see_spots_run']['ASG_tagger']['min_healthy_AZs']</tt></td>
    <td><tt>['AWS_see_spots_run']['health_enforcer']['interval']</tt></td>
    <td><tt>['AWS_see_spots_run']['health_enforcer']['demand_expiration']</tt></td>
    <td><tt>['AWS_see_spots_run']['health_enforcer']['min_health_threshold']</tt></td>

Attribute | Description | Type | Default
----------|-------------|------|--------
`['exec_path']` | Description | String | ``
`['excluded_regions']` |  |  | ``
`['spot_request_killer']['interval']` |  |  | ``
`` |  |  | ``
`` |  |  | ``
`` |  |  | ``
`` |  |  | ``
`` |  |  | ``
`` |  |  | ``


## Platforms
* Tested on Amazon Linux with Chef 11.12.8 and should be widely compatible with any Linux flavor and modern Chef client.

## Bugs / Development / Contributing
* Report issues/questions/feature requests on in the [Issues](https://github.com/dreamboxlearning/AWS_see_spots_run/issues) section.
* Feel free to ask questions via email.

Pull requests are welcome!
Ideally create a topic branch for every separate change you make.
For example:

1. Fork the repo
2. Create your feature branch (`git checkout -b my-new-feature`)
3. If possible, write some tests.
4. Commit your awesome changes (`git commit -am 'Added some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create a new Pull Request and tell us about it your changes.

## LICENSE
Copyright 2015 Dreambox Learning, Inc.

Licensed under the Apache License, Version 2.0 (the “License”); you may not use this file except in
compliance with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is
distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied. See the License for the specific language governing permissions and limitations under the
License.

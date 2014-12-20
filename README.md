# AWS_see_spots_run Cookbook

## Description

A cookbook to manage AWS spot EC2 instances within autoscaling groups via Chef, cronjobs, and magic.

- http://aws.amazon.com/ec2/purchasing-options/spot-instances/

## Platforms

* Tested on Amazon Linux with Chef 11.12.8

## Attributes
- `node['AWS_see_spots_run']['spot_request_killer_interval']` - sets the interval (in minutes) to run the spot request killer
- `node['AWS_see_spots_run']['ASG_adjuster_interval']` - sets the interval (in minutes) to move ASGs away from AZs where multiple failures are seen
- `node['AWS_see_spots_run']['LC_price_adjuster'_interval']` - sets the interval (in minutes) to run the launch configuration price adjuster
- `TODO: include a hash attribute to give caps to prices for instance types per region`

## Recipes
### default

No-op, assuming cookbook inclusion in a custom wrapper.

### cronjobs

Drops files on the system and installs cronjobs.

## Files
### spot_request_killer.py

### ASG_AZ_adjuster.py

### price_adjuster.py

### ASG_tagger.py

### ec2instancespricing.py

### AWS_see_spots_run_common.py

## Usage

Feel free to ask questions via email.


## Development / Contributing

* Source hosted at [GitHub][repo]
* Report issues/questions/feature requests on [GitHub Issues][issues]

Pull requests are very welcome! Make sure your patches are well tested.
Ideally create a topic branch for every separate change you make. For
example:

1. Fork the repo
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Write some tests, see [ChefSpec](https://github.com/sethvargo/chefspec)
4. Commit your awesome changes (`git commit -am 'Added some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create a new Pull Request and tell us about it your changes.

# TODO

## add code for LC price adjuster
## introduce dry run capability to each script
## rubocop, food critic, ChefSpec, testing, ect

# Sticky considerations
## AZs with ELBs, do we need to change their AZs also?

# potential features:
## instance_type_adjuster


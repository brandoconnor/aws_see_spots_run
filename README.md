# AWS_see_spots_run Cookbook

## Description

A cookbook to manage AWS spot EC2 instances within autoscaling groups via Chef, cronjobs, and magic.

- http://aws.amazon.com/ec2/purchasing-options/spot-instances/

## Platforms

* Tested on Amazon Linux

## Attributes
- `node['AWS_see_spots_run']['spot_kill_interval']` - 
- `node['AWS_see_spots_run']['adjust_AZs_interval']` - 
- `node['AWS_see_spots_run']['adjust_prices_interval']` - 
- `TODO: include a hash attribute to give caps to prices for instance types per region`

## Recipes
### default

No-op, assuming cookbook inclusion in a custom wrapper.

### cronjobs

Drops files on the system and installs cronjobs.

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


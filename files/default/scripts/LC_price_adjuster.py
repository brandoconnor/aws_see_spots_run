#!/usr/bin/env python27
'''
Changes the bid price to either specified value or
This is the only script of the bunch that isn't run on a schedule.
'''
import boto
import random
import string
import sys
from AWS_see_spots_run_common import *
from  boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.exception import EC2ResponseError, BotoServerError

# NOTE: when flipping to ondemand, I think a special state is required where all potential AZs are added back.

def main():
    pass


def recreate_LC(as_group, new_bid, dry_run, verbose):
    try:
        old_launch_config = get_launch_config(as_group)
        new_launch_config_name = old_launch_config.name[:-13] + id_generator()

        launch_config = LaunchConfiguration( 
            image_id = old_launch_config.image_id,
            key_name = old_launch_config.key_name,
            security_groups = old_launch_config.security_groups,
            user_data = old_launch_config.user_data,
            instance_type = old_launch_config.instance_type,
            kernel_id = old_launch_config.kernel_id,
            ramdisk_id = old_launch_config.ramdisk_id,
            block_device_mappings = old_launch_config.block_device_mappings,
            instance_monitoring = old_launch_config.instance_monitoring.enabled,
            instance_profile_name = old_launch_config.instance_profile_name,
            ebs_optimized = old_launch_config.ebs_optimized,
            associate_public_ip_address = old_launch_config.associate_public_ip_address,
            volume_type = old_launch_config.volume_type,
            delete_on_termination = old_launch_config.delete_on_termination,
            iops = old_launch_config.iops,
            use_block_device_types = old_launch_config.use_block_device_types,
            spot_price = new_bid, # new values
            name = new_launch_config_name,
            )

        as_groups = [ a for a in as_group.connection.get_all_groups() if old_launch_config.name == a.launch_config_name ]
        for as_group in as_groups:
            #setattr(as_group, launch_config_name, launch_config.name)
            as_group.launch_config_name = launch_config.name
            if not dry_run:
                print_verbose("Created LC %s with price %s and applying to ASG %s" % 
                        (launch_config.name , new_bid, as_group_name), verbose)
                as_group.update()
            else:
                print_verbose("Created LC %s with price %s but NOT applying to ASG %s" % 
                        (launch_config.name , new_bid, as_group_name), True)

        #TODO: delete old LC?
        print_verbose("Autoscaling group launch configuration update complete.", verbose)

    except EC2ResponseError, e:
        handle_exception(e)
        pass

    except BotoServerError, e:
        handle_exception(e)
        pass

    except Exception, e:
        handle_exception(e)
        return 1


def id_generator(size=10, chars=string.ascii_uppercase + string.digits):
    return 'SSR' + ''.join(random.choice(chars) for _ in range(size))

if __name__ == "__main__":
    sys.exit(main()) 

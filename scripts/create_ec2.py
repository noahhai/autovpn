from __future__ import print_function

import time
import boto
import boto.ec2
import sys
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

keyname=sys.argv[1]
instance_type=sys.argv[2]
region=sys.argv[3]
ami=sys.argv[4]
port=sys.argv[5]
if region:
    conn_region = boto.ec2.connect_to_region(region)
else:
    conn_region = boto.connect_ec2()

def auto_vpn(ami=ami,
                    instance_type=instance_type,
                    key_name=keyname,
                   	group_name="vpn_2",
                    ssh_port="22",
                    vpn_port=port,
                    cidr="0.0.0.0/0",
                    tag="auto_vpn",
                    user_data=None):
	

    ec2 = conn_region 
 
    try:
        group = ec2.get_all_security_groups(groupnames=[group_name])[0]
    except ec2.ResponseError, e:
        if e.code == 'InvalidGroup.NotFound':
            group = ec2.create_security_group(group_name,
                                                'A group that allows VPN access')
            group.authorize('tcp',ssh_port,ssh_port,cidr)
            group.authorize('udp',vpn_port,vpn_port,cidr)
        else:
            raise

    if int(port) != int(1194):
        try:
            mgroup = ec2.get_all_security_groups(groupnames=[group_name])[0]
            mgroup.authorize('udp',vpn_port,vpn_port,cidr)
        except ec2.ResponseError, e:
            if e.code == 'InvalidPermission.Duplicate':
                '''fail here'''
            else: 
                raise

    spot_request = ec2.request_spot_instances(
        price="0.005",
        count=1,
        image_id=ami,
        key_name=key_name,
        security_groups=[group_name],
        instance_type=instance_type,
        user_data=user_data,
        )[0]

    while True:
        eprint("Waiting. spot request status: '%s', state: '%s'" % (spot_request.state, spot_request.status.code))
        if spot_request.state == 'active' and spot_request.status.code == 'fulfilled':
            break
        time.sleep(10)
        spot_request = ec2.get_all_spot_instance_requests(request_ids=[spot_request.id])[0]
    while True:
        instance = ec2.get_all_instances(instance_ids=[spot_request.instance_id])[0].instances[0]
        eprint("Waiting. spot instance state: '%s'" % instance.state)
        if instance.state == 'running':
            break
        time.sleep(10)


    ec2.create_tags([instance.id], {tag:""})

    global host
    instance = ec2.get_all_instances(instance_ids=[spot_request.instance_id])[0].instances[0]
    host = instance.ip_address
    print("%s" % host)
	

if __name__ == "__main__":
    auto_vpn()
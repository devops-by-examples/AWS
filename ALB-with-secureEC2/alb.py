import boto3
import time

ec2 = boto3.resource('ec2')
client = boto3.client('ec2')
user_data_script = """#!/bin/bash
yum clean all
yum update -y
yum install httpd -y
echo "Hello this is test website" >> /var/www/html/index.html
systemctl start httpd
systemctl restart httpd
systemctl enable httpd"""


# create a file to store the key locally
outfile = open('test-ec2-keypair.pem','w')
# call the boto ec2 function to create a key pair
key_pair = ec2.create_key_pair(KeyName='test-ec2-keypair')
# capture the key and store it in a file
KeyPairOut = str(key_pair.key_material)
outfile.write(KeyPairOut)


def awslogin():
    session = boto3.Session(
        aws_access_key_id="XXXXX",
        aws_secret_access_key="XXXX",
    )
    return session


def create_security_group(descript, group_name, vpc_id):
    sg1_response = client.create_security_group(Description=descript, GroupName=group_name, VpcId=vpc_id)
    return sg1_response


def create_instances(subnet_name, instance_name):
    web_instance = ec2.create_instances(ImageId='ami-0e1d30f2c40c4c701', InstanceType='t2.micro', MinCount=1,
                                        MaxCount=1, KeyName='test-ec2-keypair', SubnetId=subnet_name, UserData=user_data_script,
                                        SecurityGroupIds=[sgId], TagSpecifications=[
            {'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': instance_name}]}])
    return web_instance


def get_ec2id(data):
    for reservation in data["Reservations"]:
        for instance in reservation["Instances"]:
            ec2 = boto3.resource('ec2')
            response = ec2.Instance(instance["InstanceId"])
    return response


def vpc_creation():
    # Create VPC
    response = client.create_vpc(CidrBlock='172.16.0.0/16', InstanceTenancy='default')
    # Assign tags to VPC
    client.create_tags(Resources=[response['Vpc']['VpcId']], Tags=[{'Key': 'Name', 'Value': 'test-vpc', }])
    print('***** VPC Created with ID*********', response['Vpc']['VpcId'])
    vpc_id = response['Vpc']['VpcId']
    return vpc_id


def create_ig(vpc_id):
    ig = ec2.create_internet_gateway()
    client.attach_internet_gateway(InternetGatewayId=ig.id, VpcId=vpc_id)
    return ig

def create_tag_for_route_table(route_table_number, route_table_name):
    tag = client.create_tags(Resources=[route_table_number['RouteTable']['RouteTableId']],Tags=[{'Key': 'Name','Value': route_table_name}])
    return tag
# create subnets
def create_subnet(cidr, vpc_id, azname):
    subnet_response = client.create_subnet(CidrBlock=cidr, VpcId=vpc_id, AvailabilityZone=azname)
    return subnet_response


def create_sg_tag(websg_or_elbsg, sg_group_name):
    sg_tag_response = client.create_tags(Resources=[websg_or_elbsg['GroupId']],
                                         Tags=[{'Key': 'Name', 'Value': sg_group_name}])
    return sg_tag_response


# def create_tag(subnet_number, subnet_name):
# client.create_tags(Resources=[subnet_number['Subnet']['SubnetId']], Tags=[{'Key': 'Name', 'Value': subnet_name}])


def create_alb(ec2_subnet2, ec2_subnet4, ec2_subnet6, elbsgId):
    lb = boto3.client('elbv2')
    lb_response = lb.create_load_balancer(
        Name='test-alb',
        Subnets=[
            ec2_subnet2, ec2_subnet4, ec2_subnet6,
        ],
        SecurityGroups=[
            elbsgId,
        ],
        Scheme='internet-facing',
        Tags=[
            {
                'Key': 'Name',
                'Value': 'test-alb'
            },
        ],
        Type='application',
        IpAddressType='ipv4'
    )
    lbId = lb_response['LoadBalancers'][0]['LoadBalancerArn']
    print('Successfully created load balancer - ', lbId)
    return lb, lbId


def create_tg(lb, vpc_id):
    create_tg_response = lb.create_target_group(
        Name='test-web-tg',
        Protocol='HTTP',
        Port=80,
        TargetType='instance',
        HealthCheckPath='/index.html',
        VpcId=vpc_id
    )
    tgId = create_tg_response['TargetGroups'][0]['TargetGroupArn']
    print('Successfully created target group - ', tgId)
    return tgId

def createlistner(lb, lbId, tgId):
    listnerId = lb.create_listener(
        LoadBalancerArn=lbId,
        Protocol='HTTP',
        Port=80,
        DefaultActions=[
            {
                'Type': 'forward',
                'TargetGroupArn': tgId
            },
        ]
    )
def regis_targets(lb, tgId, instance1, instance2, instance3):
    register_targets = lb.register_targets(TargetGroupArn=tgId, Targets=[{'Id': instance1.id, },
                                                                      {'Id': instance2.id, },
                                                                      {'Id': instance3.id, },
                                                                         ],)

if __name__ == '__main__':
    session = awslogin()
    vpc_id = vpc_creation()
    ig = create_ig(vpc_id)
    routetable1_response = client.create_route_table(VpcId=vpc_id)
    tag = create_tag_for_route_table(routetable1_response, 'test-rt1')
    print('Route Table 1 Created - ', routetable1_response['RouteTable']['RouteTableId'])
    route_table1 = ec2.RouteTable(routetable1_response['RouteTable']['RouteTableId'])
    #route_table1.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=ig.id)
    # Create Security Group for EC2 instances which will accept traffic from ALB
    ec2_sg1 = create_security_group('Accept traffic from ALB', 'test-ec2-sg', vpc_id)
    sgId = ec2_sg1['GroupId']
    create_sg_tag(ec2_sg1, 'test-ec2-sg')
    print('Created Security Group for EC2 Web Instances -', sgId)
    web1 = ec2.SecurityGroup(sgId)
    web1.authorize_ingress(GroupId=sgId, IpPermissions=[
        {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}])
    web1.authorize_ingress(GroupId=sgId, IpPermissions=[
        {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '172.31.0.0/16'}]}])

    client.authorize_security_group_ingress(GroupId=sgId, IpPermissions=[
        {'IpProtocol': '-1', 'UserIdGroupPairs': [{'GroupId': sgId}]}])

    # Create Security for ALB which will accept traffic from Internet
    elb_sg1 = create_security_group('Accept traffic from Internet', 'test-alb-sg', vpc_id)
    elbsgId = elb_sg1['GroupId']
    create_sg_tag(elb_sg1, 'test-alb-sg')
    print('Created Security Group for ELB -', elbsgId)
    elb1 = ec2.SecurityGroup(elbsgId)
    elb1.authorize_ingress(GroupId=elbsgId, IpPermissions=[
        {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}])

    client.authorize_security_group_ingress(GroupId=elbsgId, IpPermissions=[
        {'IpProtocol': '-1', 'UserIdGroupPairs': [{'GroupId': elbsgId}]}])
    subnet1 = create_subnet('172.16.1.0/24', vpc_id, 'us-east-1a')
    subnet2 = create_subnet('172.16.2.0/24', vpc_id, 'us-east-1a')
    subnet3 = create_subnet('172.16.3.0/24', vpc_id, 'us-east-1b')
    subnet4 = create_subnet('172.16.4.0/24', vpc_id, 'us-east-1b')
    subnet5 = create_subnet('172.16.5.0/24', vpc_id, 'us-east-1c')
    subnet6 = create_subnet('172.16.6.0/24', vpc_id, 'us-east-1c')

    ec2_subnet1 = subnet1['Subnet']['SubnetId']
    route_table1.associate_with_subnet(SubnetId=ec2_subnet1)
    ec2_subnet3 = subnet3['Subnet']['SubnetId']
    route_table1.associate_with_subnet(SubnetId=ec2_subnet3)
    ec2_subnet5 = subnet5['Subnet']['SubnetId']
    route_table1.associate_with_subnet(SubnetId=ec2_subnet5)
    routetable2_response = client.create_route_table(VpcId=vpc_id)
    tag = create_tag_for_route_table(routetable2_response, 'test-rt2')
    print('Route Table 2 Created - ', routetable2_response['RouteTable']['RouteTableId'])
    route_table2 = ec2.RouteTable(routetable2_response['RouteTable']['RouteTableId'])
    route_table2.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=ig.id)
    ec2_subnet2 = subnet2['Subnet']['SubnetId']
    route_table2.associate_with_subnet(SubnetId=ec2_subnet2)
    ec2_subnet4 = subnet4['Subnet']['SubnetId']
    route_table2.associate_with_subnet(SubnetId=ec2_subnet4)
    ec2_subnet6 = subnet6['Subnet']['SubnetId']
    route_table2.associate_with_subnet(SubnetId=ec2_subnet6)
    instance_1 = create_instances(ec2_subnet1, 'test1')
    time.sleep(60)
    response1 = client.describe_instances()
    instance1 = get_ec2id(response1)
    print('Launching ec2 instance1 - ', instance1.id)
    instance_2 = create_instances(ec2_subnet3, 'test2')
    time.sleep(60)
    response2 = client.describe_instances()
    instance2 = get_ec2id(response2)
    print('Launching ec2 instance2 - ', instance2.id)
    instance_3 = create_instances(ec2_subnet5, 'test3')
    time.sleep(60)
    response3 = client.describe_instances()
    instance3 = get_ec2id(response3)
    print('Launching ec2 instance3 - ', instance3.id)
    lb, lbId = create_alb(ec2_subnet2, ec2_subnet4, ec2_subnet6, elbsgId)
    tgId = create_tg(lb, vpc_id)
    createlistner(lb, lbId, tgId)
    regis_targets(lb, tgId, instance1, instance2, instance3)

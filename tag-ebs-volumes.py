import json
import boto3
import botocore
import os
import sys


def get_required_tags(rulename):
    client = boto3.client('config')
    rules_details=client.describe_config_rules(
    ConfigRuleNames=rulename
    )
    #required tags
    required_tags=rules_details['ConfigRules'][0]['InputParameters']
    tags_as_json=json.loads(required_tags)
    items=tags_as_json.items()
    #print(items)
    #the tag config can include tag names and tag values
    #we only want to know required keynames as these are the names of required tags
    returned_tag_names = {v for (k,v) in items if 'Key' in k}
    print("Mandatory Tags for EBS Volumes (according to AWS Config rule) are currently: ",returned_tag_names)
    return returned_tag_names

def tag_ebs_volume(volume_resource_id, ec2_resource_id, tags_to_apply):
    #this is the function to take an ebs volume, query the ec2 instance it is attached to and apply any tags that are missing
    #we don't want to overwrite any tags that already might be on the volume if it was attached from a restore or another instance (e.g. Application Tag)
    #so we check for any missing tags and copy them over only 
    
    #print("Trying to tag ",volume_resource_id, " with any missing tag values from mandatory tags: ", tags_to_apply)
    #1. Get tags on the ebs volume
    ec2=boto3.resource('ec2')
    volume = ec2.Volume(volume_resource_id)
    ebs_tags = volume.tags
    
    instance = ec2.Instance(ec2_resource_id)
    instance_tags = instance.tags
    
    #print("EBS tag values:", ebs_tags)
    #print("Attached EC2 tag values:", instance_tags)
    
    for tag in tags_to_apply:
        print("")
        #print("Checking EBS tag value for: ",tag)
        try:
            matching_ebs_tag = [d for d in ebs_tags if d['Key'] == tag]
        except Exception as e:
            print ("Error getting tags for EBS volume, there may be no tags at all")
            ebs_tags=[]
            matching_ebs_tag=[]
        if (len(matching_ebs_tag))>0:
            continue
            #print("There is already an EBS tag value for ",tag, "(value found is: ",matching_ebs_tag[0]['Value'],") so we will leave it alone.")
        if (len(matching_ebs_tag)==0):
            print("No EBS tag value found for ",tag)
            try:
                matching_ec2_tag = [d for d in instance_tags if d['Key'] == tag]
            except Exception as e:
                print("Error getting tags for EC2 instance, there may be no tags at all..")
                matching_ec2_tag=[]
            if (len(matching_ec2_tag))>0:
                print("Found an EC2 tag value for ",tag," on the attached EC2 instance (",matching_ec2_tag[0]['Value'],") so copying that to EBS volume...")
                ec2_client = boto3.client('ec2')
                new_tags=ebs_tags+matching_ec2_tag
                try:
                    ec2_client.create_tags(Resources=[volume_resource_id], Tags=new_tags)
                except Exception as e:
                    print ("There was an error applying the tags: ",e)
            if (len(matching_ec2_tag)==0):
                print("Could not find an EC2 tag value for", tag,"  - leaving the EBS tag blank. If the EC2 is tagged we will fix EBS on the next run..")
            
        #print(current_value)
        #print ("Current EBS value: ", current_value)
    print("")
    #4. For any missing tags on the EBS volume, tag from the corresponding EC2 tag value
    return


def lambda_handler(event, context):
    try:
        config_rule_name = os.environ['TAG_COMPLIANCE_RULE_NAME']
    except Exception as e:
        print("ERROR: Unable to determine the name of the config rule for tag compliance.. check Lambda Environment Variables")
        sys.exit(1)
    #boto3.set_stream_logger('')
    print('Starting EBS Volume Tagger....')
    print('==================================')
    ec2=boto3.resource('ec2')
    #customise retry count for aws config client as we keep hitting throttling retry limit with default of 4..
    boto3_config=botocore.config.Config(retries={'max_attempts':10})
    client = boto3.client('config', config=boto3_config)
    paginator = client.get_paginator('get_compliance_details_by_config_rule')
    page_iterator = paginator.paginate(
        ConfigRuleName=config_rule_name,
        ComplianceTypes=['NON_COMPLIANT']
        )
    #get the tag names that the rule checks for
    required_tags=get_required_tags([config_rule_name])
    all_results=[]
    for page in page_iterator:
        results=page['EvaluationResults']
        all_results += results
    #filter all_results for ones that relate to EBS volumes
    ebs_volumes= [x for x in all_results if x['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceType'] == 'AWS::EC2::Volume']
    print('Checking AWS Config Compliance results.....')
    print('================================================')
    print("Found ",len(ebs_volumes)," EBS volumes which are missing one or more of these tags. Attempting to fix any non-compliant..")
    for ebs_volume in ebs_volumes:
        #describe the tags from the ec2 instance and apply them to the volume
        #find if the volume is attached to an instance
        #if it is call the tagging function to check propagate tags down to the volume from the instance
        #but only for missing tags 
        vol_id=(ebs_volume['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'])
        volume = ec2.Volume(vol_id)
        volume_details=volume.attachments
        if len(volume_details) == 0:
            print(vol_id," is not attached to an instance, skipping")
        if len(volume_details) > 0:
            #Volume has attachment details, will try to detect instance tags and apply
            instance_id=volume_details[0]['InstanceId']
            print("Non-compliant volume ",vol_id," is attached to instance ",instance_id,". Trying to add missing tags from the instance..'")
            print('==================================')
            tag_ebs_volume(vol_id, instance_id, required_tags)
            
    return {
        'statusCode': 200,
        'body': json.dumps('EBS Tag Check Completed succesfully..')
    }

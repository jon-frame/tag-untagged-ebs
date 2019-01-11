

## Description
The Lambda uses boto3 to tag non-compliant EBS volumes by propagating missing tags down to the attached EBS volumes.
Unlike other tagging functions for EBS this function only propagates down tags which are defined as mandatory in your configuration of the managed AWS Config rule for required tagging, and will not overwrite any existing tags.  

We only propagate tags stipulated as required within the AWS Config rule so that we don't copy over irrelevant tags.

The function does the following:

1. Get all non-compliance EBS Volumes based on an environment variable containing the name for the config rule used for tag compliance
2. Query the AWS Config rule and get the scope of the rule (what are the actual tags which we need to obtain compliance?
3. Iterate through all non-compliant EBS Volumes
4. If you find a non-compliant EBS volume, check for an attached EC2 instance
5. If there’s an attached instance, check the tags on the instance
6. For any missing tags (but not for any tags that are already present), copy the tag from the EC2 instance.


## Deployment
The function requires a Python 3.6 runtime environment, with an mandatory Environment variable:

TAG_COMPLIANCE_RULE_NAME:  required-tags (this is used for the function to check for non-compliant results and determine which tags to copy down)

Timeout: 5 minutes

Sample IAM Policy for this function (to use in combination with the AWS Managed Policy AWSLambdaBasicExecutionRole):
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ReadOnlyToConfigAndEC2",
            "Effect": "Allow",
            "Action": [
                "config:GetComplianceDetailsByConfigRule",
                "ec2:DescribeInstances",
                "ec2:DescribeVolumes",
                "config:DescribeConfigRules",
                "ec2:DescribeVolumeAttribute"
           ],
            "Resource": "*"
        },
        {
            "Sid": "CreateTagsOnVolumes",
            "Effect": "Allow",
            "Action": "ec2:CreateTags",
            "Resource": "arn:aws:ec2:*:*:volume/*"
        }
    ]
}
```

## Trigger
It is suggested that the function is run on a schedule via a scheduled CloudWatch Event.

## Sample Log
A sample log for a run of the function is below:

START RequestId: 99ad4a57-13c0-11e9-80b3-27c5633ce5a7 Version: $LATEST
Starting EBS Volume Tagger....
--------------------------------
The Mandatory Tags that should be present on EBS Volumes (according to AWS Config rule) are currently: {'CostCentre', 'Anothertag', 'Application'}
Checking AWS Config Compliance results.....
--------------------------------==============
Found 3 EBS volumes which are missing one or more of these tags. Attempting to fix..
Non-compliant volume vol-0504aa8548a4b92d3 is attached to instance i-092afc416297cc215 . Trying to add missing tags from the instance..'
--------------------------------
Trying to tag vol-0504aa8548a4b92d3 with any missing tag values from mandatory tags: {'CostCentre', 'Anothertag', 'Application'}
EBS tag values: [{'Key': 'Application', 'Value': 'App1'}, {'Key': 'device', 'Value': '/dev/xvda'}, {'Key': 'instance_id', 'Value': 'i-092afc416297cc215'}]
Attached EC2 tag values: [{'Key': 'Application', 'Value': 'App1'}, {'Key': 'CostCentre', 'Value': 'Wholesale'}]

Checking EBS tag value for: CostCentre
No EBS tag value found for CostCentre
Found an EC2 tag value for CostCentre on the attached EC2 instance ( Wholesale ) so copying that to EBS volume...

Checking EBS tag value for: Anothertag
No EBS tag value found for Anothertag
Could not find an EC2 tag value for Anothertag - leaving the EBS tag blank. If the EC2 is tagged we will fix EBS on the next run..

Checking EBS tag value for: Application
There is an EBS tag value for Application (value found is: App1 )

Non-compliant volume vol-05d55eea091c6f32e is attached to instance i-0e1deaaaf162da286 . Trying to add missing tags from the instance..'
--------------------------------
Trying to tag vol-05d55eea091c6f32e with any missing tag values from mandatory tags: {'CostCentre', 'Anothertag', 'Application'}
EBS tag values: [{'Key': 'device', 'Value': '/dev/sda1'}, {'Key': 'instance_id', 'Value': 'i-0e1deaaaf162da286'}, {'Key': 'Name', 'Value': 'winbastion'}]
Attached EC2 tag values: [{'Key': 'Name', 'Value': 'winbastion'}]

Checking EBS tag value for: CostCentre
No EBS tag value found for CostCentre
Could not find an EC2 tag value for CostCentre - leaving the EBS tag blank. If the EC2 is tagged we will fix EBS on the next run..

Checking EBS tag value for: Anothertag
No EBS tag value found for Anothertag
Could not find an EC2 tag value for Anothertag - leaving the EBS tag blank. If the EC2 is tagged we will fix EBS on the next run..

Checking EBS tag value for: Application
No EBS tag value found for Application
Could not find an EC2 tag value for Application - leaving the EBS tag blank. If the EC2 is tagged we will fix EBS on the next run..

vol-0df0f36770fad1934 is not attached to an instance, skipping
END RequestId: 99ad4a57-13c0-11e9-80b3-27c5633ce5a7
REPORT RequestId: 99ad4a57-13c0-11e9-80b3-27c5633ce5a7	Duration: 5438.31 ms	Billed Duration: 5500 ms Memory Size: 128 MB	Max Memory Used: 45 MB	

 
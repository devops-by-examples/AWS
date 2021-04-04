import botocore
import boto3

s3_client = boto3.client('s3')

def getBucketList():
    return s3_client.list_buckets()
    
def lambda_handler(event, context):
    bucketNames = []
    unencrpted = []
    response = getBucketList()
    buckets = response['Buckets']
    for bucket in buckets:
        bucketNames.append(bucket['Name'])
    for bucket in bucketNames:
        try:
            s3_client.get_bucket_encryption(Bucket=bucket)
        except botocore.exceptions.ClientError as err:
            unencrpted.append(bucket)
    print("Unencrypted s3 buckets are " + str(unencrpted))

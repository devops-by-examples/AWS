import boto3
import csv 
# call s3 bucket
s3 = boto3.resource('s3')
bucket = s3.Bucket("test-abhi-01") # Enter your bucket name, e.g 'Data'
# key path, e.g.'customer_profile/Reddit_Historical_Data.csv'
key = 'test/testcsv.csv'
# lambda function
def lambda_handler(event,context):
    # download s3 csv file to lambda tmp folder
    local_file_name = '/tmp/test.csv' #
    s3.Bucket("test-abhi-01").download_file(key,local_file_name)
    
    # list you want to append
    lists = ['5/20/2020',123,321,31,'A'] 
    # write the data into '/tmp' folder
    with open('/tmp/test.csv','r') as infile:
        reader = list(csv.reader(infile))
        reader = reader[::-1] # the date is ascending order in file
        reader.insert(0,lists)
    
    with open('/tmp/test.csv', 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        for line in reversed(reader): # reverse order
            writer.writerow(line)
    
    # upload file from tmp to s3 key
    bucket.upload_file('/tmp/test.csv', key)
    

import boto3
import logging

# Enable debug logging to see detailed request/response information
logging.basicConfig(level=logging.DEBUG)

# Initialize the S3 client
s3 = boto3.client(
    's3',
    endpoint_url="https://fra1.digitaloceanspaces.com",  # DigitalOcean Spaces endpoint
    region_name="fra1",  # Match the region of your Space
    aws_access_key_id='DO801XNLGTYEWHUBBEAP',  # Your DigitalOcean Spaces access key
    aws_secret_access_key='B5d9q33jcImk00jtkF3zJCAKCCEgfKEzJeyuya+uaqI',  # Your DigitalOcean Spaces secret key
    config=boto3.session.Config(signature_version='s3v4')  # Use AWS Signature Version 4
)

# Specify the bucket and object key you want to interact with
bucket_name = 'dishpal-data'  # Replace with your bucket name
object_key = 'example-object.txt'  # Replace with a valid object key in your bucket

try:
    # Example: Upload a new object to the bucket
    new_object_key = 'new-example-object.txt'
    s3.put_object(Bucket=bucket_name, Key=new_object_key, Body='Hello, DigitalOcean Spaces!')
    print(f"Uploaded object '{new_object_key}' to bucket '{bucket_name}'.")

    # Example: Delete an object from the bucket
    s3.delete_object(Bucket=bucket_name, Key=object_key)
    print(f"Deleted object '{object_key}' from bucket '{bucket_name}'.")

except Exception as e:
    print(f"Error: {e}")
import os
import boto3
from botocore.client import Config

REDIRECT_ASSET_BUCKET=os.environ['REDIRECT_ASSET_BUCKET']

def lambda_handler(event, context):
    print(event)
    short_url = "u/" + event.get("Key")

    s3 = boto3.client('s3')
    resp = s3.head_object(Bucket=REDIRECT_ASSET_BUCKET, Key=short_url)

    print(resp)
    redirect_url = resp.get('WebsiteRedirectLocation')
    if redirect_url:
        print("Redirect: " + redirect_url)
        return { "Redirect": redirect_url }
    else:
        return { "Error": "Unable to load redirect url for object: s3://" + REDIRECT_ASSET_BUCKET + "/" + short_url }
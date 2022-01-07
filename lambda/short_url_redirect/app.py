import os
import boto3
import json

SHORT_URL_BUCKET=os.environ['SHORT_URL_BUCKET']

def lambda_handler(event, context):
    pathParameters = event['pathParameters']
    short_url = "u/" + pathParameters.get("key")

    s3 = boto3.client('s3')
    resp = s3.head_object(Bucket=SHORT_URL_BUCKET, Key=short_url)

    redirect_url = resp.get('WebsiteRedirectLocation')
    if redirect_url:
        return {
            "redirect" : redirect_url
        }
    else:
        return { "Error": "Unable to load redirect url for object: s3://" + SHORT_URL_BUCKET + "/" + short_url }
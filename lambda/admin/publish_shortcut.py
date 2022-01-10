from datetime import datetime
import json
from os import environ
import boto3

stage = environ['STAGE']
version_table = environ['VERSION_TABLE']
param_base = f"/{stage}/mindtether/version/shortcut"

def handler(event,context):
    if(event and event['body']):
        body = event['body']
        if not type(body) == dict:
            body = json.loads(body)
        if body.keys() >= {"version","description","shortcut_link"}:
            version = body['version']
            description = body['version']
            shortcut_link = body['shortcut_link']
            release_date = datetime.now()
            dynamo_item = {
                    'app':{'S':'shortcuts'},
                    'version': { 'S' : version },
                    "description": { "S" : description},
                    "shortcutLink": {"S": shortcut_link},
                    "releaseDate": { "S": release_date}
                }
            if "makeMinVersion" in body and body["makeMinVersion"] == True:
                min_param = f"{param_base}/min"
                ssm = boto3.client("ssm")
                min_response = ssm.put_parameter(
                    Name=min_param,
                    Value=version,
                    Overwrite=True
                )
                # If it has to be the min, it should also be the latest, regardless of input
                body['makeLatestVersion'] = True
            if "makeLatestVersion" in body and body['makeLatestVersion'] == True:
                latest_param = f"{param_base}/latest"
                ssm = boto3.client("ssm")
                latest_response = ssm.put_parameter(
                    Name=latest_param,
                    Value=version,
                    Overwrite=True
                )
            
            dynamodb = boto3.client("dynamodb")
            dynamo_response = dynamodb.put_item(
                TableName=version_table,
                Item=dynamo_item
            )
            if not dynamo_response['Attributes']:
                raise Exception("ERROR Releasing Shortcut")
            else:
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "updateStatus": "updated"
                    })
                }
    else:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Something went wrong"
            })
        }
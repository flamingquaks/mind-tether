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
            if("https://www.icloud.com/shortcuts/" in body['shortcut_link']):
                shortcut_id = body['shortcut_link'][body['shortcut_link'].rindex("/")+1:]
            else:
                shortcut_id = body['shortcut_link']
            version = body['version']
            description = body['description']
            release_date = datetime.now()
            release_date_string = release_date.strftime("%m/%d/%Y, %H:%M:%S")
            dynamo_item = {
                    'app':{'S':'shortcuts'},
                    'version': { 'S' : version },
                    "description": { "S" : description},
                    "shortcutId": {"S": shortcut_id},
                    "releaseDate": { "S": release_date_string}
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
            

            if "ResponseMetadata" not in dynamo_response or ("ResponseMetadata" in dynamo_response and dynamo_response['ResponseMetadata']['HTTPStatusCode'] != 200):
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
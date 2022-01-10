from datetime import datetime
import json
from os import environ
import boto3

stage = environ['STAGE']
version_table = environ['VERSION_TABLE']

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
            if body['makeMinVersion'] and body['makeMinVersion'] == True:
                dynamo_item['isMinVersion'] = True
            if body['makeLatestVersion'] and body['makeLatestVersion'] == True:
                dynamo_item['makeLatestVersion'] = True
            
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
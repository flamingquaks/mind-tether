from os import environ
import boto3
from boto3.dynamodb.conditions import Key
import json

stage = environ['STAGE']
version_table = environ['VERSION_TABLE']

def handler(event,context):
    if event and event['pathParameters'] and event['pathParameters']['app']:
        app = event['pathParameters']['app']
        dynamodb = boto3.resource("dynamodb")
        app_table = dynamodb.Table(version_table)
        query_response = app_table.query(
            KeyConditionExpression=Key("app").eq(app)
        )
        version_output = []
        for version in query_response['Items']:
            version_output.append({
                "version": version['version'],
                "description": version['description'],
                "releaseDate": version['releaseDate']
            })
        if len(version_output) > 0:
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "versions": version_output   
                })
            }
        else:
            return {
                "statusCode": 500,
                "body": json.dump({
                    "message": "There was an unknown error"
                })
            }
    else:
        return {
                "statusCode": 500,
                "body": json.dump({
                    "message": "There was an unknown error"
                })
        }
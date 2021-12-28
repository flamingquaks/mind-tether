import boto3
import os

request_table_name = os.environ['REQUEST_TABLE_NAME']


def lambda_handler(event,context):
    if request_id := event['queryStringParameters']['requestId']:
        dynamo_client = boto3.client("dynamodb")
        dynamo_response = dynamo_client.get_item(
            TableName=request_table_name,
            Key={
                "requestId":{"S": request_id}
            }
        )
        if dynamo_response and dynamo_response['Item'] and dynamo_response['Item']['status']:
            if dynamo_response['Item']['status'] == "CREATED":
                return {
                "statusCode":200,
                "status":dynamo_response['Item']['status'],
                "url": dynamo_response['Item']['image_url']
            }
            else:
                return {
                    "statusCode":200,
                    "status":dynamo_response['Item']['status']
                }
        else:
            return {
                "statusCode":500
            }
            

import boto3
import os
import json

request_table_name = os.environ['REQUEST_TABLE_NAME']


def lambda_handler(event,context):
    if request_id := event['pathParameters']['requestId']:
        dynamo_client = boto3.client("dynamodb")
        dynamo_response = dynamo_client.get_item(
            TableName=request_table_name,
            Key={
                "requestId":{"S": request_id}
            }
        )
        print(dynamo_response)
        if dynamo_response and dynamo_response['Item'] and dynamo_response['Item']['create_status']['S']:
            if dynamo_response['Item']['create_status']['S'] == "COMPLETE":
                return {
                "statusCode":200,
                "body":json.dumps({
                    "status":dynamo_response['Item']['create_status']['S'],
                    "url": dynamo_response['Item']['image_url']['S']
                })
               
            }
            else:
                return {
                    "statusCode":200,
                    "body":json.dumps({
                        "status": dynamo_response['Item']['create_status']['S']
                    })

                }
        else:
            return {
                "statusCode":500
            }
            

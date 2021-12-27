import boto3
import os
from uuid import uuid4
from datetime import datetime
from datetime import timedelta


state_machine_arn = os.environ['STATE_MACHINCE_ARN']
request_table_name = os.environ['REQUEST_TABLE_NAME']


def lambda_handler(event,context):
    if event['queryStringParameters'] and event['queryStringParameters']['day'] and \
        event['queryStringParameters']['width'] and event['queryStringParameters']['height']:
            day = event['queryStringParameters']['day']
            width = event['queryStringParameters']['width']
            height = event['queryStringParameters']['height']
            step_function_input = {
                "day":day,
                "width": width,
                "height": height
            }
            request_id = uuid4()
            stepfunctions_client = boto3.client("stepfunctions")
            step_function_response = stepfunctions_client.start_execution(
                stateMachineArn=state_machine_arn,
                input=step_function_input
            )
            if step_function_response['ExecutionArn']:
                request_time = datetime.now()
                ttl_val = request_time + timedelta(minutes=15)
                dynamodb_client = boto3.client("dynamodb")
                dynamodb_client.put_item(
                    TableName=request_table_name,
                    Item={
                        "requestId":request_id,
                        "stepFunctionExecutionArn" : step_function_response['executionArn'],
                        "status":"started",
                        "ttl": ttl_val
                    }
                )
                return {
                    "requestId":request_id,
                    "statusCode":200,
                    "height":height,
                    "width":width,
                    "day":day
                }
    else:
        return {
            "statusCode": 400   
        }
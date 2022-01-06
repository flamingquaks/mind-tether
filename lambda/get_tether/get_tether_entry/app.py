import boto3
import os
from uuid import uuid4
from datetime import datetime
import json
from datetime import timedelta
import MindTetherCore


state_machine_arn = os.environ['STATE_MACHINCE_ARN']
request_table_name = os.environ['REQUEST_TABLE_NAME']


def lambda_handler(event,context):
    if event['queryStringParameters'] and event['queryStringParameters']['day'] and \
        event['queryStringParameters']['width'] and event['queryStringParameters']['height']:
            day = event['queryStringParameters']['day']
            width = event['queryStringParameters']['width']
            height = event['queryStringParameters']['height']
            request_id=str(uuid4())
            step_function_input = {
                "day":day,
                "width": width,
                "height": height,
                "background_base_key": MindTetherCore.AssetMapper.get_background_image_key(day,width,height),
                "requestId":request_id
            }
            event['requestId'] = request_id
            stepfunctions_client = boto3.client("stepfunctions")
            step_function_response = stepfunctions_client.start_execution(
                stateMachineArn=state_machine_arn,
                input=json.dumps(step_function_input)
            )
            if step_function_response['executionArn']:
                request_time = datetime.now()
                ttl_val = request_time + timedelta(minutes=15)
                dynamodb_client = boto3.client("dynamodb")
                dynamodb_client.put_item(
                    TableName=request_table_name,
                    Item={
                        'requestId':{'S':request_id},
                        'stepFunctionExecutionArn' : {'S':str(step_function_response['executionArn'])},
                        'create_status':{'S':'IN_PROGRESS'},
                        'ttl': {'S': str(ttl_val)}
                    }
                )
                return {
                    "statusCode":200,
                    "body": json.dumps({
                        "requestId":request_id,
                        "height":height,
                        "width":width,
                        "day":day
                    })
                }
    else:
        return {
            "statusCode": 400   
        }
import boto3
import os

request_table_name = os.environ['REQUEST_TABLE_NAME']


def lambda_handler(event,context):
    if request_id := event['queryStringParams']['requestId']:
        dynamo_client = boto3.client("dynamodb")
        dynamo_response = dynamo_client.get_item(
            TableName=request_table_name,
            Key={
                "requestId":request_id
            }
        )
        if dynamo_response:
            execution_arn = dynamo_response['item']['stepFunctionExecutionArn']
            if execution_arn:
                sfn_client = boto3.client("sfn")
                sfn_response = sfn_client.describe_execution(
                    executionArn=execution_arn
                )
                if sfn_response and sfn_response['status']:
                    execution_status = sfn_response['status']
                    if execution_status == "RUNNING":
                        return {
                            "statusCode":200,
                            "GetTetherState": "GeneratingTether"
                        }
                    elif execution_status == "SUCCEEDED":
                        return {
                            "statusCode":200,
                            "GetTetherState": "TetherGenerated"
                        }
        
        return {
            "statusCode": 403
        }
            
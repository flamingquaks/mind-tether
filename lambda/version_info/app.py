import boto3
from os import environ
import json

stage = environ['STAGE']


def lambda_handler(event,context):
    if event and event['pathParameters'] and event['pathParameters']['app']:
        app = event['pathParameters']['app']
        param_base = f"/{stage}/MindTether/version/{app}"
        ssm = boto3.client("ssm")
        param_response = ssm.get_parameters_by_path(Path=param_base,Recursive=True)
        params = param_response['Parameters']
        return {
            "statusCode": 200,
            "body": json.dumps(params)
        }
    else:
        return {
            "statusCode": 500
        }
        
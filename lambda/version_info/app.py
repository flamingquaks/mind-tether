import boto3
from os import environ
import json

stage = environ['STAGE']


def lambda_handler(event,context):
    if event and event['pathParameters'] and event['pathParameters']['app']:
        app = event['pathParameters']['app']
        param_base = f"/{stage}/mindtether/version/{app}"
        ssm = boto3.client("ssm")
        param_response = ssm.get_parameters_by_path(Path=param_base,Recursive=True)
        params = param_response['Parameters']
        version_data = {}
        i = 0
        while i < len(params):
            param = params[i]
            attribute_name = param['Name'][param['Name'].rindex("/")+1:]
            version_data[attribute_name] = param['Value']
            i += 1
        return {
            "statusCode": 200,
            "body": json.dumps(version_data)
        }
    else:
        return {
            "statusCode": 500
        }
        
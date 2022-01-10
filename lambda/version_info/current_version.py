import boto3
from os import environ
import json

stage = environ['STAGE']


def is_newer_version_available (user_version:str, remote_version:str):
    user_version_parts = user_version.split(".")
    remote_version_parts = remote_version.split(".")
    for x in range(3):
        if remote_version_parts[x] > user_version_parts[x]:
            return True
    return False


def lambda_handler(event,context):
    if event and "pathParameters" in event and "app" in event['pathParameters']:
        app = event['pathParameters']['app']
        param_base = f"/{stage}/mindtether/version/{app}"
        if "version" in event['pathParameters']:
            user_version = event['pathParameters']['version']
            update_check = True
        else:
            update_check = False
        ssm = boto3.client("ssm")
        param_response = ssm.get_parameters_by_path(Path=param_base,Recursive=True)
        params = param_response['Parameters']
        version_data = {}
        i = 0
        version_attributes = {"min":{"update_key": "requiredUpdate"},"latest":{"update_key": "optionalOptional"}}
        while i < len(params):
            param = params[i]
            attribute_name = param['Name'][param['Name'].rindex("/")+1:]
            version_data[attribute_name] = param['Value']
            
            if attribute_name and update_check:
                if update_available := is_newer_version_available(user_version,param['Value']):
                    version_data[version_attributes[attribute_name]['update_key']] = update_available
            i += 1
        return {
            "statusCode": 200,
            "body": json.dumps(version_data)
        }
    else:
        return {
            "statusCode": 500
        }
        
from typing_extensions import runtime
import json
from aws_cdk import (
    Duration,
    BundlingOptions,
    Stack,
    Stage,
    # aws_sqs as sqs,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_apigateway as apigw,
    aws_appintegrations as api_integrations,
    aws_lambda as _lambda,
    # aws_efs as efs
    
)

from constructs import Construct

class PhoneBackgroundHelperStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ## Create the S3 Asset Bucket
        asset_bucket = s3.Bucket(self,"AssetBucket")
        asset_bucket.lifecycleRules = [s3.LifecycleRule(
            enabled=True,
            expiration=Duration.minutes(1)
        )]
        ## Create and configure API Gateway
        api = apigw.RestApi(self, "PhoneBackgroundHelperAPI")
        deployment_environment = self._get_environment()
        ## Setting stage from the deployment
        stage_name = deployment_environment['stage']
        api_deployment = apigw.Deployment(self,"deployment",api=api)
        api.deployment_stage = apigw.Stage(self,stage_name, deployment=api_deployment,stage_name=stage_name)
        
        #Create the Lambda Layers
        asset_layer = _lambda.LayerVersion(
            self, 'asset-layer', code=_lambda.Code.from_asset("lambda_layers/mindtether_assets"),
            layer_version_name="asset-layer"
        )
        
        mindtether_core = _lambda.LayerVersion(
            self, "mindtether_core", code=_lambda.Code.from_asset("lambda_layers/mindtether_core"),
            layer_version_name="mindtether_core-layer"
        )
        ## Begin creating the generate_helper_image lambda
        generate_helper_image_lambda = _lambda.Function(self,
                                                        "GenerateHelperImage",
                                                        runtime=_lambda.Runtime.PYTHON_3_8,
                                                        code=_lambda.Code.from_asset(path="lambda/generate_helper_image", bundling=BundlingOptions(
                                                            command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"],
                                                            image=_lambda.Runtime.PYTHON_3_8.bundling_image)),
                                                        handler='lambda_handler',
                                                        timeout=Duration.seconds(60)
                                                        )
        
        generate_helper_image_lambda.add_layers(asset_layer)
        generate_helper_image_lambda.add_layers(mindtether_core)
        
        generate_helper_image_lambda.add_environment("S3_BUCKET", asset_bucket.bucket_name)
        generate_helper_image_lambda.add_environment("SHORTENER_URL","https://link.mindtether.rudy.fyi/admin_shrink_url")
        generate_helper_image_lambda.add_environment("CDN_PREFIX","link.mindtether.rudy.fyi")
        
        asset_bucket.grant_read(generate_helper_image_lambda)
        asset_bucket.grant_write(generate_helper_image_lambda)
        
        generate_helper_image_api_integration = apigw.LambdaIntegration(generate_helper_image_lambda)
        generate_helper_image_api_resource = api.root.add_resource("generate-helper-image")
        
        generate_helper_image_api_resource.add_method("GET",generate_helper_image_api_integration)
        
        ## Begin creating get_phone_data lambda
        get_phone_data_lambda = _lambda.Function(self,
                                                 "GetPhoneData",
                                                 runtime=_lambda.Runtime.PYTHON_3_8,
                                                 code=_lambda.Code.from_asset(path="lambda/get_phone_data", bundling=BundlingOptions(
                                                     command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"],
                                                            image=_lambda.Runtime.PYTHON_3_8.bundling_image)),
                                                 handler='lambda_handler',
                                                 timeout=Duration.seconds(15)
                                                 )
        # get_phone_data_api_integration = apigw.LambdaIntegration("GET",get_phone_data_lambda)
        # get_phone_data_api_resource = api.root.add_resource("get-phone-data")
        # get_phone_data_api_resource.add_method("GET", get_phone_data_api_integration)
        
        
        # Version based on context
        if deployment_environment['stage'] == "prod":
            generate_helper_image_lambda_version = _lambda.Version(self,'GenerateHelperImageV1', function=generate_helper_image_lambda)
            generate_helper_image_lambda_alias = _lambda.Alias(self,"alias", alias_name="prod", version=generate_helper_image_lambda_version)
            
            get_phone_data_lambda_version = _lambda.Version(self,"GetPhoneDataV1", function=get_phone_data_lambda)
            get_phone_data_lambda_alias = _lambda.Alias(self,"alias", alias_name="prod", version=get_phone_data_lambda_version)
        else:
            generate_helper_image_lambda_alias = _lambda.Alias(self,"GenerateHelperImageAlias", alias_name="dev",version=generate_helper_image_lambda.latest_version)
            get_phone_data_lambda_alias = _lambda.Alias(self,"GetPhoneDataAlias", alias_name="dev",version=get_phone_data_lambda.latest_version)
            
        
    
        
        
    def _get_environment(self):
        print("Determining deployment environment")
        if self.node.try_get_context("deployment"):
            deployment_env = dict(self.node.try_get_context(self.node.try_get_context("deployment")))
            print("Received deployment context from input.")
            print("Setting deployment stage to %s"%(deployment_env['stage']))
        else:
            print("No deployment context received from input. Defaulting...")
            deployment_env = dict(self.node.try_get_context("dev"))
            print("Setting deployment stage to %s"%(deployment_env['stage']))
        return deployment_env;

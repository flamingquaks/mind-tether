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

        asset_bucket = s3.Bucket(self,"AssetBucket")
        # s3_deployment.BucketDeployment(self,"DeployAssets", 
        #                                sources=[s3_deployment.Source.asset("assets")],
        #                                destination_bucket=asset_bucket)
        asset_bucket.lifecycleRules = [s3.LifecycleRule(
            enabled=True,
            expiration=Duration.minutes(1)
        )]
        api = apigw.RestApi(self, "PhoneBackgroundHelperAPI")
        deployment_environment = self._get_environment()
        stage_name = deployment_environment['stage']
        api_deployment = apigw.Deployment(self,"deployment",api=api)
        api.deployment_stage = apigw.Stage(self,stage_name, deployment=api_deployment,stage_name=stage_name)

        generate_helper_image_lambda = _lambda.Function(self,
                                                        "GenerateHelperImage",
                                                        runtime=_lambda.Runtime.PYTHON_3_8,
                                                        code=_lambda.Code.from_asset(path="lambda", bundling=BundlingOptions(
                                                            command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"],
                                                            image=_lambda.Runtime.PYTHON_3_8.bundling_image)),
                                                        handler='generate_helper_image.lambda_handler',
                                                        timeout=Duration.seconds(60)
                                                        )
        
        generate_helper_image_lambda.add_layers(_lambda.LayerVersion(
            self, 'asset-layer-images', code=_lambda.Code.from_asset("assets/images"),
            layer_version_name="asset-layer-images"
        ))
        
        generate_helper_image_lambda.add_layers(_lambda.LayerVersion(
            self, "asset-layer-text", code=_lambda.Code.from_asset("assets/text"),
            layer_version_name="asset-layer-text"
        ))
        
        generate_helper_image_lambda.add_environment("S3_BUCKET", asset_bucket.bucket_name)
        generate_helper_image_lambda.add_environment("SHORTENER_URL","https://link.mindtether.rudy.fyi/admin_shrink_url")
        generate_helper_image_lambda.add_environment("CDN_PREFIX","link.mindtether.rudy.fyi")
        
        if deployment_environment['stage'] == "prod":
            generate_helper_image_lambda_version = _lambda.Version(self,'GenerateHelperImageV1', function=generate_helper_image_lambda)
            generate_helper_image_lambda_alias = _lambda.Alias(self,"alias", alias_name="prod", version=generate_helper_image_lambda_version)
        else:
            generate_helper_image_lambda_alias = _lambda.Alias(self,"alias", alias_name="dev",version=generate_helper_image_lambda.latest_version)
            
        
    
        asset_bucket.grant_read(generate_helper_image_lambda)
        asset_bucket.grant_write(generate_helper_image_lambda)
        
        get_generate_helper_image_handler = apigw.LambdaIntegration(generate_helper_image_lambda)
        generate_helper_image_resource = api.root.add_resource("generate-helper-image")
        
        generate_helper_image_resource.add_method("GET",get_generate_helper_image_handler)
        
    def _get_environment(self):
        print("Determining deployment environment")
        if self.node.try_get_context("deployment"):
            deployment_env = dict(self.node.try_get_context(self.node.try_get_context("deployment")))
            print("Received deployment context from input.")
            print("Setting deployment stage to %s"%(deployment_env['stage']))
        else:
            print("No deployment context received from inpu. Defaulting...")
            deployment_env = dict(self.node.try_get_context("dev"))
            print("Setting deployment stage to %s"%(deployment_env['stage']))
        return deployment_env;

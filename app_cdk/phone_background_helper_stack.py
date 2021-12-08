from typing_extensions import runtime
from aws_cdk import (
    Duration,
    BundlingOptions,
    Stack,
    # aws_sqs as sqs,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_apigateway as apigw,
    aws_appintegrations as api_integrations,
    aws_lambda as _lambda,
    aws_lambda_python_alpha as _lambda_python
)

from constructs import Construct

class PhoneBackgroundHelperStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        asset_bucket = s3.Bucket(self,"AssetBucket")
        # s3_deployment.BucketDeployment(self,"DeployAssets", 
        #                                sources=[s3_deployment.Source.asset("assets")],
        #                                destination_bucket=asset_bucket)
        
        api = apigw.RestApi(self, "PhoneBackgroundHelperAPI")
        
        # lambda_bundling = BundlingOptions
        # lambda_bundling.command = "pip install -r requirements.txt"
        # lambda_bundling.image = _lambda.Runtime.bundling_image
        
        generate_helper_image_lambda = _lambda.Function(self,
                                                        "GenerateHelperImage",
                                                        runtime=_lambda.Runtime.PYTHON_3_8,
                                                        code=_lambda.Code.from_asset(path="lambda", bundling=BundlingOptions(
                                                            command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"],
                                                            image=_lambda.Runtime.PYTHON_3_8.bundling_image)),
                                                        handler='generate_helper_image.lambda_handler',
                                                        timeout=Duration.seconds(60)
                                                        )
        
        # generate_helper_image_lambda.add_layers(_lambda.LayerVersion(
        #     self, 'asset-layer', code=_lambda.Code.from_asset("assets")
        # ))
        
        generate_helper_image_lambda.add_environment("S3_BUCKET", asset_bucket.bucket_name)
                
        asset_bucket.grant_read(generate_helper_image_lambda)
        asset_bucket.grant_write(generate_helper_image_lambda)
        
        get_generate_helper_image_handler = apigw.LambdaIntegration(generate_helper_image_lambda)
        generate_helper_image_resource = api.root.add_resource("generate-helper-image")
        
        generate_helper_image_resource.add_method("GET",get_generate_helper_image_handler)
        


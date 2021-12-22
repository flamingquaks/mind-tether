from aws_cdk import (
    Duration,
    BundlingOptions,
    Stack,
    aws_s3 as s3,
    aws_apigateway as apigw,
    aws_lambda as _lambda,    
    aws_lambda_python_alpha as python_lambda
)

from constructs import Construct

class MindTetherApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,   **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
            
        api = apigw.RestApi(self,"MindTetherApi")
        
        if not self.node.try_get_context("short_url_host") or not self.node.try_get_context("api_host"):
            print("Missing values in cdk.json. Please check that short_url_host and api_host are provided.")
        else:
            short_url_host = self.node.try_get_context("short_url_host")
            api_host = self.node.try_get_context("api_host")

        ## Create the S3 Asset Bucket
        asset_bucket = s3.Bucket(self,"AssetBucket")
        asset_bucket.add_lifecycle_rule(abort_incomplete_multipart_upload_after=Duration.days(1),
                                        enabled=True,
                                        expiration=Duration.days(1))
        
        api_deployment = apigw.Deployment(self,"deployment",api=api)
        # api.deployment_stage = apigw.Stage(self,stage_name, deployment=api_deployment,stage_name=stage_name)
        
        #Create the Lambda Layers
        mindtether_assets = _lambda.LayerVersion(
            self, 'mindtether_assets', code=_lambda.Code.from_asset("lambda_layers/mindtether_assets_layer"),
            layer_version_name="mindtether_assets"
        )
        
        mindtether_core = _lambda.LayerVersion(
            self, "mindtether_core", code=_lambda.Code.from_asset("lambda_layers/mindtether_core"),
            layer_version_name="mindtether_core"
        )
        
        """ 
        V0 - GenerateHelperImage Lambda
        This was the very first iteration of the project.   
        #DEPRECATED!
        """
        
        generate_helper_image_lambda = python_lambda.PythonFunction(
            self,
            "GenerateHelperImage",
            entry="lambda/generate_helper_image",
            runtime=_lambda.Runtime.PYTHON_3_8,
            index="app.py",
            handler="lambda_handler",
            timeout=Duration.seconds(60)
        )
        
        ## Lambda:GenerateHelperImage - Add Lambda Layers
        generate_helper_image_lambda.add_layers(mindtether_assets)
        # generate_helper_image_lambda.add_layers(mindtether_core)
        
        ## Lambda:GenerateHelperImage - Add Environment Variables
        generate_helper_image_lambda.add_environment("S3_BUCKET", asset_bucket.bucket_name)
        generate_helper_image_lambda.add_environment("SHORTENER_URL","https://%s/admin_shrink_url"%(short_url_host))
        generate_helper_image_lambda.add_environment("CDN_PREFIX",short_url_host)
        
        ## Lambda:GenerateHelperImage - Grant access to asset_bucket (s3)
        asset_bucket.grant_read(generate_helper_image_lambda)
        asset_bucket.grant_write(generate_helper_image_lambda)
        
        # Lambda:GenerateHelperImage - Add Lambda to API
        generate_helper_image_api_integration = apigw.LambdaIntegration(generate_helper_image_lambda)
        generate_helper_image_api_resource = api.root.add_resource("generate-helper-image")
        
        generate_helper_image_api_resource.add_method("GET",generate_helper_image_api_integration)
        
        #### END of V0
        
        """V1 Lambdas
        """
        
        ## get_tether_lambdas
        get_background_image_info_lambda = python_lambda.PythonFunction(
            self,
            "GetBkgImgInfo",
            entry="lambda/get_tether/get_background_image_info",
            index="app.py",
            handler="lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_8,
            timeout=Duration.seconds(60)
        )
        get_background_image_info_lambda.add_environment("MIND_TETHER_API_ASSETS",asset_bucket.bucket_name)
        get_background_image_info_lambda.add_layers(mindtether_core,mindtether_assets)
        asset_bucket.grant_read_write(get_background_image_info_lambda)
        
            
        

        if(self.node.try_get_context("extended_mode") and self.node.try_get_context("extended_mode") == True):
            print("extended_mode == True")
            ## URLShortener
            ## URLShortner:S3 Bucket
            shortener_bucket = s3.Bucket(self,"URLShortnerBucket")
            shortener_bucket.add_lifecycle_rule(self,enabled=True,expiration=Duration.minutes(5))
            
            ## URLShortener:LambdaShortener
            url_shortener_lambda = _lambda.Function(self,
                                                    "ShortenURL",
                                                    runtime=_lambda.Runtime.PYTHON_3_8,
                                                    code=_lambda.Code.from_asset(path="lambda/shorten_url", bundling=BundlingOptions(
                                                        command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"],
                                                        image=_lambda.Runtime.PYTHON_3_8.bundling_image)),
                                                    handler="lambda_handler",
                                                    timeout=Duration.seconds(30)
                                                                
            )    

            shortener_bucket.grant_read_write(url_shortener_lambda)
        
        # Version based on context
        if self.node.try_get_context("deployment") == "prod":
            generate_helper_image_lambda_version = _lambda.Version(self,'GenerateHelperImageV1', function=generate_helper_image_lambda)
            generate_helper_image_lambda_alias = _lambda.Alias(self,"alias", alias_name="prod", version=generate_helper_image_lambda_version)
        else:
            generate_helper_image_lambda_alias = _lambda.Alias(self,"GenerateHelperImageAlias", alias_name="dev",version=generate_helper_image_lambda.latest_version)
            

            prodStage = apigw.Stage(self,"prod",deployment=api_deployment,stage_name="prod")
            devStage = apigw.Stage(self,"dev",deployment=api_deployment, stage_name="dev")
        
        if self.node.try_get_context("deployment") == "prod":
            api.deployment_stage = prodStage
        else:
            api.deployment_stage = devStage
        
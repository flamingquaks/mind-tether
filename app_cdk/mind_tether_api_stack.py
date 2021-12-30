from aws_cdk import (
    Duration,
    BundlingOptions,
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
    aws_apigateway as apigw,
    aws_lambda as _lambda,    
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as stepfunction_tasks,
    aws_dynamodb as dynamodb
    # aws_lambda_python_alpha as python_lambda
)


from constructs import Construct


class MindTetherApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, stage_name:str=None,  **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        if not stage_name:
            exit()
        
        ## Define the Rest Api Gateway
        api = apigw.RestApi(self,"MindTetherApi-%s"%(stage_name))
        
        if not self.node.try_get_context("short_url_host") or not self.node.try_get_context("api_host"):
            print("Missing values in cdk.json. Please check that short_url_host and api_host are provided.")
        else:
            short_url_host = self.node.try_get_context("short_url_host")
            api_host = self.node.try_get_context("api_host")

        ## Create the S3 Asset Bucket
        if stage_name == "dev":
            removal_policy = RemovalPolicy.DESTROY
        else:
            removal_policy = RemovalPolicy.RETAIN
        asset_bucket = s3.Bucket(self,"AssetBucket", removal_policy=removal_policy)
        asset_bucket.add_lifecycle_rule(abort_incomplete_multipart_upload_after=Duration.days(1),
                                        enabled=True)
                
        ###### Create Lambda Layers ######
        mindtether_assets_name="mindtether_assets"
        mindtether_assets = _lambda.LayerVersion(
            self, mindtether_assets_name, code=_lambda.Code.from_asset("lambda_layers/mindtether_assets_layer"),
            layer_version_name="mindtether_assets"
        )
        mindtether_assets_path="/opt/%s" % (mindtether_assets_name)
        
        mindtether_core = _lambda.LayerVersion(
            self, "mindtether_core", code=_lambda.Code.from_asset("lambda_layers/mindtether_core"),
            layer_version_name="mindtether_core"
        )
        
        """ 
        V0 - GenerateHelperImage Lambda
        This was the very first iteration of the project.   
        #DEPRECATED!
        """
        
        generate_helper_image_lambda = _lambda.Function(
            self,
            "GenerateHelperImage",
            code=_lambda.Code.from_asset("lambda/v0/generate_helper_image"),
            handler="app.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_8,
            timeout=Duration.seconds(60)
        )
        
        
        ## Lambda:GenerateHelperImage - Add Lambda Layers
        generate_helper_image_lambda.add_layers(mindtether_assets)
        generate_helper_image_lambda.add_layers(mindtether_core)
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
                
        get_tether_requests_table = dynamodb.Table(
            self,
            "GetTetherRequests",
            partition_key=dynamodb.Attribute(
                name="requestId",
                type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl"
        )
        
        get_background_image_info_lambda = _lambda.Function(
            self,
            "GetBkgImgInfo",
            code=_lambda.Code.from_asset("lambda/get_tether/get_background_image_info"),
            handler="app.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_8,
            timeout=Duration.seconds(60)
        )
        
        
        get_background_image_info_lambda.add_environment("MIND_TETHER_API_ASSETS",asset_bucket.bucket_name)
        get_background_image_info_lambda.add_environment("ASSET_LAYER_NAME", mindtether_assets_name)
        get_background_image_info_lambda.add_layers(mindtether_core,mindtether_assets)
        asset_bucket.grant_read_write(get_background_image_info_lambda)
        
            
        get_day_image_lambda = _lambda.Function(
            self,
            "GetDayImgInfo",
            code=_lambda.Code.from_asset("lambda/get_tether/get_day_image_info"),
            handler="app.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_8,
            timeout=Duration.seconds(60)
        )
        
        get_day_image_lambda.add_environment("MIND_TETHER_API_ASSETS",asset_bucket.bucket_name)
        get_day_image_lambda.add_environment("ASSET_LAYER_NAME", mindtether_assets_name)
        get_day_image_lambda.add_layers(mindtether_core,mindtether_assets)
        asset_bucket.grant_read_write(get_day_image_lambda)
        
        compile_image_lambda = _lambda.Function(
            self,
            "CompileImg",
            code=_lambda.Code.from_asset("lambda/get_tether/compile_image"),
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="app.lambda_handler",
            timeout=Duration.seconds(60)
        )
        
        compile_image_lambda.add_environment("MIND_TETHER_API_ASSETS",asset_bucket.bucket_name)
        compile_image_lambda.add_environment("ASSET_LAYER_NAME", mindtether_assets_name)
        compile_image_lambda.add_environment("REQUEST_TABLE_NAME", get_tether_requests_table.table_name)
        compile_image_lambda.add_layers(mindtether_core,mindtether_assets)
        asset_bucket.grant_read_write(compile_image_lambda)
        get_tether_requests_table.grant_read_write_data(compile_image_lambda)        

        
        
        get_background_image_info_task = stepfunction_tasks.LambdaInvoke(
            self,"GetBkgImgInfoTask", lambda_function=get_background_image_info_lambda
        )
        
        get_day_image_task = stepfunction_tasks.LambdaInvoke(
            self,"GetDayImgTask", lambda_function=get_day_image_lambda
        )
        
        compile_image_task = stepfunction_tasks.LambdaInvoke(
            self,"CompileImgTask", lambda_function=compile_image_lambda
        )
        
        get_tether_state_machine_definition = get_background_image_info_task\
            .next(get_day_image_task) \
            .next(compile_image_task)
        
        get_tether_state_machine = stepfunctions.StateMachine(self,"GetTetherStateMachine",
                                                              definition=get_tether_state_machine_definition,
                                                              timeout=Duration.minutes(5),
                                                              state_machine_type=stepfunctions.StateMachineType.STANDARD)
        

        get_tether_entry_lambda = _lambda.Function(self,
                                                   "get-tether-entry",
                                                   code=_lambda.Code.from_asset("lambda/get_tether/get_tether_entry"),
                                                   handler="app.lambda_handler",
                                                   runtime=_lambda.Runtime.PYTHON_3_8)
        
        # get_tether_entry_lambda.role.add_managed_policy(ManagedPolicy.from_aws_managed_policy_name("AWSLambdaBasicExecutionRole"))
        
        get_tether_requests_table.grant_read_write_data(get_tether_entry_lambda)
        get_tether_state_machine.grant_start_execution(get_tether_entry_lambda) 
        
        get_tether_entry_lambda.add_environment("REQUEST_TABLE_NAME", get_tether_requests_table.table_name)
        get_tether_entry_lambda.add_environment("STATE_MACHINCE_ARN", get_tether_state_machine.state_machine_arn)
            
        
        get_tether_entry_api_integration = apigw.LambdaIntegration(get_tether_entry_lambda)
        get_tether_entry_api_resource = api.root.add_resource("get-tether")
        
        get_tether_entry_api_resource.add_method("GET",get_tether_entry_api_integration)
        
        get_tether_status_lambda = _lambda.Function(self,
                                                    "get-tether-status",
                                                    code=_lambda.Code.from_asset("lambda/get_tether/get_tether_status"),
                                                    handler="app.lambda_handler",
                                                    runtime=_lambda.Runtime.PYTHON_3_8)
        
        get_tether_status_lambda.add_environment("REQUEST_TABLE_NAME", get_tether_requests_table.table_name)
        
        get_tether_requests_table.grant_read_data(get_tether_status_lambda)
        
        get_tether_status_api_integration = apigw.LambdaIntegration(get_tether_status_lambda)
        get_tether_status_api_resource = get_tether_entry_api_resource.add_resource("{requestId}")
        
        get_tether_status_api_resource.add_method("GET",get_tether_status_api_integration)
        
        

        if(self.node.try_get_context("extended_mode") and self.node.try_get_context("extended_mode") == True):
            print("extended_mode == True")
            ## URLShortener
            ## URLShortner:S3 Bucket
            shortener_bucket = s3.Bucket(self,"URLShortnerBucket")
            shortener_bucket.add_lifecycle_rule(self,enabled=True,expiration=Duration.minutes(5))
            
            # ## URLShortener:LambdaShortener
            # url_shortener_lambda = _lambda.Function(self,
            #                                         "ShortenURL",
            #                                         runtime=_lambda.Runtime.PYTHON_3_8,
            #                                         code=_lambda.Code.from_asset(path="lambda/shorten_url", bundling=BundlingOptions(
            #                                             command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"],
            #                                             image=_lambda.Runtime.PYTHON_3_8.bundling_image)),
            #                                         handler="lambda_handler",
            #                                         timeout=Duration.seconds(30)
                                                                
            # )    

            # shortener_bucket.grant_read_write(url_shortener_lambda)
        
        # Version based on context
        if self.node.try_get_context("deployment") == "prod":
            generate_helper_image_lambda_version = _lambda.Version(self,'GenerateHelperImageV1', function=generate_helper_image_lambda)
            generate_helper_image_lambda_alias = _lambda.Alias(self,"alias", alias_name="prod", version=generate_helper_image_lambda_version)
        else:
            generate_helper_image_lambda_alias = _lambda.Alias(self,"GenerateHelperImageAlias", alias_name="dev",version=generate_helper_image_lambda.latest_version)
            

        api_deployment = apigw.Deployment(self,"deployment",api=api)
        if stage_name != "prod":
            api_stage = apigw.Stage(self,stage_name,deployment=api_deployment, stage_name=stage_name)
        

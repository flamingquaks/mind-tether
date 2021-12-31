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
    aws_dynamodb as dynamodb,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cloudfront_origins,
    aws_certificatemanager as acm,
    aws_ssm as ssm
)


from constructs import Construct


class MindTetherApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, stage_name:str=None,  **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        if not stage_name:
            exit()
            
        
        
        ## Define the Rest Api Gateway
        api = apigw.RestApi(self,"MindTetherApi-%s"%(stage_name))
        
        # This will be phased out with the completion on get-tether and subsequent shortcut update.
        if not self.node.try_get_context("short_url_host") or not self.node.try_get_context("api_host"):
            print("Missing values in cdk.json. Please check that short_url_host and api_host are provided.")
            exit()
        else:
            short_url_host_old = self.node.try_get_context("short_url_host")
            api_host = self.node.try_get_context("api_host")
            
            
        ## Get context for the current stage:
        if stack_context := self.node.try_get_context(stage_name):
            api_host = stack_context['api_host']
            api_stage = stack_context['stage']
            short_url_host = stack_context['short_url_host']
            cert_arn_string = stack_context['cert_arn']
            
        if cert_arn_string:
            cert_arn = ssm.StringParameter.from_string_parameter_name(self,"certParam", string_parameter_name=cert_arn_string).string_value
        else:
            exit()

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
        generate_helper_image_lambda.add_environment("SHORTENER_URL","https://%s/admin_shrink_url"%(short_url_host_old))
        generate_helper_image_lambda.add_environment("CDN_PREFIX",short_url_host_old)
        
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
            self,"GetDayImgTask", lambda_function=get_day_image_lambda,
            input_path="$.Payload"
        )
        
        compile_image_task = stepfunction_tasks.LambdaInvoke(
            self,"CompileImgTask", lambda_function=compile_image_lambda,
            input_path="$.Payload"
        )
        
        get_tether_state_machine_definition = get_background_image_info_task\
            .next(get_day_image_task) \
            .next(compile_image_task)
        
        get_tether_state_machine = stepfunctions.StateMachine(self,"GetTetherStateMachine",
                                                              definition=get_tether_state_machine_definition,
                                                              timeout=Duration.days(1),
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
    
        
        ## Now we are creating the infrastructure to support our URL shortener
        
        redirect_asset_bucket = s3.Bucket(self,"REDIRECT_ASSET_BUCKET",
                                          removal_policy=RemovalPolicy.DESTROY,
                                          encryption=s3.BucketEncryption.S3_MANAGED,
                                          website_index_document="index.html",
                                          lifecycle_rules=[s3.LifecycleRule(
                                              abort_incomplete_multipart_upload_after=Duration.days(1),
                                              expiration=Duration.days(1),
                                              prefix="u/",
                                              enabled=True,
                                              id="expireOldRedirects"
                                          )])
        
          ##redirector API function:
        redirect_lambda = _lambda.Function(
            self,
            "RedirectFunction",
            code=_lambda.Code.from_asset("lambda/short_url_redirect"),
            handler="app.lambda_hanlder",
            runtime=_lambda.Runtime.PYTHON_3_8
        )
        
        redirect_lambda.add_environment("REDIRECT_ASSET_BUCKET", redirect_asset_bucket.bucket_name)
        redirect_asset_bucket.grant_read(redirect_lambda)
        
        redirect_api_integration = apigw.LambdaIntegration(redirect_lambda)
        redirect_root_resource = api.root.add_resource("redirect")
        redirect_key_resource = redirect_root_resource.add_resource("{key}")
        redirect_key_resource.add_method("GET",redirect_api_integration)
        
        cloudfront_origin = cloudfront_origins.HttpOrigin(domain_name=api_host)
        
        
        redirect_cloudfront_distribution = cloudfront.Distribution(
            self,
            "RedirectCloudFront",
            domain_names=[short_url_host],
            default_behavior=cloudfront.BehaviorOptions(
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                origin=cloudfront_origin
            ), certificate=acm.Certificate.from_certificate_arn(self,"CERT",cert_arn)
            
        )
        

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
        

from aws_cdk import (
    Duration,
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
    aws_route53 as route53
)
import os


from constructs import Construct


class MindTetherApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        
        # This is here so that if the stack is called by a parent deployment process, it is able to properly resolve
        # the path to src files
        project_build_base = os.path.realpath(__file__)[:os.path.realpath(__file__).rindex("/")] # folder = this files cwd
        project_build_base = project_build_base[0:project_build_base.rindex("/")] # folder = one directory above cwd
                
        stage_name = self.node.try_get_context("config")
        
        ## Define the Rest Api Gateway
        api = apigw.RestApi(self,"MindTetherApi-%s"%(stage_name))
    
        
        # This will be phased out with the completion on get-tether and subsequent shortcut update.
        if not self.node.try_get_context("short_url_host") or not self.node.try_get_context("api_host"):
            print("Missing values in cdk.json. Please check that short_url_host and api_host are provided.")
            exit()
        else:
            short_url_host_old = self.node.try_get_context("short_url_host")
            api_host = self.node.try_get_context("api_host")
        route53_zone = None    
        short_url_host = ""
        ## Get context for the current stage:
        stack_context = self.node.try_get_context(stage_name)
        if stack_context:
            api_host = stack_context['api_host']
            short_url_host = stack_context['short_url_host']
            if stack_context['route53_zone']:
                route53_zone = stack_context['route53_zone']
        else:
            print("Missing context. Please confirm context is supplied")
            exit()


        ## Create the S3 Asset Bucket
        if stage_name == "dev":
            removal_policy = RemovalPolicy.DESTROY
        else:
            removal_policy = RemovalPolicy.RETAIN
        asset_bucket = s3.Bucket(self,"AssetBucket", removal_policy=removal_policy)
        asset_bucket.add_lifecycle_rule(abort_incomplete_multipart_upload_after=Duration.days(1),
                                        enabled=True)
                
        short_url_bucket = s3.Bucket(self,"REDIRECT_ASSET_BUCKET",
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
        
        
        ###### Create Lambda Layers ######
        mindtether_assets_name="mindtether_assets"
        mindtether_assets = _lambda.LayerVersion(
            self, mindtether_assets_name, code=_lambda.Code.from_asset("%s/lambda_layers/mindtether_assets_layer"%(project_build_base)),
            layer_version_name="mindtether_assets"
        )
        mindtether_assets_path="/opt/%s" % (mindtether_assets_name)
        
        mindtether_core = _lambda.LayerVersion(
            self, "mindtether_core", code=_lambda.Code.from_asset("%s/lambda_layers/mindtether_core"%(project_build_base)),
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
            code=_lambda.Code.from_asset("%s/lambda/v0/generate_helper_image"%(project_build_base)),
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
            code=_lambda.Code.from_asset("%s/lambda/get_tether/get_background_image_info"%(project_build_base)),
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
            code=_lambda.Code.from_asset("%s/lambda/get_tether/get_day_image_info"%(project_build_base)),
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
            code=_lambda.Code.from_asset("%s/lambda/get_tether/compile_image"%(project_build_base)),
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="app.lambda_handler",
            timeout=Duration.seconds(60)
        )
        
        compile_image_lambda.add_environment("MIND_TETHER_API_ASSETS",asset_bucket.bucket_name)
        compile_image_lambda.add_environment("ASSET_LAYER_NAME", mindtether_assets_name)
        compile_image_lambda.add_environment("REQUEST_TABLE_NAME", get_tether_requests_table.table_name)
        compile_image_lambda.add_environment("SHORT_URL_HOST", short_url_host)
        compile_image_lambda.add_environment("SHORT_URL_BUCKET", short_url_bucket.bucket_name)
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
                                                   code=_lambda.Code.from_asset("%s/lambda/get_tether/get_tether_entry"%(project_build_base)),
                                                   handler="app.lambda_handler",
                                                   runtime=_lambda.Runtime.PYTHON_3_8)
        
        
        get_tether_requests_table.grant_read_write_data(get_tether_entry_lambda)
        get_tether_state_machine.grant_start_execution(get_tether_entry_lambda) 
        
        get_tether_entry_lambda.add_environment("REQUEST_TABLE_NAME", get_tether_requests_table.table_name)
        get_tether_entry_lambda.add_environment("STATE_MACHINCE_ARN", get_tether_state_machine.state_machine_arn)
            
        
        get_tether_entry_api_integration = apigw.LambdaIntegration(get_tether_entry_lambda)
        get_tether_entry_api_resource = api.root.add_resource("get-tether")
        
        get_tether_entry_api_resource.add_method("GET",get_tether_entry_api_integration)
        
        get_tether_status_lambda = _lambda.Function(self,
                                                    "get-tether-status",
                                                    code=_lambda.Code.from_asset("%s/lambda/get_tether/get_tether_status"%(project_build_base)),
                                                    handler="app.lambda_handler",
                                                    runtime=_lambda.Runtime.PYTHON_3_8)
        
        get_tether_status_lambda.add_environment("REQUEST_TABLE_NAME", get_tether_requests_table.table_name)
        
        get_tether_requests_table.grant_read_data(get_tether_status_lambda)
        
        get_tether_status_api_integration = apigw.LambdaIntegration(get_tether_status_lambda)
        get_tether_status_api_resource = get_tether_entry_api_resource.add_resource("{requestId}")
        
        get_tether_status_api_resource.add_method("GET",get_tether_status_api_integration)
    
        
        ## Now we are creating the infrastructure to support our URL shortener
        
       
          ##redirector API function:
        redirect_lambda = _lambda.Function(
            self,
            "RedirectFunction",
            code=_lambda.Code.from_asset("%s/lambda/short_url_redirect"%(project_build_base)),
            handler="app.lambda_hanlder",
            runtime=_lambda.Runtime.PYTHON_3_8
        )
        
        redirect_lambda.add_environment("REDIRECT_ASSET_BUCKET", short_url_bucket.bucket_name)
        short_url_bucket.grant_read(redirect_lambda)
        
        redirect_api_integration = apigw.LambdaIntegration(redirect_lambda)
        redirect_root_resource = api.root.add_resource("redirect")
        redirect_key_resource = redirect_root_resource.add_resource("{key}")
        redirect_key_resource.add_method("GET",redirect_api_integration)
        
        cloudfront_origin = cloudfront_origins.HttpOrigin(domain_name=api_host)
        
        # If not ACM ARN or short URL host are missing we will stick with the generated CNAME
        if route53_zone and short_url_host:
            hosted_zone = route53.HostedZone.from_hosted_zone_id(self,"route53zone", route53_zone)
            acm_cert = acm.Certificate(self, "ShortLinkCert", domain_name=short_url_host,
                                       validation=acm.CertificateValidation.from_dns(hosted_zone))
            redirect_cloudfront_distribution = cloudfront.Distribution(
            self,
            "RedirectCloudFront",
            default_behavior=cloudfront.BehaviorOptions(
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                origin=cloudfront_origin
            ), certificate=acm_cert,
            domain_names=[short_url_host]
        )
        else:
            redirect_cloudfront_distribution = cloudfront.Distribution(
            self,
            "RedirectCloudFront",
            default_behavior=cloudfront.BehaviorOptions(
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                origin=cloudfront_origin
            )
            )
        
        
        
        

                
        # Version based on context
        if self.node.try_get_context("deployment") == "prod":
            generate_helper_image_lambda_version = _lambda.Version(self,'GenerateHelperImageV1', function=generate_helper_image_lambda)
            generate_helper_image_lambda_alias = _lambda.Alias(self,"alias", alias_name="prod", version=generate_helper_image_lambda_version)
        else:
            generate_helper_image_lambda_alias = _lambda.Alias(self,"GenerateHelperImageAlias", alias_name="dev",version=generate_helper_image_lambda.latest_version)
            

        api_deployment = apigw.Deployment(self,"deployment",api=api)
        if stage_name != "prod":
            api_stage = apigw.Stage(self,stage_name,deployment=api_deployment, stage_name=stage_name)
        

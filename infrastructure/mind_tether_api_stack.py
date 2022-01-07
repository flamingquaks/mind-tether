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
    aws_route53 as route53,
    aws_route53_targets as route53_targets
)
import os

import json

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
        if not self.node.try_get_context("short_url_host"):
            print("Missing context value. Please check that short_url_host is provided")
            exit()
        else:
            short_url_host_old = self.node.try_get_context("short_url_host")
            
        route53_zone_id = None    
        route53_zone_name = None
        short_url_host = ""
        ## Get context for the current stage:
        stack_context = self.node.try_get_context(stage_name)
        if stack_context:
            short_url_host = stack_context['short_url_host']
            if stack_context['route53_zone'] and stack_context['route53_zone_name']:
                route53_zone_id = stack_context['route53_zone']
                route53_zone_name = stack_context['route53_zone_name']
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
        
        
        
        mindtether_core = _lambda.LayerVersion(
            self, "mindtether_core", code=_lambda.Code.from_asset("%s/lambda_layers/mindtether_core"%(project_build_base)),
            layer_version_name="mindtether_core"
        )
        
        
        short_url_generator = _lambda.Function(
            self,
            "ShortUrlGenerator",
            code=_lambda.Code.from_asset("%s/lambda/short_url_generator"%(project_build_base)),
            handler="app.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_8,
            timeout=Duration.seconds(5)
        )
        short_url_generator.add_layers(mindtether_core)
        
        short_url_generator.add_environment("SHORT_URL_BUCKET", short_url_bucket.bucket_name)
        short_url_generator.add_environment("SHORT_URL_HOST", short_url_host)
        
        short_url_bucket.grant_read_write(short_url_generator)
        
                
                
        generate_background_image = _lambda.Function(
            self,
            "GenerateBackgroundImage",
            code=_lambda.Code.from_asset(f"{project_build_base}/lambda/get_tether/generate_background_image"),
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="app.lambda_handler",
            timeout=Duration.seconds(15)
        )
        
        asset_bucket.grant_read_write(generate_background_image)
        generate_background_image.add_layers(mindtether_core)
        generate_background_image.add_environment("TETHER_ASSETS", asset_bucket.bucket_name)
        generate_background_image.add_environment("MIND_TETHER_CORE_PATH","/opt/mindtether_core")
        
        get_tether_requests_table = dynamodb.Table(
            self,
            "GetTetherRequests",
            partition_key=dynamodb.Attribute(
                name="requestId",
                type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl"
        )
        

        
        
        generate_short_url_task = stepfunction_tasks.LambdaInvoke(
            self,
            "Generate short URL",
            lambda_function=short_url_generator
        )
        
        generate_background_image_task = stepfunction_tasks.LambdaInvoke(
            self,
            "GenerateBackgroundTask",
            lambda_function=generate_background_image
        ).next(generate_short_url_task)
        
        
        
        update_tether_status_success_task = stepfunction_tasks.DynamoUpdateItem(self,
            "Update Tether Status as Completed",
            input_path=stepfunctions.JsonPath.string_at("$.Payload"),
            key={
                "requestId": stepfunction_tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.requestId"))
            }, table=get_tether_requests_table,
            expression_attribute_values={
                ":status" : stepfunction_tasks.DynamoAttributeValue.from_string("COMPLETE")
            },
            update_expression="SET create_status = :status")
        
        update_tether_status_fail_task = stepfunction_tasks.DynamoUpdateItem(self,
            "Update Tether Status as Failed",
            key={
                "requestId": stepfunction_tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.requestId"))
            }, table=get_tether_requests_table,
            expression_attribute_values={
                ":status" : stepfunction_tasks.DynamoAttributeValue.from_string("COMPLETE"),
                ":url": stepfunction_tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.short_url"))
            },
            update_expression="SET create_status = :status and url = :url")
       
        background_image_existence_query_task = stepfunction_tasks.CallAwsService(self,"Query for image",\
            service="s3", action="headObject",parameters={
                "Bucket": asset_bucket.bucket_name,
                "Key": stepfunctions.JsonPath.string_at("$.background_base_key")
            }, iam_resources=[asset_bucket.arn_for_objects("*")], result_path=stepfunctions.JsonPath.string_at("$.objectResult"))
        background_image_existence_query_task.add_catch(generate_background_image_task, result_path=stepfunctions.JsonPath.string_at("$.errorCatch"))
        background_image_existence_query_task.next(generate_short_url_task).next(update_tether_status_success_task)
        
        
         
            
    
        
            
        validate_input_step = stepfunctions.Choice(self,"Validate Input") \
            .when(stepfunctions.Condition.and_(stepfunctions.Condition.is_present("$.height"), stepfunctions.Condition.is_present("$.width"), \
                stepfunctions.Condition.is_present("$.day"), stepfunctions.Condition.is_present("$.background_base_key")),background_image_existence_query_task)
        
        get_tether_state_machine = stepfunctions.StateMachine(self,"GetTetherStateMachine",
                                                              definition=validate_input_step,
                                                              timeout=Duration.days(1),
                                                              state_machine_type=stepfunctions.StateMachineType.STANDARD)
        
        asset_bucket.grant_read(get_tether_state_machine)
        

        get_tether_entry_lambda = _lambda.Function(self,
                                                   "get-tether-entry",
                                                   code=_lambda.Code.from_asset("%s/lambda/get_tether/get_tether_entry"%(project_build_base)),
                                                   handler="app.lambda_handler",
                                                   runtime=_lambda.Runtime.PYTHON_3_8)
        
        get_tether_entry_lambda.add_layers(mindtether_core)
        
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
            handler="app.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_8
        )
        
        redirect_lambda.add_layers(mindtether_core)
        
        redirect_lambda.add_environment("SHORT_URL_BUCKET", short_url_bucket.bucket_name)
        redirect_lambda.add_environment("SHORT_URL_HOST",short_url_host)
        short_url_bucket.grant_read(redirect_lambda)
        
        method_response_302 = apigw.MethodResponse(status_code="302",response_parameters={
            "method.response.header.Location": True
        })
        
        redirect_api_integration_response = apigw.IntegrationResponse(
            status_code=method_response_302.status_code,
            response_parameters={
                "method.response.header.Location" : "integration.response.body.Redirect"
            },
            response_templates={
                "application/json": json.dumps({ "key": "$input.params('key')" })
            }
        )
        
        redirect_api_integration = apigw.LambdaIntegration(redirect_lambda, 
                                                           proxy=False,
                                                           integration_responses=[redirect_api_integration_response])
        
        
        
        redirect_root_resource = api.root.add_resource("redirect")
        redirect_key_resource = redirect_root_resource.add_resource("{key}")
        redirect_key_resource.add_method("GET",redirect_api_integration, method_responses=[method_response_302])
        api_origin = f"{api.rest_api_id}.execute-api.{self.region}.{self.url_suffix}"
        
        oai = cloudfront.OriginAccessIdentity(self,"cloudfront-oai")
        asset_bucket.grant_read(oai)
        
        redirect_cloudfront_origin = cloudfront_origins.HttpOrigin(domain_name=api_origin,origin_path="/prod/redirect")
        
        mindtether_image_assets_origin = cloudfront_origins.S3Origin(asset_bucket,origin_path="/images",origin_access_identity=oai)
        
        # If not ACM ARN or short URL host are missing we will stick with the generated CNAME
        if route53_zone_id and route53_zone_name and short_url_host:
            hosted_zone = route53.HostedZone.from_hosted_zone_attributes(self,"route53zone", hosted_zone_id=route53_zone_id, zone_name=route53_zone_name)
            acm_cert = acm.Certificate(self, "ShortLinkCert", domain_name=short_url_host,
                                       validation=acm.CertificateValidation.from_dns(hosted_zone))
            redirect_cloudfront_distribution = cloudfront.Distribution(
            self,
            "RedirectCloudFront",
            default_behavior=cloudfront.BehaviorOptions(
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                origin=redirect_cloudfront_origin
            ), certificate=acm_cert,
            domain_names=[short_url_host]
            )
            short_url_route53_record = route53.ARecord(self,
                                                          "shortUrlDnsRecord",
                                                          zone=hosted_zone,
                                                          target=route53.RecordTarget.from_alias(
                                                              route53_targets.CloudFrontTarget(
                                                                  redirect_cloudfront_distribution)
                                                              ),
                                                          record_name=short_url_host
                                                          )
        else:
            redirect_cloudfront_distribution = cloudfront.Distribution(
            self,
            "RedirectCloudFront",
            default_behavior=cloudfront.BehaviorOptions(
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                origin=redirect_cloudfront_origin
            )
            )

        redirect_cloudfront_distribution.add_behavior("/images/",mindtether_image_assets_origin)        
        
        
    
        apigw.Deployment(self,"deployment",api=api)
        # If these values are provided in the context, we assume that the domain name already exists and will import.
        # if stack_context and stack_context['api_config'] and route53_zone:
        #     api_details = stack_context['api_config']
        #     api_domain = apigw.DomainName.from_domain_name_attributes(self,"apiDomainName", apigw.DomainNameAttributes(
        #         domain_name=api_details['host'],domain_name_alias_hosted_zone_id=api_details['hosted_zone_id'], domain_name_alias_target=api_details['gateway_domain'])
        #         )
        #     api_domain.add_base_path_mapping(api,base_path=api_details['stage'])
        
        
        

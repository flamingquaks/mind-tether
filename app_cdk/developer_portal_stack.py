from typing_extensions import runtime
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_sam as sam
)

from constructs import Construct
class DeveloperPortalStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        portal_serverless_application_location="arn:aws:serverlessrepo:us-east-1:563878140293:applications/api-gateway-dev-portal"
        portal_serverless_application_version= "4.1.0"
        portal_cognito_domain = "auth.mindtether.app"

        
        portal_application = sam.CfnApplication(self,"PortalApp",
                                                location = sam.CfnApplication.ApplicationLocationProperty(
                                                    application_id=portal_serverless_application_location,
                                                    semantic_version=portal_serverless_application_version
                                                ),parameters= {
                                                    "ArtifactsS3BucketName" : "Artifacts",
                                                    "DevPortalSiteS3BucketName" : "Site",
                                                    "CognitoDomainNameOrPrefix": portal_cognito_domain
                                                })
        
       
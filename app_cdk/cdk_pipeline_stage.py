from constructs import Construct
from aws_cdk import (
    Stage,
    aws_apigateway
)

from .mind_tether_api_stack import MindTetherApiStack

class CdkPipelineStage(Stage):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        service = MindTetherApiStack(self,"API",  
                                        tags={
                                            "app":"mindtether",
                                            "cost-center": "mindtether-api"
                                            },
        )
from constructs import Construct
from aws_cdk import (
    Stage,
    aws_apigateway
)

from .mind_tether_api_stack import MindTetherApiStack

class MindTetherApiStage(Stage):
    def __init__(self, scope: Construct, id: str, stage_name:str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        stack = MindTetherApiStack(self,"API",  
                                        tags={
                                            "app":"mindtether",
                                            "cost-center": "mindtether-api",
                                            "stage_name": stage_name
                                            },
                                        stage_name=stage_name
        )
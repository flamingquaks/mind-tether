
from typing_extensions import runtime
from aws_cdk import (
    CfnParameter,
    Stack,
    pipelines,
    aws_apigateway as apigw,
    aws_codebuild as codebuild
)

from constructs import Construct

from app_cdk.cdk_pipeline_stage import CdkPipelineStage

class CdkPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        connection_arn = CfnParameter(
            self,
            "githubConnectionArn",
            type="String",
            description="The ARN for the GitHub connection"
        )
        
        if self.node.try_get_context("branch"):
            
            branch = self.node.try_get_context("branch")
        else:
            branch = "development"
        python_version=self.node.try_get_context("python_version")
        code_source = pipelines.CodePipelineSource.connection(
                    "flamingquaks/mind-tether", branch, connection_arn=connection_arn.value_as_string)
        build_spec = codebuild.BuildSpec.from_object({
            "phases": {
                "install": {
                    "runtime-versions": {
                        "python": self.node.try_get_context("python_version")
                    },
                    "commands": [
                        "pip install pipenv"
                    ]
                },
                "pre_build":{
                    
                }
            }
        })
        pipeline = pipelines.CodePipeline(self,"MindTetherPipeline", synth=pipelines.ShellStep(
                "Synth",
                input=code_source,
                commands=[
                "npm install -g aws-cdk",
                "pipenv install",
                "cd lambda_layers/mindtether_core",
                "pipenv lock -r > requirements.txt"
                "pip install -r ./requirements.txt --target ./python",
                "cd",
                "pipenv run cdk synth --verbose"
            ]
            ),code_build_defaults=pipelines.CodeBuildOptions(
                partial_build_spec=build_spec
            )
        )
        

        
        pipeline_stage = pipeline.add_stage(CdkPipelineStage(self,"Stage"))

        # 
        # dev_stage = Stage(self,"DevStage")
    
        # prod_stage = CdkPipelineStage(self,"prod")
        
        
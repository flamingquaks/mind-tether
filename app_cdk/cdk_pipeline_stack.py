
from typing_extensions import runtime
from aws_cdk import (
    Stack,
    Stage,
    pipelines,
    aws_apigateway as apigw,
    aws_codebuild as codebuild
)

from constructs import Construct

from app_cdk.cdk_pipeline_stage import CdkPipelineStage

class CdkPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        if self.node.try_get_context("branch"):
            
            branch = self.node.try_get_context("branch")
        else:
            branch = "development"
        python_version=self.node.try_get_context("python_version")
        code_source = pipelines.CodePipelineSource.connection(
                    "flamingquaks/mind-tether", branch, connection_arn=self.node.try_get_context("github_connection_arn"))
        build_spec = codebuild.BuildSpec.from_object({
            "phases": {
                "install": {
                    "runtime-versions": {
                        "python": self.node.try_get_context("python_version")
                    }
                }
            }
        })
        pipeline = pipelines.CodePipeline(self,"MindTetherPipeline", synth=pipelines.ShellStep(
                "Synth",
                input=code_source,
                commands=[
                "npm install -g aws-cdk",
                "pip install pipenv",
                "pipenv install",
                "npx cdk synth"
            ]
            ),code_build_defaults=pipelines.CodeBuildOptions(
                partial_build_spec=build_spec
            )
        )
        
        

        
        pipeline_stage = pipeline.add_stage(CdkPipelineStage(self,"Stage"))
        # 
        # dev_stage = Stage(self,"DevStage")
    
        # prod_stage = CdkPipelineStage(self,"prod")
        
        
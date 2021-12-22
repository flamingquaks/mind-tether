
from aws_cdk import (
    Stack,
    Stage,
    pipelines,
    aws_apigateway as apigw
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
        code_source = pipelines.CodePipelineSource.connection(
                    "flamingquaks/mind-tether", branch, connection_arn=self.node.try_get_context("github_connection_arn"))
        pipeline = pipelines.CodePipeline(self,"Pipeline", synth=pipelines.ShellStep(
                "Synth",
                input=code_source,
                commands=[
                "npm install -g aws-cdk",
                "curl https://pyenv.run | bash",
                "exec $SHELL"
                "pyenv install %s" % (self.node.try_get_context("python-version")),
                "pyenv virtualenv %s mind-tether" % (self.node.try_get_context("python-version")),
                "pyenv activate mind-tether"
                "pip install -r requirements.txt",
                "npx cdk synth"
            ]
            ))
        
        

        
        pipeline_stage = pipeline.add_stage(CdkPipelineStage(self,"Stage"))
        # 
        # dev_stage = Stage(self,"DevStage")
    
        # prod_stage = CdkPipelineStage(self,"prod")
        
        
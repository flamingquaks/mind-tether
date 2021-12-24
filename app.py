#!/usr/bin/env python3
import os

from aws_cdk import (
    App
)

from app_cdk.cdk_pipeline_stack import CdkPipelineStack

app = App()
cdk_pipeline_stack = CdkPipelineStack(app, "MindTether")

app.synth()

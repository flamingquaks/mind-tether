#!/usr/bin/env python3
import os

from aws_cdk import (
    App
)

from app_cdk.cdk_pipeline_stack import CdkPipelineStack

app = App()
mind_tether_dev_pipeline = CdkPipelineStack(app, "MindTether", branch="dev", tags={
    "app":"mind-tether"
})
mind_tether_prod_pipeline = CdkPipelineStack(app, "MindTether", branch="main", tags={
    "app":"mind-tether"
})

app.synth()

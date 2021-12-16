#!/usr/bin/env python3
import os

from aws_cdk import (
    App,Tags
)

from app_cdk.mind_tether_api_stack import MindTetherApiStack, PhoneBackgroundHelperStack

app = App()

mindtether_api_stack = MindTetherApiStack(app, "MindTetherApi",tags={
    "app":"mindtether",
    "cost-center": "mindtether-api"
})

app.synth()

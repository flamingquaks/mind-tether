#!/usr/bin/env python3
import os

from aws_cdk import (
    App,Tags
)

from app_cdk.phone_background_helper_stack import PhoneBackgroundHelperStack

app = App()

mindtether_api_stack = PhoneBackgroundHelperStack(app, "PhoneBackgroundHelperStack",tags={
    "app":"mindtether",
    "cost-center": "mindtether-api"
})

app.synth()

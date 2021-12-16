#!/usr/bin/env python3
import os

from aws_cdk import (
    App,Tags
)

from app_cdk.phone_background_helper_stack import PhoneBackgroundHelperStack
from app_cdk.developer_portal_stack import DeveloperPortalStack


app = App()

mindtether_api_stack = PhoneBackgroundHelperStack(app, "PhoneBackgroundHelperStack",tags={
    "app":"mindtether",
    "cost-center": "mindtether-api"
})

mindtether_developer_portal_stack = DeveloperPortalStack(app, "MT-DevPortal", tags={
    "app":"mindtether",
    "cost-center": "mindtether-developer-portal"
})

app.synth()

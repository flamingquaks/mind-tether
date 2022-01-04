#!/usr/bin/env python3
import os

from aws_cdk import (
    App
)

from infrastructure.mind_tether_api_stack import MindTetherApiStack

app = App()

mind_tether_stack = MindTetherApiStack(app,"MindTetherApi")

app.synth()

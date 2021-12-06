import aws_cdk as core
import aws_cdk.assertions as assertions

from phone_background_helper.phone_background_helper_stack import PhoneBackgroundHelperStack

# example tests. To run these tests, uncomment this file along with the example
# resource in phone_background_helper/phone_background_helper_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = PhoneBackgroundHelperStack(app, "phone-background-helper")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })

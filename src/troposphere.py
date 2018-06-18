#!/usr/bin/env python

from troposphere import Parameter, Ref, Template, GetAtt, Join, Output
from troposphere.dynamodb import KeySchema, AttributeDefinition, ProvisionedThroughput, Table
from troposphere.awslambda import Function, Code, Permission, Environment
from troposphere.iam import ManagedPolicy, Role
from troposphere.apigateway import RestApi, Method, Resource, Integration, IntegrationResponse, MethodResponse, Deployment, Stage
from troposphere.events import Rule, Target


# This email MUST be valided in your SES configuration.
stage_name = "v1"
dynamo_table_name="emailListTable"

## These don"t need adjustment if using the build script alongside docker (see readme) 
sub_src_file= "/app/subscribe.py"
unsub_src_file= "/app/unsubscribe.py"
emailer_src_file = "/app/emailer.py"

#
region_ref = Ref('AWS::Region')
t = Template()
t.add_description("BriteCore Daily Quote API Project. Forms an API Gateway + Lambda Functions + DynamoDB datastore")

from_email_param = t.add_parameter(
    Parameter(
        'FromEmail',
        ConstraintDescription='Must be an email address',
        Description='Email address that is verified to send outbound SES emails',
        Type="String",
        AllowedPattern=r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    ))

#email_from = Ref(from_email_param)

## DynamoDB table to hold email addresses
email_table = t.add_resource(Table(
    "emailListTable",
    AttributeDefinitions=[
        AttributeDefinition(
            AttributeName="email",
            AttributeType="S"
        ),
    ],
    KeySchema=[
        KeySchema(
            AttributeName="email",
            KeyType="HASH"
        )
    ],
    ProvisionedThroughput=ProvisionedThroughput(
        ReadCapacityUnits=5,
        WriteCapacityUnits=5
    ),
    TableName=dynamo_table_name
))

t.add_output(Output(
    "emailListTableName",
    Value=Ref(email_table),
    Description="Table Name",
))


# Policies
allow_db_access_policy = t.add_resource(ManagedPolicy(
    "AllowDynamoEmailList",
    Description="IAM Managed Policy to have full access to DynamoDB Email List Table",
    ManagedPolicyName="AllowDynamoEmailList",
    PolicyDocument={
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem", 
                "dynamodb:DeleteItem", 
                "dynamodb:GetItem",
                "dynamodb:Scan"
                ],
            "Resource": GetAtt(email_table, "Arn")
        }],
    }
))

allow_logs_policy = t.add_resource(ManagedPolicy(
    "AllowFullLogsPolicy",
    Description="Grants access to logs",
    ManagedPolicyName="AllowLogAccess",
    PolicyDocument={
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["logs:*"],
            "Resource": "arn:aws:logs:*:*:*"
        }],
    }
))

allow_ses_policy = t.add_resource(ManagedPolicy(
    "AllowSESPolicy",
    Description="Grants access to ses sending",
    ManagedPolicyName="AllowSESPolicy",
    PolicyDocument={
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "ses:SendEmail", 
                "ses:SendRawEmail"
                ],
            "Resource": "*"
        }],
    }
))


# IAM Role with needed policies attached
LambdaExecutionRole = t.add_resource(Role(
    "LambdaEmailListRole",
    Path="/",
    ManagedPolicyArns=[
        Ref("AllowDynamoEmailList"),
        Ref("AllowFullLogsPolicy")
        ],
    AssumeRolePolicyDocument={
        "Version": "2012-10-17",
        "Statement": [{
            "Action": ["sts:AssumeRole"],
            "Effect": "Allow",
            "Principal": {
                "Service": ["lambda.amazonaws.com"]
            }
        }]
    },
))

LambdaSesExecutionRole = t.add_resource(Role(
    "LambdaEmailSendRole",
    Path="/",
    ManagedPolicyArns=[
        Ref("AllowDynamoEmailList"),
        Ref("AllowFullLogsPolicy"),
        Ref("AllowSESPolicy")
        ],
    AssumeRolePolicyDocument={
        "Version": "2012-10-17",
        "Statement": [{
            "Action": ["sts:AssumeRole"],
            "Effect": "Allow",
            "Principal": {
                "Service": ["lambda.amazonaws.com"]
            }
        }]
    },
))

## Lambda functions - source code loaded from local files

# Subscribe Function
with open(sub_src_file, "r") as file:
    code = file.readlines()
    file.close()

EmailSubscribeFunction = t.add_resource(Function(
    "EmailSubscribeFunction",
    Code=Code(
        ZipFile=Join("", code)
    ),
    Handler="index.subscribe_handler",
    Role=GetAtt(LambdaExecutionRole, "Arn"),
    Runtime="python2.7",
    Description="Subscribe Endpoint. Adds provided email to dynamo table",
    FunctionName="EmailSubscribeFunction"
))

# Unsubscribe function
with open(unsub_src_file, "r") as file:
    code = file.readlines()
    file.close()

EmailUnsubscribeFunction = t.add_resource(Function(
    "EmailUnsubscribeFunction",
    Code=Code(
        ZipFile=Join("", code)
    ),
    Handler="index.unsubscribe_handler",
    Role=GetAtt(LambdaExecutionRole, "Arn"),
    Runtime="python2.7",
    Description="Unsubscribe Endpoint. Deletes provided email to dynamo table",
    FunctionName="EmailUnsubscribeFunction"
))

# Emailer
with open(emailer_src_file, "r") as file:
    code = file.readlines()
    file.close()

EmailSendFunction = t.add_resource(Function(
    "EmailSendFunction",
    Code=Code(
        ZipFile=Join("", code)
    ),
    Handler="index.daily_quote_handler",
    Role=GetAtt(LambdaSesExecutionRole, "Arn"),
    Runtime="python2.7",
    Environment=Environment(
        Variables={"email_from": Ref(from_email_param)}
    ),
    Description="Sends the Daily Quote. No endpoint, runs on a schedule.",
    FunctionName="EmailSendFunction"
))

### API GATEWAY
rest_api = t.add_resource(RestApi(
    "EmailListApi",
    Name="EmailListApi"
))

# /subscribe (POST)
subscribe_resource = t.add_resource(Resource(
    "subscribeResource",
    RestApiId=Ref(rest_api),
    PathPart="subscribe",
    ParentId=GetAtt("EmailListApi", "RootResourceId")
))

subscribe_method = t.add_resource(Method(
    "subscribeMethod",
    DependsOn="EmailSubscribeFunction",
    RestApiId=Ref(rest_api),
    AuthorizationType="NONE",
    ResourceId=Ref(subscribe_resource),
    HttpMethod="POST",
    Integration=Integration(
        Type="AWS",
        IntegrationHttpMethod="POST",
        IntegrationResponses=[
            IntegrationResponse(
                StatusCode="200"
            )
        ],
        Uri=Join("", [
            "arn:aws:apigateway:",
            Ref('AWS::Region'),
            ":lambda:path/2015-03-31/functions/",
            GetAtt(EmailSubscribeFunction, "Arn"),
            "/invocations"
        ])
    ),
    MethodResponses=[
        MethodResponse(
            "CatResponse",
            StatusCode="200"
        )
    ]
))

# /unsubscribe 
unsubscribe_resource = t.add_resource(Resource(
    "unsubscribeResource",
    RestApiId=Ref(rest_api),
    PathPart="unsubscribe",
    ParentId=GetAtt("EmailListApi", "RootResourceId")
))

unsubscribe_method = t.add_resource(Method(
    "unsubscribeMethod",
    DependsOn="EmailUnsubscribeFunction",
    RestApiId=Ref(rest_api),
    AuthorizationType="NONE",
    ResourceId=Ref(unsubscribe_resource),
    HttpMethod="POST",
    Integration=Integration(
        Type="AWS",
        IntegrationHttpMethod="POST",
        IntegrationResponses=[
            IntegrationResponse(
                StatusCode="200"
            )
        ],
        Uri=Join("", [
            "arn:aws:apigateway:",
            Ref('AWS::Region'),
            ":lambda:path/2015-03-31/functions/",
            GetAtt(EmailUnsubscribeFunction, "Arn"),
            "/invocations"
        ])
    ),
    MethodResponses=[
        MethodResponse(
            "CatResponse",
            StatusCode="200"
        )
    ]
))

resource = t.add_resource(Permission(
    "SubscribePermission",
    Action="lambda:InvokeFunction",
    Principal="apigateway.amazonaws.com",
    FunctionName=GetAtt(EmailSubscribeFunction, "Arn")
))

resource = t.add_resource(Permission(
    "UnsubscribePermission",
    Action="lambda:InvokeFunction",
    Principal="apigateway.amazonaws.com",
    FunctionName=GetAtt(EmailUnsubscribeFunction, "Arn")
))

# Deploy API
deployment = t.add_resource(Deployment(
    stage_name + "Deployment",
    DependsOn=["subscribeMethod", "unsubscribeMethod"],
    RestApiId=Ref(rest_api),
))

deployment_stage = t.add_resource(Stage(
    stage_name + "Stage",
    StageName=stage_name,
    RestApiId=Ref(rest_api),
    DeploymentId=Ref(deployment)
))

t.add_output([
    Output(
        "ApiEndpoint",
        Value=Join("", [
            "https://",
            Ref(rest_api),
            ".execute-api.",
            Ref('AWS::Region'),
            ".amazonaws.com/",
            stage_name
        ]),
        Description="Endpoint for this stage of the api"
    )
])

#Event Target (for email scheduling)
event_target_daily_emailer = Target(
    "DailyEmailerTarget",
    Arn=GetAtt("EmailSendFunction", "Arn"),
    Id="DailyEmailerTargetFunction"
)

# Schedule the emailer to run daily
event_rule_daily_emailer = t.add_resource(Rule(
    "DailyEmailsRule",
    ScheduleExpression="cron(0 23 * * ? *)", 
    Name="DailyEmailListRule",
    State="ENABLED",
    Targets=[event_target_daily_emailer]
))

# Project wants yaml instead of json
#print(t.to_json())
print(t.to_yaml())



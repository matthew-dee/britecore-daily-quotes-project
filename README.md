# BriteCore Daily Quote Programming Project

Project details and requirements: https://github.com/IntuitiveWebSolutions/PDPlatformEngineerProject

Included in this repo is a fully created `cloudformation.yaml` as requested in the project instructions. 
However, this project also includes all of the tooling and source code used to generate the cloudformation template from scratch.

## Quick Start 
**This application is already deployed and ready for use!**
```
POST https://d5ll82w6a5.execute-api.us-east-1.amazonaws.com/v1/subscribe
POST https://d5ll82w6a5.execute-api.us-east-1.amazonaws.com/v1/unsubscribe
```
In both methods, the API expects a content type of `application/json` with body contents denoting an `email` address:
```
{ "email": "myemail@example.com" }
```
The API will return an `HTTP 200` and appropriate message if succesful. A `400` will return with an appropriate message otherwise. 

The recipient will then get an "Inspirational Quote of the Day" along with the quote's author in their email every day at 11:00pm UTC. 


## Design & Workflow Notes
**Overall, the application creates:**
- 3x Lambda functions to perform subscribe, unsubscribe, and send email actions. 
- DynamoDB Table to hold the email addresses
- API Gateway Rest API with a subscribe and unsubscribe endpoint. No authorization is used for this demo project. 
- Various policies are also created

**Architecture**:
The Troposphere Python library has been utilized to generate the stack template. https://github.com/cloudtools/troposphere

The Lambda function source code is stored here locally and injected into the CloudFormation template itself so there is no S3 config needed to pull in the function source and it can cleanly stay with source control. 

It's suggested to review `src/troposphere.py` for details on how the template has been assembled.


## Deploying to your site:
- SES needs to be configured in your target AWS ecosystem in order to send outbound email.  
- Pass in the parameter `FromEmail` with a value of a working email address validated to send emails from your SES domain. 
- If using the AWS cli to deploy, ensure you've setup the aws cli with appropriate access keys (`aws configure`)

**There is 1 required parameter to pass to cloudformation**:
- `FromEmail` - This needs to be a validated email to be used as an email sender "from address." This address needs to be validated to send out via your SES domain.

**Example deploy**:
```
aws cloudformation create-stack \
--stack-name BriteCoreEmailer \
--region "us-east-1" \
--template-body file://cloudformation.yaml \
--parameters ParameterKey=FromEmail,ParameterValue="noreply@stacktech.xyz" \
--capabilities CAPABILITY_NAMED_IAM
```


## Generate a fresh cloudformation.yaml from scratch (optional): 

### Using Docker & Docker Compose: 
1. **From the project root**, run `./build-cloudformation.sh` - the `cloudformation.yaml` file will output in the project root. 

### Without using Docker & Docker Compose:
1. If needed, adjust any variable values in `src/troposphere.py` to comply with your build environment. 
2. Ensure Python2.7 is installed 
3. Install the Troposphere Python library (`pip install troposphere`)
3. Execute `./src/troposphere.py` - the template code will print to screen. 

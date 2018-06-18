from __future__ import print_function
import boto3
import json

def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }

def subscribe_handler(event, context):
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('emailListTable')
    except Exception, e:
        return respond(RuntimeError('Failed to connect to DynamoDB. Msg: ' + str(e)))
    if 'email' in event.keys(): # Ensure we have the proper payload
        email_exists = table.get_item( # Test if email already exists in db
           Key={'email': event['email']}
        )
        if 'Item' not in email_exists.keys(): # Email doesn't exist, ok to add it
            table.put_item(
                Item={'email': event['email']}
            )
            return respond(None, "Succesfully added " + event['email'])
        else:
            return respond(ValueError(event['email'] + " already exists in the mailing list"))
    else:
        return respond(ValueError('Value for email not provided'))
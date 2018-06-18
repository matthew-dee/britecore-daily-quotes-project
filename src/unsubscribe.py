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

def unsubscribe_handler(event, context):
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('emailListTable')
    except Exception, e:
        return respond(RuntimeError('Failed to connect to DynamoDB. Msg: ' + str(e)))
    if 'email' in event.keys(): # Ensure we have the proper payload
        email_exists = table.get_item( # Test if email already exists in db
           Key={'email': event['email']}
        )
        if 'Item' in email_exists.keys(): # Email exists, delete the record
            table.delete_item(
                Key={'email': event['email']}
            )
            return respond(None, "Succesfully removed " + event['email'] + " from the email list.")
        else:
            return respond(ValueError(event['email'] + " does not exist on the list."))
    else:
        return respond(ValueError('Value for email not provided'))
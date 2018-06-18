from botocore.vendored import requests
from email.mime.multipart import MIMEMultipart
import json
import boto3
import smtplib
import os

req_url = 'http://api.forismatic.com/api/1.0/?method=getQuote&format=json&lang=en'
email_from = os.environ['email_from'] # We're using SES, so this domain must be validated. 
email_subject = 'Daily Inspirational Quote' 

def get_email_list(): # Connects to Dynamo and gathers the list of emails. 
    email_list = []
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('emailListTable')
        dbitems = table.scan()
        for item in dbitems['Items']:
            email_list.append(item['email'])
    except Exception, e:
        print "Failed to gather email addresses: " + str(e)
        raise SystemExit(1)
    return email_list

def send_emails(quote_string, email_list): # Trigger SES through Boto3
    ses = boto3.client('ses')
    ses.send_email(
        Source=email_from,
        Destination={
            'ToAddresses': email_list
        },
        Message={
            'Subject': {
            'Data': email_subject,
            'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {
                    'Data': quote_string ,
                    'Charset': 'UTF-8'
                }
            }
        }
    )

def daily_quote_handler(event, context):
    email_list = get_email_list() # Get our recipients
    if len(email_list) > 0:       # Only if we actually have recipients
        r = requests.get(req_url) # Gather the quote from 3rd party API
        if r.status_code == 200:  # Ensure the response was good
            resp = json.loads(r.text)
            quote_string = resp["quoteText"] + " --" + resp["quoteAuthor"]
        else:
            print "Received invalid status code " + str(r.status_code) + " from " + req_url
            raise SystemExit(1)
        print quote_string
        send_emails(quote_string, email_list) # Send the quote out

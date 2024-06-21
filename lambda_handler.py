import json
import boto3
import uuid
import base64
from datetime import datetime
from botocore.exceptions import ClientError
from utils import decimal_default

def createTicket(event, context):

    # Initialize a session using Amazon DynamoDB and S3
    dynamodb = boto3.resource('dynamodb')
    s3 = boto3.client('s3')
    
    # Define the S3 bucket 
    bucket_name = 'cloudengr'

    # Select your DynamoDB table
    table = dynamodb.Table('ticket_table')
    
    
    # Extract the body from the event
    body = json.loads(event['body'])
    
    details = body['details']
    image_base64 = body['image_base64']
    user_id = body['user_id']
    username = body['username']
    address = body['address']
    building = body['building']
    floor = body['floor']
    place = body['place']
    problem_header = body['problem_header']
        
    image_key = f'problems/{uuid.uuid4()}.jpg'
    
    # Decode the base64 image
    try:
        image_data = base64.b64decode(image_base64)
    except (base64.binascii.Error, ValueError):
        return {
            'statusCode': 400,
            'body': json.dumps('image_base64 is not properly encoded')
        }
        
    # Upload the image to S3
    try:
        s3.put_object(Bucket=bucket_name, Key=image_key, Body=image_data, ContentType='image/jpeg')
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps(e.response['Error']['Message'])
        }
        
    ticket_id = f'{uuid.uuid4()}'
    current_time = f'{datetime.now()}'
    item={ 
            'problem_details': details, 
            'problem_image_key': image_key,
            'status': False,
            'ticket_id': ticket_id,
            'creation_date': current_time,
            'user_id': user_id,
            'assigned_role': "",
            'resolution_details':"",
            'resolution_image_key':"",
            'solved_date':"",
            'problem_header':problem_header,
            'username': username,
            'address': address,
            'floor': floor,
            'place': place,
            'building': building
        } 
    
    response = table.put_item(Item=item)
    
    body['ticket_id'] = ticket_id
    
    return {
        'statusCode': 200,
        'body': json.dumps(body)
    }

def updateTicket(event, context):
    # Initialize a session using Amazon DynamoDB and S3
    dynamodb = boto3.resource('dynamodb')
    s3 = boto3.client('s3')
    
    # Select your DynamoDB table
    table = dynamodb.Table('ticket_table')
    
    # Extract the body from the event
    body = json.loads(event['body'])
    
    # Ensure 'ticket_id' is in the event
    if 'ticket_id' not in body:
        return {
            'statusCode': 400,
            'body': json.dumps('ticket_id is missing from the event')
        }
    
    # Ensure 'resolution_details' is in the event
    if 'resolution_details' not in body:
        return {
            'statusCode': 400,
            'body': json.dumps('resolution_details is missing from the event')
        }
    
    # Ensure 'image_base64' is in the event
    if 'image_base64' not in body:
        return {
            'statusCode': 400,
            'body': json.dumps('image_base64 is missing from the event')
        }

    ticket_id = body['ticket_id']
    resolution_details = body['resolution_details']
    image_base64 = body['image_base64']
    
    # Decode the base64 image
    try:
        image_data = base64.b64decode(image_base64)
    except (base64.binascii.Error, ValueError):
        return {
            'statusCode': 400,
            'body': json.dumps('image_base64 is not properly encoded')
        }
    
    # Define the S3 bucket and create a unique image key
    bucket_name = 'cloudengr'
    image_key = f'resolutions/{uuid.uuid4()}.jpg'
    current_time = f'{datetime.now()}'
    
    try:
        # Upload the image to S3
        s3.put_object(Bucket=bucket_name, Key=image_key, Body=image_data, ContentType='image/jpeg')
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps(e.response['Error']['Message'])
        }
    
    try:
        # Update the item in the table
        response = table.update_item(
            Key={'ticket_id': ticket_id},
            UpdateExpression="set resolution_image_key = :rik, resolution_details = :rd, #s = :s, solved_date = :sd",
            ExpressionAttributeValues={
                ':rik': image_key,
                ':rd': resolution_details,
                ':s': True,
                ':sd': current_time
            },
            ExpressionAttributeNames={
                "#s": "status"
            },
            ReturnValues="UPDATED_NEW"
        )
        
        # Return the updated item
        return {
            'statusCode': 200,
            'body': json.dumps(response['Attributes'], default=decimal_default)
        }

    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps(e.response['Error']['Message'])
        }

def deleteTicket(event, context):
    # Initialize a session using Amazon DynamoDB
    dynamodb = boto3.resource('dynamodb')

    # Select your DynamoDB table
    table = dynamodb.Table('ticket_table')

    # Extract the ticket_id from the event
    ticket_id = event['pathParameters']['id']

    try:
        # Delete the item from the table
        response = table.delete_item(
            Key={'ticket_id': ticket_id},
            ConditionExpression="attribute_exists(ticket_id)"
        )

        return {
            'statusCode': 200,
            'body': json.dumps(f'Ticket {ticket_id} deleted successfully')
        }

    except ClientError as e:
        # Handle the case where the item does not exist
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            return {
                'statusCode': 404,
                'body': json.dumps(f'Ticket {ticket_id} not found')
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps(e.response['Error']['Message'])
            }
        
def getAllTickets(event, context):
    # Initialize a session using Amazon DynamoDB
    dynamodb = boto3.resource('dynamodb')

    # Select your DynamoDB table
    table = dynamodb.Table('ticket_table')

    try:
        # Scan the table to get all items
        response = table.scan()

        # Check if items exist
        if 'Items' in response:
            items = response['Items']
            return {
                'statusCode': 200,
                'body': json.dumps(items, default=decimal_default)
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps('No items found')
            }

    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps(e.response['Error']['Message'])
        }

def getTicketById(event, context):
    # Initialize a session using Amazon DynamoDB
    dynamodb = boto3.resource('dynamodb')

    # Select your DynamoDB table
    table = dynamodb.Table('ticket_table')

    # Define the primary key of the item to get
    
    ticket_id = event['pathParameters']['id']
    
    try:
        # Get the item from the table
        response = table.get_item(Key={'ticket_id': ticket_id})

        # Check if the item exists
        if 'Item' in response:
            item = response['Item']
            return {
                'statusCode': 200,
                'body': json.dumps(item, default=decimal_default)
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps('Item not found')
            }

    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps(e.response['Error']['Message'])
        }
    
def getTicketsByUserId(event, context):
    # Initialize a session using Amazon DynamoDB
    dynamodb = boto3.resource('dynamodb')

    # Select your DynamoDB table
    table = dynamodb.Table('ticket_table')

    # Define the primary key of the item to get
    user_id = event['pathParameters']['id']
    #user_id = event['id']
    
    try:
        # Get the item from the table
        response = table.scan(
        FilterExpression=Attr('user_id').eq(user_id))
        
        tickets = response['Items']
        
        if not tickets:
            return {
                'statusCode': 404,
                'body': json.dumps('No tickets found for the user_id.')
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps(e.response['Error']['Message'])
        }

def assignTicketRole(event, context):
    # Initialize a session using Amazon DynamoDB
    dynamodb = boto3.resource('dynamodb')

    # Select your DynamoDB table
    table = dynamodb.Table('ticket_table')
    
    # Extract the body from the event
    body = json.loads(event['body'])
    
    

    # Ensure 'ticket_id' and 'assigned_role' are in the event
    if 'ticket_id' not in body:
        return {
            'statusCode': 400,
            'body': json.dumps('ticket_id is missing from the event')
        }
    
    if 'assigned_role' not in body:
        return {
            'statusCode': 400,
            'body': json.dumps('assigned_role is missing from the event')
        }

    
    ticket_id = body['ticket_id']  # Convert to integer since the key is a number
    assigned_role = body['assigned_role']

    try:
        # Update the item in the table
        response = table.update_item(
            Key={'ticket_id': ticket_id},
            UpdateExpression="set assigned_role = :r",
            ExpressionAttributeValues={
                ':r': assigned_role
            },
            ReturnValues="UPDATED_NEW"
        )

        # Return the updated item
        return {
            'statusCode': 200,
            'body': json.dumps(body)
        }

    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps(e.response['Error']['Message'])
        }
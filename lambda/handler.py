import json
import boto3
import string
import random
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])
BASE_URL = os.environ['BASE_URL']

def generate_code(length=6):
    """Generate a random 6-character short code."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def shorten_url(original_url):
    """Store a new short code → URL mapping in DynamoDB."""
    code = generate_code()

    # Retry if code already exists (very unlikely but safe)
    for _ in range(5):
        try:
            table.put_item(
                Item={
                    'short_code': code,
                    'original_url': original_url,
                    'created_at': datetime.utcnow().isoformat(),
                    'hits': 0
                },
                ConditionExpression='attribute_not_exists(short_code)'
            )
            break
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            code = generate_code()

    return {
        'short_code': code,
        'short_url': f"{BASE_URL}/{code}",
        'original_url': original_url
    }

def redirect_url(code):
    """Look up a short code and return the original URL."""
    response = table.get_item(Key={'short_code': code})
    item = response.get('Item')

    if not item:
        return None

    # Increment hit counter
    table.update_item(
        Key={'short_code': code},
        UpdateExpression='SET hits = hits + :val',
        ExpressionAttributeValues={':val': 1}
    )

    return item['original_url']

def handler(event, context):
    import logging
    logging.getLogger().setLevel(logging.INFO)
    logging.info(f"EVENT: {json.dumps(event)}")
    logging.info(f"BODY TYPE: {type(event.get('body'))}")
    logging.info(f"BODY VALUE: {repr(event.get('body'))}")
    # API Gateway v2 sends method here
    http_context = event.get('requestContext', {}).get('http', {})
    method = http_context.get('method', '') or event.get('httpMethod', '')
    path = event.get('rawPath', '') or event.get('path', '/')

    # POST /shorten — create a short URL
    if method == 'POST' and path == '/shorten':
        try:
            raw_body = event.get('body') or '{}'
            if isinstance(raw_body, str):
                body = json.loads(raw_body)
            else:
                body = raw_body
            original_url = body.get('url', '').strip()

            if not original_url:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'url is required'})
                }

            if not original_url.startswith(('http://', 'https://')):
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'url must start with http:// or https://'})
                }

            result = shorten_url(original_url)
            return {
                'statusCode': 201,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(result)
            }

        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': str(e)})
            }

    # GET /{code} — redirect to original URL
    elif method == 'GET' and path != '/':
        code = path.lstrip('/')

        if not code:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'message': 'URL Shortener API', 'usage': 'POST /shorten with {"url": "https://example.com"}'})
            }

        original_url = redirect_url(code)

        if not original_url:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Short code {code} not found'})
            }

        return {
            'statusCode': 301,
            'headers': {'Location': original_url},
            'body': ''
        }

    # GET / — API info
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'message': 'URL Shortener API',
            'endpoints': {
                'POST /shorten': 'Create a short URL. Body: {"url": "https://example.com"}',
                'GET /{code}': 'Redirect to original URL'
            }
        })
    }

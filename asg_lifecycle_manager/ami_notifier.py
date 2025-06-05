import boto3
import requests

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    ami_id = event['ami_id']
    
    response = ec2.describe_images(ImageIds=[ami_id])
    image_info = response['Images'][0]
    
    state = image_info['State']
    ami_name = image_info.get('Name', 'Unknown')  # AMI 이름 가져오기
    
    if state == 'available':
        # 웹훅 호출
        webhook_url = "Webhook URL"
        headers = {'Content-Type': 'application/json'}
        data = {
            'body': 'AMI Is Available.',
            'connectColor': '#28a745',
            'connectInfo': [
                {
                    'title': 'Complete AMI Create. AMI State Available.',
                    'description': f'AMI ID: {ami_id}, Name: {ami_name}'
                }
            ]
        }
        try:
            res = requests.post(webhook_url, headers=headers, json=data)
            print(f"Webhook sent, status code: {res.status_code}")
        except Exception as e:
            print(f"Webhook send failed: {e}")

    return {
        'ami_id': ami_id,
        'ami_name': ami_name,
        'ami_state': state
    }

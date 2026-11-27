import os
from typing import Any
import boto3


def client() -> Any:
    return boto3.client('sqs', endpoint_url=os.getenv('SQS_ENDPOINT','http://localhost:9324'), region_name='us-east-1', aws_access_key_id='local', aws_secret_access_key='local')


def queue_url(sqs: Any) -> str:
    return str(sqs.get_queue_url(QueueName='jobs')['QueueUrl'])

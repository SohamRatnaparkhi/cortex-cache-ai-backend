import os

import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_S3_cortex_cache_manager_access_key")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_S3_cortex_cache_manager_secret_key")
AWS_REGION_NAME = os.getenv("AWS_S3_bucket_region")
AWS_BUCKET_NAME = os.getenv("AWS_S3_bucket_name")

# Create a session using your credentials
session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION_NAME
)

# Create an S3 client
s3 = session.client('s3')


class S3Operations():
    def __init__(self):
        pass

    def get_all_bucket_names(self) -> list[str]:
        response = s3.list_buckets()
        bucket_names = [bucket['Name'] for bucket in response['Buckets']]
        return bucket_names

    def get_all_objects(self, bucket_name=AWS_BUCKET_NAME) -> list[str]:
        response = s3.list_objects_v2(Bucket=bucket_name)
        object_keys = [obj['Key'] for obj in response.get('Contents', [])]
        return object_keys

    def get_object(self, object_key: str, bucket_name=AWS_BUCKET_NAME) -> dict:
        try:
            response = s3.get_object(Bucket=bucket_name, Key=object_key)
            return response
        except s3.exceptions.NoSuchKey:
            raise ValueError(f"Object with key '{object_key}' not found in bucket '{bucket_name}'")
        except Exception as e:
            raise RuntimeError(f"Error retrieving object from S3: {str(e)}")

    def upload_object(self, object_key: str, file_path: str, bucket_name=AWS_BUCKET_NAME) -> None:
        s3.upload_file(file_path, bucket_name, object_key)

    def download_object(self, object_key: str, bucket_name=AWS_BUCKET_NAME) -> bytes:
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        return response['Body'].read()

    def delete_object(self, object_key: str, bucket_name=AWS_BUCKET_NAME) -> dict:
        response = s3.delete_object(Bucket=bucket_name, Key=object_key)
        return response

    def delete_bucket(self, bucket_name=AWS_BUCKET_NAME) -> dict:
        response = s3.delete_bucket(Bucket=bucket_name)
        return response

    def create_bucket(self, bucket_name=AWS_BUCKET_NAME) -> dict:
        response = s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={
                                    'LocationConstraint': AWS_REGION_NAME})
        return response

    def copy_object(self, source_bucket_name: str, source_object_key: str, destination_bucket_name: str, destination_object_key: str) -> dict:
        copy_source = {'Bucket': source_bucket_name, 'Key': source_object_key}
        response = s3.copy_object(
            Bucket=destination_bucket_name, CopySource=copy_source, Key=destination_object_key)
        return response

    def move_object(self, source_bucket_name: str, source_object_key: str, destination_bucket_name: str, destination_object_key: str) -> dict:
        self.copy_object(source_bucket_name, source_object_key, destination_bucket_name, destination_object_key)
        response = self.delete_object(source_object_key, source_bucket_name)
        return response

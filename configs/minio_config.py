"""
MinIO / S3-compatible storage client factory.
"""
from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from configs.settings import MINIO_ACCESS_KEY, MINIO_ENDPOINT, MINIO_SECRET_KEY


def get_s3_client():
    """Return a boto3 S3 client pointed at the local MinIO instance."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    )


def ensure_bucket_exists(bucket: str) -> None:
    """Create bucket if it does not yet exist."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        error_code = int(exc.response["Error"]["Code"])
        if error_code == 404:
            client.create_bucket(Bucket=bucket)
        else:
            raise

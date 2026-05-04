import logging
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=_settings.s3_endpoint_url or None,
            aws_access_key_id=_settings.s3_access_key,
            aws_secret_access_key=_settings.s3_secret_key,
            config=Config(connector_pool_maxsize=10),
        )
    return _s3_client


def apply_7day_expiration_policy(bucket: str, prefix: str = "segments/") -> bool:
    """
    Apply a 7-day expiration lifecycle rule to objects under prefix.
    Creates or updates a lifecycle rule on the bucket.
    """
    client = get_s3_client()
    try:
        client.put_bucket_lifecycle_configuration(
            Bucket=bucket,
            LifecycleConfiguration={
                "Rules": [
                    {
                        "ID": "segment-7day-retention",
                        "Status": "Enabled",
                        "Prefix": prefix,
                        "Expiration": {"Days": 7},
                    },
                    {
                        "ID": "abort-incomplete-multipart-uploads",
                        "Status": "Enabled",
                        "Prefix": prefix,
                        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                    },
                ]
            },
        )
        logger.info(f"Lifecycle rule applied to s3://{bucket}/{prefix} — 7-day expiration")
        return True
    except ClientError as e:
        logger.error(f"Failed to apply lifecycle policy: {e}")
        return False


def delete_object(bucket: str, key: str) -> bool:
    """Delete an object from S3."""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Deleted s3://{bucket}/{key}")
        return True
    except ClientError as e:
        logger.error(f"Failed to delete s3://{bucket}/{key}: {e}")
        return False


def list_objects(bucket: str, prefix: str = "", max_keys: int = 1000) -> list[dict]:
    """List objects under prefix, returning key and last_modified."""
    client = get_s3_client()
    try:
        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_keys)
        return [
            {"key": obj["Key"], "last_modified": obj["LastModified"]}
            for obj in response.get("Contents", [])
        ]
    except ClientError as e:
        logger.error(f"Failed to list objects in s3://{bucket}/{prefix}: {e}")
        return []


def object_exists(bucket: str, key: str) -> bool:
    client = get_s3_client()
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def presign_url(bucket: str, key: str, expires_seconds: int = 3600) -> str | None:
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL for s3://{bucket}/{key}: {e}")
        return None
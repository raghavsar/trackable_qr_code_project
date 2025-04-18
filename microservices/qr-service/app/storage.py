from minio import Minio
from minio.error import S3Error
import os
from io import BytesIO
import magic
from datetime import timedelta, datetime
from typing import Optional
import logging
import json
import base64
from PIL import Image
import requests

logger = logging.getLogger(__name__)

class MinioStorage:
    def __init__(self):
        # Load environment variables with explicit defaults and logging
        minio_endpoint = os.getenv("MINIO_ENDPOINT")
        minio_public_endpoint = os.getenv("MINIO_PUBLIC_ENDPOINT")
        minio_access_key = os.getenv("MINIO_ACCESS_KEY", "qr_service_user")
        minio_secret_key = os.getenv("MINIO_SECRET_KEY", "qr_service_password_123")
        minio_use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "qrcodes")

        # Log all configuration values (except secret key)
        logger.info("MinIO Configuration:")
        logger.info(f"MINIO_ENDPOINT: {minio_endpoint}")
        logger.info(f"MINIO_PUBLIC_ENDPOINT: {minio_public_endpoint}")
        logger.info(f"MINIO_ACCESS_KEY: {minio_access_key}")
        logger.info(f"MINIO_USE_SSL: {minio_use_ssl}")
        logger.info(f"MINIO_BUCKET_NAME: {self.bucket_name}")

        if not minio_endpoint:
            logger.warning("MINIO_ENDPOINT not set, using default: minio:9000")
            minio_endpoint = "minio:9000"

        if not minio_public_endpoint:
            logger.warning("MINIO_PUBLIC_ENDPOINT not set, using default: https://qr.phonon.io/minio")
            minio_public_endpoint = "https://qr.phonon.io/minio"

        logger.info(f"Final MinIO configuration - endpoint: {minio_endpoint}, public endpoint: {minio_public_endpoint}")

        self.client = Minio(
            endpoint=minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=minio_use_ssl
        )
        self.endpoint = minio_public_endpoint
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            logger.info(f"Checking if bucket {self.bucket_name} exists...")
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(f"Creating bucket {self.bucket_name}...")
                self.client.make_bucket(self.bucket_name)

                # Set bucket policy for public read
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                        }
                    ]
                }

                try:
                    logger.info("Setting bucket policy for public read access...")
                    self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
                    logger.info("Bucket policy set successfully")
                except S3Error as policy_error:
                    logger.error(f"Failed to set bucket policy: {str(policy_error)}")
                    # Continue even if policy setting fails
                    pass

                logger.info("Bucket created successfully")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except S3Error as e:
            logger.error(f"MinIO Error: {str(e)}")
            if "AccessDenied" in str(e):
                logger.error("Access denied. Please check MinIO credentials and permissions.")
            raise Exception(f"Failed to create/check bucket: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

    async def upload_qr_code(self, qr_image: BytesIO, object_name: str) -> str:
        """
        Upload a QR code image to MinIO

        Args:
            qr_image: BytesIO object containing the QR code image
            object_name: Name to give the object in storage

        Returns:
            str: Public URL to access the uploaded QR code
        """
        try:
            logger.info(f"Uploading QR code: {object_name}")

            # Get the image data and size
            qr_image.seek(0)
            image_data = qr_image.read()
            size = len(image_data)

            # Detect content type
            content_type = magic.from_buffer(image_data, mime=True)
            logger.info(f"Detected content type: {content_type}")

            # Upload the image
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=BytesIO(image_data),
                length=size,
                content_type=content_type
            )
            logger.info(f"QR code uploaded successfully: {object_name}")

            # Return permanent public URL through the API gateway
            # Use the API gateway URL format for storage access
            api_base_url = os.getenv("API_GATEWAY_URL", "https://qr.phonon.io/api")
            api_base_url = api_base_url.rstrip('/')
            public_url = f"{api_base_url}/v1/storage/{self.bucket_name}/{object_name}"
            logger.info(f"Generated public URL via API gateway: {public_url}")

            return public_url

        except S3Error as e:
            logger.error(f"MinIO Error during upload: {str(e)}")
            raise Exception(f"Failed to upload QR code: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during upload: {str(e)}")
            raise

    async def get_qr_code_url(self, object_name: str) -> str:
        """
        Get the public URL for accessing a QR code

        Args:
            object_name: Name of the object in storage

        Returns:
            str: Public URL to access the QR code
        """
        api_base_url = os.getenv("API_GATEWAY_URL", "https://qr.phonon.io/api")
        api_base_url = api_base_url.rstrip('/')
        return f"{api_base_url}/v1/storage/{self.bucket_name}/{object_name}"

    async def delete_qr_code(self, object_name: str):
        """
        Delete a QR code from storage

        Args:
            object_name: Name of the object to delete
        """
        try:
            logger.info(f"Deleting QR code: {object_name}")
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"QR code deleted successfully: {object_name}")
        except S3Error as e:
            logger.error(f"MinIO Error during deletion: {str(e)}")
            raise Exception(f"Failed to delete QR code: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during deletion: {str(e)}")
            raise

class StorageService:
    def __init__(self):
        self.client = Minio(
            endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "qr_service_user"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "qr_service_password_123"),
            secure=os.getenv("MINIO_USE_SSL", "false").lower() == "true"
        )
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "qrcodes")
        self.public_endpoint = os.getenv("MINIO_PUBLIC_ENDPOINT", "https://qr.phonon.io/minio")

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {str(e)}")
            raise

    async def upload_profile_photo(self, photo_data: str, user_id: str, vcard_id: str = None) -> Optional[str]:
        """
        Upload a profile photo to MinIO and return a publicly accessible URL
        Args:
            photo_data: Base64 string or URL of the photo
            user_id: User ID for the photo
            vcard_id: VCard ID for the photo
        Returns:
            Public URL of the uploaded photo
        """
        try:
            # Handle base64 data
            if photo_data.startswith('data:image'):
                # Extract image data and format
                format_type = photo_data.split(';')[0].split('/')[1]
                image_data = base64.b64decode(photo_data.split(',')[1])

                # Process image to reduce size if needed
                img = Image.open(BytesIO(image_data))

                # Resize if too large (max 400x400 for vCard compatibility)
                if max(img.size) > 400:
                    img.thumbnail((400, 400), Image.Resampling.LANCZOS)

                # Convert to RGB if needed
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Save to bytes with compression
                output = BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                image_data = output.getvalue()
                format_type = 'jpeg'  # Force JPEG for better compatibility

                # Generate filename with timestamp
                timestamp = datetime.utcnow().timestamp()
                if vcard_id:
                    filename = f"users/{user_id}/pfp_vcard/{vcard_id}_{timestamp}.{format_type}"
                else:
                    filename = f"users/{user_id}/profile_photos/profile_{timestamp}.{format_type}"

            else:
                # If it's already a URL, check if it's our MinIO URL
                if self.public_endpoint in photo_data:
                    return photo_data

                # For external URLs, download and process
                try:
                    response = requests.get(photo_data, timeout=5)
                    response.raise_for_status()
                    img = Image.open(BytesIO(response.content))

                    # Process image same as base64
                    if max(img.size) > 400:
                        img.thumbnail((400, 400), Image.Resampling.LANCZOS)

                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')

                    output = BytesIO()
                    img.save(output, format='JPEG', quality=85, optimize=True)
                    image_data = output.getvalue()
                    format_type = 'jpeg'

                    timestamp = datetime.utcnow().timestamp()
                    if vcard_id:
                        filename = f"users/{user_id}/pfp_vcard/{vcard_id}_{timestamp}.{format_type}"
                    else:
                        filename = f"users/{user_id}/profile_photos/profile_{timestamp}.{format_type}"
                except Exception as e:
                    logger.error(f"Failed to process external URL: {str(e)}")
                    return photo_data

            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=filename,
                data=BytesIO(image_data),
                length=len(image_data),
                content_type=f"image/jpeg"
            )

            # Return public URL via API gateway
            api_base_url = os.getenv("API_GATEWAY_URL", "https://qr.phonon.io/api")
            api_base_url = api_base_url.rstrip('/')
            return f"{api_base_url}/v1/storage/{self.bucket_name}/{filename}"

        except Exception as e:
            logger.error(f"Error uploading profile photo: {str(e)}")
            return None

storage_service = StorageService()

# Create a singleton instance
storage = MinioStorage()
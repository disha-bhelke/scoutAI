import os
from typing import Dict, Any, Optional
import cloudinary
import cloudinary.uploader
import cloudinary.api
from config import settings


def init_cloudinary():
    """Initializes Cloudinary with configured credentials or CLOUDINARY_URL."""
    if settings.CLOUDINARY_URL:
        # Automatically parses cloudinary://API_KEY:API_SECRET@CLOUD_NAME
        cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)
    elif settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME.strip(),
            api_key=settings.CLOUDINARY_API_KEY.strip(),
            api_secret=settings.CLOUDINARY_API_SECRET.strip(),
            secure=True
        )


class CloudinaryStorageService:
    """Handles uploading, listing, and downloading documents to/from Cloudinary."""

    def __init__(self):
        init_cloudinary()

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        folder: str = "scout_documents"
    ) -> Dict[str, Any]:
        """
        Uploads a raw document (PDF, TXT) to Cloudinary storage.
        Returns the upload metadata containing secure_url and public_id.
        """
        # Upload as raw resource type so PDFs and TXT files preserve original bytes
        result = cloudinary.uploader.upload(
            file_bytes,
            resource_type="raw",
            folder=folder,
            public_id=filename,
            use_filename=True,
            unique_filename=False,
            overwrite=True
        )
        return {
            "public_id": result.get("public_id"),
            "url": result.get("secure_url") or result.get("url"),
            "filename": filename,
            "bytes": result.get("bytes", len(file_bytes)),
            "format": result.get("format")
        }

    def list_documents(self, folder: str = "scout_documents") -> list:
        """Lists all uploaded raw documents in the Cloudinary folder."""
        try:
            res = cloudinary.api.resources(
                resource_type="raw",
                type="upload",
                prefix=folder,
                max_results=100
            )
            return res.get("resources", [])
        except Exception as e:
            print(f"[Cloudinary] Error listing documents: {e}")
            return []

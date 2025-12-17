import os
import json
import time
from google.cloud import storage
from google.api_core.exceptions import NotFound
from datetime import datetime

class GCSCache:
    """
    Google Cloud Storage backed cache for persistent storage of stock data.
    """
    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name or os.environ.get("GCS_CACHE_BUCKET", "stock-analyzer-cache")
        self._client = None
        self._bucket = None
        
        # Initialize lazily to avoid startup errors if creds are missing
        self._check_connection()

    def _ensure_client(self):
        """Ensure GCS client and bucket exist."""
        if self._client is None:
            try:
                self._client = storage.Client()
                self._bucket = self._client.bucket(self.bucket_name)
                # Check if bucket exists, if not try to create it
                if not self._bucket.exists():
                    try:
                        self._bucket.create(location="US") 
                        print(f"Created GCS bucket: {self.bucket_name}")
                    except Exception as e:
                        print(f"Failed to create bucket {self.bucket_name}: {e}")
                        # Fallback: maybe we can't create it but it exists? 
                        # If exists() returned False, we can't use it.
                        self._bucket = None
            except Exception as e:
                print(f"Error initializing GCS client: {e}")
                self._client = None
                self._bucket = None

    def _check_connection(self):
        """Try to initialize and print status."""
        self._ensure_client()
        if self._bucket and self._bucket.exists():
            print(f"GCS Cache initialized. Connected to bucket: {self.bucket_name}")
        else:
            print(f"Warning: GCS Cache could not connect to bucket: {self.bucket_name}. Cache operations will fail silently or return None.")

    def get(self, key: str):
        """Get value from GCS. Returns None if not found."""
        self._ensure_client()
        if not self._bucket:
            return None
        
        try:
            blob = self._bucket.blob(key)
            if blob.exists():
                data = blob.download_as_text()
                return json.loads(data)
        except Exception as e:
            print(f"GCS Cache get error for {key}: {e}")
        return None

    def set(self, key: str, value: any, ttl: int = None):
        """
        Set value in GCS. 
        TTL is ignored as per requirement to remove one hour TTL.
        """
        self._ensure_client()
        if not self._bucket:
            return
            
        try:
            blob = self._bucket.blob(key)
            blob.upload_from_string(
                json.dumps(value),
                content_type="application/json"
            )
        except Exception as e:
            print(f"GCS Cache set error for {key}: {e}")

    def delete(self, key: str):
        """Delete a specific key."""
        self._ensure_client()
        if not self._bucket:
            return False
            
        try:
            blob = self._bucket.blob(key)
            if blob.exists():
                blob.delete()
                return True
        except Exception as e:
            print(f"GCS Cache delete error for {key}: {e}")
        return False

    def clear(self):
        """Clear all blobs in the bucket."""
        self._ensure_client()
        if not self._bucket:
            return 0
            
        count = 0
        try:
            blobs = list(self._client.list_blobs(self.bucket_name))
            for blob in blobs:
                blob.delete()
                count += 1
        except Exception as e:
            print(f"GCS Cache clear error: {e}")
        return count

    def stats(self):
        """
        Get basic stats. Note: Listing all blobs can be slow for large buckets.
        """
        self._ensure_client()
        if not self._bucket:
            return {"status": "disconnected", "error": "No GCS connection"}

        try:
            blobs = list(self._client.list_blobs(self.bucket_name))
            total = len(blobs)
            return {
                "total": total,
                "bucket": self.bucket_name,
                "status": "connected"
            }
        except Exception as e:
             return {"status": "error", "error": str(e)}

    def get_created_timestamp(self, key: str):
        """Get the creation timestamp of the blob."""
        self._ensure_client()
        if not self._bucket:
            return 0
            
        try:
            blob = self._bucket.blob(key)
            blob.reload() # Ensure metadata is loaded
            if blob.exists():
                # time_created is a datetime object
                return blob.time_created.timestamp()
        except Exception as e:
            print(f"GCS Cache timestamp error for {key}: {e}")
        return 0

    def keys(self):
        """List all keys."""
        self._ensure_client()
        if not self._bucket:
            return []
            
        try:
            return [blob.name for blob in self._client.list_blobs(self.bucket_name)]
        except Exception:
            return []

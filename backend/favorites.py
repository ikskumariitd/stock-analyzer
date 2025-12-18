"""
Favorites storage module with Google Cloud Storage support and local fallback.

Manages persistent favorites list.
"""

import os
import json
from typing import List, Optional
from threading import Lock


class FavoritesStorage:
    """
    Manages favorites persistence with GCS + local fallback.
    
    Priority:
    1. GCS bucket (if GCS_BUCKET env var is set) - read/write
    2. Local favorites.json - read/write fallback
    """
    
    def __init__(self):
        self._lock = Lock()
        self._gcs_client = None
        self._bucket = None
        self._bucket_name = os.environ.get("GCS_BUCKET")
        self._favorites_blob = "favorites.json"
        
        # Local fallback file path
        self._local_file_path = os.path.join(
            os.path.dirname(__file__), 
            "favorites.json"
        )
        
        self._is_gcs_enabled = False
        self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """Initialize the storage backend."""
        if self._bucket_name:
            try:
                from google.cloud import storage
                self._gcs_client = storage.Client()
                self._bucket = self._gcs_client.bucket(self._bucket_name)
                # Test access by checking if bucket exists
                if self._bucket.exists():
                    self._is_gcs_enabled = True
                    print(f"[FAVORITES] Using GCS bucket: {self._bucket_name}")
                    self._init_gcs_favorites()
                    return
            except Exception as e:
                print(f"[WARN] GCS initialization failed for Favorites: {e}")
                print("       Falling back to local file storage")
        
        # Fallback to local
        self._is_gcs_enabled = False
        print(f"[FAVORITES] Using local persistence: {self._local_file_path}")
    
    def _init_gcs_favorites(self) -> None:
        """Initialize favorites.json in GCS if it doesn't exist."""
        try:
            blob = self._bucket.blob(self._favorites_blob)
            if not blob.exists():
                data = {"favorites": []}
                blob.upload_from_string(
                    json.dumps(data, indent=2),
                    content_type="application/json"
                )
                print("[FAVORITES] Initialized empty favorites in GCS")
        except Exception as e:
            print(f"[WARN] Failed to initialize GCS favorites: {e}")
    
    def _read_local_favorites(self) -> List[str]:
        """Read favorites from local json file."""
        if not os.path.exists(self._local_file_path):
            return []
        try:
            with open(self._local_file_path, 'r') as f:
                data = json.load(f)
                return data.get("favorites", [])
        except Exception as e:
            print(f"[WARN] Failed to read local favorites: {e}")
            return []
            
    def _write_local_favorites(self, favorites: List[str]) -> bool:
        """Write favorites to local json file."""
        try:
            with open(self._local_file_path, 'w') as f:
                json.dump({"favorites": favorites}, f, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to write local favorites: {e}")
            return False
    
    def _read_gcs_favorites(self) -> List[str]:
        """Read favorites from GCS."""
        try:
            blob = self._bucket.blob(self._favorites_blob)
            if not blob.exists():
                return []
            content = blob.download_as_text()
            data = json.loads(content)
            return data.get("favorites", [])
        except Exception as e:
            print(f"[WARN] Failed to read GCS favorites: {e}")
            return []
    
    def _write_gcs_favorites(self, favorites: List[str]) -> bool:
        """Write favorites to GCS."""
        try:
            blob = self._bucket.blob(self._favorites_blob)
            data = {"favorites": favorites}
            blob.upload_from_string(
                json.dumps(data, indent=2),
                content_type="application/json"
            )
            return True
        except Exception as e:
            print(f"[ERROR] Failed to write GCS favorites: {e}")
            return False
    
    def get_favorites(self) -> List[str]:
        """Get current favorites list."""
        with self._lock:
            if self._is_gcs_enabled and self._bucket:
                return self._read_gcs_favorites()
            else:
                return self._read_local_favorites()
    
    def add_favorite(self, symbol: str) -> dict:
        """Add stock to favorites."""
        symbol = symbol.upper().strip()
        if not symbol:
            return {"success": False, "message": "Invalid symbol"}
        
        with self._lock:
            if self._is_gcs_enabled and self._bucket:
                favorites = self._read_gcs_favorites()
                save_func = self._write_gcs_favorites
            else:
                favorites = self._read_local_favorites()
                save_func = self._write_local_favorites
            
            if symbol in favorites:
                return {
                    "success": False, 
                    "message": f"{symbol} is already in favorites",
                    "favorites": favorites
                }
            
            favorites.insert(0, symbol)
            
            if save_func(favorites):
                return {
                    "success": True, 
                    "message": f"Added {symbol} to favorites",
                    "favorites": favorites
                }
            else:
                return {"success": False, "message": "Failed to save favorites"}
    
    def remove_favorite(self, symbol: str) -> dict:
        """Remove stock from favorites."""
        symbol = symbol.upper().strip()
        
        with self._lock:
            if self._is_gcs_enabled and self._bucket:
                favorites = self._read_gcs_favorites()
                save_func = self._write_gcs_favorites
            else:
                favorites = self._read_local_favorites()
                save_func = self._write_local_favorites
            
            if symbol not in favorites:
                return {
                    "success": False, 
                    "message": f"{symbol} is not in favorites",
                    "favorites": favorites
                }
            
            favorites.remove(symbol)
            
            if save_func(favorites):
                return {
                    "success": True, 
                    "message": f"Removed {symbol} from favorites",
                    "favorites": favorites
                }
            else:
                return {"success": False, "message": "Failed to save favorites"}

    def clear_favorites(self) -> dict:
        """Clear all favorites."""
        with self._lock:
            if self._is_gcs_enabled and self._bucket:
                save_func = self._write_gcs_favorites
            else:
                save_func = self._write_local_favorites
            
            favorites = []
            if save_func(favorites):
                return {
                    "success": True, 
                    "message": "Favorites cleared",
                    "favorites": favorites
                }
            else:
                return {"success": False, "message": "Failed to save favorites"}
    
    @property
    def is_gcs_enabled(self) -> bool:
        return self._is_gcs_enabled
    
    @property
    def storage_backend(self) -> str:
        return "gcs" if self._is_gcs_enabled else "local"


# Global instance
_favorites_storage: Optional[FavoritesStorage] = None

def get_favorites_storage() -> FavoritesStorage:
    """Get or create the global favorites storage instance."""
    global _favorites_storage
    if _favorites_storage is None:
        _favorites_storage = FavoritesStorage()
    return _favorites_storage

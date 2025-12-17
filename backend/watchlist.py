"""
Watchlist storage module with Google Cloud Storage support and local fallback.

Manages persistent watchlist that survives server restarts.
Falls back to local config.json (read-only) when GCS is not configured.
"""

import os
import json
from typing import List, Optional
from threading import Lock


class WatchlistStorage:
    """
    Manages watchlist persistence with GCS + local fallback.
    
    Priority:
    1. GCS bucket (if GCS_BUCKET env var is set) - read/write
    2. Local config.json - read-only fallback
    """
    
    def __init__(self):
        self._lock = Lock()
        self._gcs_client = None
        self._bucket = None
        self._bucket_name = os.environ.get("GCS_BUCKET")
        self._watchlist_blob = "watchlist.json"
        self._local_config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "frontend", 
            "config.json"
        )
        self._is_writable = False
        self._cached_watchlist: Optional[List[str]] = None
        
        self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """Initialize the storage backend."""
        if self._bucket_name:
            try:
                from google.cloud import storage
                self._gcs_client = storage.Client()
                self._bucket = self._gcs_client.bucket(self._bucket_name)
                # Test access
                self._bucket.exists()
                self._is_writable = True
                print(f"[WATCHLIST] Using GCS bucket: {self._bucket_name}")
                
                # Initialize watchlist in GCS if not exists
                self._init_gcs_watchlist()
                return
            except Exception as e:
                print(f"[WARN] GCS initialization failed: {e}")
                print("       Falling back to local config.json (read-only)")
        
        # Fallback to local config
        self._is_writable = False
        print("[WATCHLIST] Using local config.json (read-only mode)")
    
    def _init_gcs_watchlist(self) -> None:
        """Initialize watchlist.json in GCS if it doesn't exist."""
        try:
            blob = self._bucket.blob(self._watchlist_blob)
            if not blob.exists():
                # Copy from local config.json
                local_watchlist = self._read_local_watchlist()
                data = {"watchlist": local_watchlist}
                blob.upload_from_string(
                    json.dumps(data, indent=2),
                    content_type="application/json"
                )
                print(f"[WATCHLIST] Initialized GCS with {len(local_watchlist)} stocks")
        except Exception as e:
            print(f"[WARN] Failed to initialize GCS watchlist: {e}")
    
    def _read_local_watchlist(self) -> List[str]:
        """Read watchlist from local config.json."""
        try:
            with open(self._local_config_path, 'r') as f:
                config = json.load(f)
                return config.get("defaultWatchlist", [])
        except Exception as e:
            print(f"[WARN] Failed to read local config: {e}")
            return ["AAPL", "NVDA", "TSLA", "GOOGL", "AMZN"]  # Hardcoded fallback
    
    def _read_gcs_watchlist(self) -> List[str]:
        """Read watchlist from GCS."""
        try:
            blob = self._bucket.blob(self._watchlist_blob)
            content = blob.download_as_text()
            data = json.loads(content)
            return data.get("watchlist", [])
        except Exception as e:
            print(f"[WARN] Failed to read GCS watchlist: {e}")
            return self._read_local_watchlist()
    
    def _write_gcs_watchlist(self, watchlist: List[str]) -> bool:
        """Write watchlist to GCS."""
        try:
            blob = self._bucket.blob(self._watchlist_blob)
            data = {"watchlist": watchlist}
            blob.upload_from_string(
                json.dumps(data, indent=2),
                content_type="application/json"
            )
            return True
        except Exception as e:
            print(f"[ERROR] Failed to write GCS watchlist: {e}")
            return False
    
    def get_watchlist(self) -> List[str]:
        """Get current watchlist."""
        with self._lock:
            if self._is_writable and self._bucket:
                return self._read_gcs_watchlist()
            else:
                return self._read_local_watchlist()
    
    def add_stock(self, symbol: str) -> dict:
        """
        Add stock to watchlist.
        
        Returns:
            dict with 'success', 'message', and 'watchlist'
        """
        symbol = symbol.upper().strip()
        
        if not symbol:
            return {"success": False, "message": "Invalid symbol"}
        
        if not self._is_writable:
            return {
                "success": False, 
                "message": "Watchlist is read-only. Configure GCS_BUCKET to enable editing."
            }
        
        with self._lock:
            watchlist = self._read_gcs_watchlist()
            
            if symbol in watchlist:
                return {
                    "success": False, 
                    "message": f"{symbol} is already in watchlist",
                    "watchlist": watchlist
                }
            
            watchlist.insert(0, symbol)  # Add to beginning
            
            if self._write_gcs_watchlist(watchlist):
                return {
                    "success": True, 
                    "message": f"Added {symbol} to watchlist",
                    "watchlist": watchlist
                }
            else:
                return {
                    "success": False, 
                    "message": "Failed to save watchlist"
                }
    
    def remove_stock(self, symbol: str) -> dict:
        """
        Remove stock from watchlist.
        
        Returns:
            dict with 'success', 'message', and 'watchlist'
        """
        symbol = symbol.upper().strip()
        
        if not self._is_writable:
            return {
                "success": False, 
                "message": "Watchlist is read-only. Configure GCS_BUCKET to enable editing."
            }
        
        with self._lock:
            watchlist = self._read_gcs_watchlist()
            
            if symbol not in watchlist:
                return {
                    "success": False, 
                    "message": f"{symbol} is not in watchlist",
                    "watchlist": watchlist
                }
            
            watchlist.remove(symbol)
            
            if self._write_gcs_watchlist(watchlist):
                return {
                    "success": True, 
                    "message": f"Removed {symbol} from watchlist",
                    "watchlist": watchlist
                }
            else:
                return {
                    "success": False, 
                    "message": "Failed to save watchlist"
                }

    def clear_watchlist(self) -> dict:
        """
        Clear all stocks from watchlist.
        
        Returns:
            dict with 'success', 'message', and 'watchlist' (empty)
        """
        if not self._is_writable:
            return {
                "success": False, 
                "message": "Watchlist is read-only. Configure GCS_BUCKET to enable editing."
            }
        
        with self._lock:
            watchlist = []
            
            if self._write_gcs_watchlist(watchlist):
                return {
                    "success": True, 
                    "message": "Watchlist cleared",
                    "watchlist": watchlist
                }
            else:
                return {
                    "success": False, 
                    "message": "Failed to save watchlist"
                }
    
    @property
    def is_writable(self) -> bool:
        """Check if watchlist can be modified."""
        return self._is_writable
    
    @property
    def storage_backend(self) -> str:
        """Get current storage backend name."""
        return "gcs" if self._is_writable else "local"


# Global instance
_watchlist_storage: Optional[WatchlistStorage] = None


def get_watchlist_storage() -> WatchlistStorage:
    """Get or create the global watchlist storage instance."""
    global _watchlist_storage
    if _watchlist_storage is None:
        _watchlist_storage = WatchlistStorage()
    return _watchlist_storage

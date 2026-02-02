"""
LoRA file download and cache management.
"""
import os
import json
import urllib.request
import ssl
from typing import Optional, Dict, Tuple

import folder_paths
from .civitai_api import get_civitai_api


class LoRACacheManager:
    """Manages downloading and caching of LoRA files."""

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            # Use ComfyUI's standard loras folder
            lora_paths = folder_paths.get_folder_paths("loras")
            if lora_paths:
                cache_dir = lora_paths[0]  # Use the first/primary loras folder
            else:
                # Fallback to default location
                cache_dir = os.path.join(folder_paths.models_dir, "loras")
        self.cache_dir = cache_dir
        # Store manifest in plugin directory to track which files we downloaded
        self.manifest_file = os.path.join(os.path.dirname(__file__), "cache", "manifest.json")
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.manifest_file), exist_ok=True)

        self._manifest = self._load_manifest()
        self._download_progress: Dict[int, float] = {}

    def _load_manifest(self) -> Dict:
        """Load the manifest of downloaded LoRAs."""
        try:
            if os.path.exists(self.manifest_file):
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[SEngine] Error loading manifest: {e}")
        return {"files": {}}

    def _save_manifest(self):
        """Save the manifest to disk."""
        try:
            with open(self.manifest_file, 'w', encoding='utf-8') as f:
                json.dump(self._manifest, f, indent=2)
        except Exception as e:
            print(f"[SEngine] Error saving manifest: {e}")

    def _get_full_path(self, file_info: Dict) -> str:
        """Construct full path from manifest entry."""
        # Support both old format (local_path) and new format (file_name)
        if "local_path" in file_info:
            # Old format - check if file exists at stored path
            if os.path.exists(file_info["local_path"]):
                return file_info["local_path"]
        # New format or fallback - construct from cache_dir + filename
        filename = file_info.get("file_name", "")
        if filename:
            return os.path.join(self.cache_dir, filename)
        return ""

    def is_downloaded(self, version_id: int) -> bool:
        """Check if a LoRA version is already downloaded."""
        str_id = str(version_id)
        if str_id not in self._manifest.get("files", {}):
            return False
        file_info = self._manifest["files"][str_id]
        local_path = self._get_full_path(file_info)
        return local_path and os.path.exists(local_path)

    def get_local_path(self, version_id: int) -> Optional[str]:
        """Get the local path for a downloaded LoRA, or None if not downloaded."""
        str_id = str(version_id)
        if str_id in self._manifest.get("files", {}):
            local_path = self._get_full_path(self._manifest["files"][str_id])
            if local_path and os.path.exists(local_path):
                return local_path
        return None

    def get_download_progress(self, version_id: int) -> float:
        """Get download progress for a LoRA (0-1, or -1 if not downloading)."""
        return self._download_progress.get(version_id, -1)

    def download_lora_sync(
        self,
        version_id: int,
        file_name: str,
        api_key: str = "",
        progress_callback=None,
        download_url: str = ""
    ) -> Tuple[bool, str]:
        """
        Download a LoRA file synchronously.

        Args:
            version_id: The Civitai model version ID
            file_name: The original filename
            api_key: Civitai API key for authenticated downloads
            progress_callback: Optional callback(version_id, progress)
            download_url: Direct download URL (preferred)

        Returns:
            Tuple of (success, local_path or error_message)
        """
        # Check if already downloaded
        existing_path = self.get_local_path(version_id)
        if existing_path:
            return (True, existing_path)

        # Use provided URL or construct one
        if not download_url:
            api = get_civitai_api(api_key)
            download_url = api.get_download_url(version_id)

        # Determine local filename
        safe_filename = f"{version_id}_{file_name}"
        local_path = os.path.join(self.cache_dir, safe_filename)

        self._download_progress[version_id] = 0.0

        try:
            # Add token to URL for Civitai
            if api_key:
                separator = "&" if "?" in download_url else "?"
                download_url = f"{download_url}{separator}token={api_key}"

            print(f"[SEngine] Downloading from: {download_url[:100]}...")

            # Create request with headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json",
            }

            request = urllib.request.Request(download_url, headers=headers)

            # Create SSL context
            ssl_context = ssl.create_default_context()

            # Download
            with urllib.request.urlopen(request, context=ssl_context) as response:
                total_size = int(response.headers.get('content-length', 0))
                content_type = response.headers.get('content-type', '')
                downloaded = 0

                print(f"[SEngine] Response content-type: {content_type}")
                print(f"[SEngine] Expected size: {total_size / (1024*1024):.1f} MB")

                # Check if we got an HTML page instead of a file
                if 'text/html' in content_type.lower():
                    return (False, "Download URL returned HTML page instead of file. Check API key or URL.")

                with open(local_path, 'wb') as f:
                    while True:
                        chunk = response.read(65536)  # 64KB chunks
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = downloaded / total_size
                            self._download_progress[version_id] = progress
                            if progress_callback:
                                progress_callback(version_id, progress)

                        # Print progress periodically
                        if total_size > 0 and downloaded % (1024 * 1024) < 65536:
                            mb_done = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            print(f"[SEngine] Progress: {mb_done:.1f}/{mb_total:.1f} MB")

            # Verify download
            if os.path.exists(local_path):
                actual_size = os.path.getsize(local_path)

                if actual_size == 0:
                    os.remove(local_path)
                    return (False, "Download produced empty file")

                # Verify size matches expected if we got content-length
                if total_size > 0 and actual_size != total_size:
                    print(f"[SEngine] Size mismatch: expected {total_size}, got {actual_size}")
                    os.remove(local_path)
                    return (False, f"Download incomplete: {actual_size}/{total_size} bytes")

                print(f"[SEngine] Download verification passed ({actual_size} bytes)")

                # Update manifest - store only filename, not full path
                if "files" not in self._manifest:
                    self._manifest["files"] = {}

                self._manifest["files"][str(version_id)] = {
                    "file_name": safe_filename,  # Just the filename, not full path
                    "original_name": file_name,
                    "version_id": version_id,
                }
                self._save_manifest()

                if version_id in self._download_progress:
                    del self._download_progress[version_id]

                print(f"[SEngine] Download complete: {local_path}")
                return (True, local_path)
            else:
                return (False, "Download produced no file")

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            print(f"[SEngine] {error_msg}")
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass
            if version_id in self._download_progress:
                del self._download_progress[version_id]
            return (False, error_msg)

        except Exception as e:
            error_msg = str(e)
            print(f"[SEngine] Download error: {error_msg}")
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass
            if version_id in self._download_progress:
                del self._download_progress[version_id]
            return (False, error_msg)

    # Async version for server routes
    async def download_lora(
        self,
        version_id: int,
        file_name: str,
        api_key: str = "",
        progress_callback=None,
        download_url: str = ""
    ) -> Tuple[bool, str]:
        """Async wrapper that calls sync download in executor."""
        import asyncio
        import functools
        loop = asyncio.get_event_loop()
        func = functools.partial(
            self.download_lora_sync,
            version_id,
            file_name,
            api_key,
            progress_callback,
            download_url
        )
        return await loop.run_in_executor(None, func)

    def clear_cache(self):
        """Clear all cached LoRA files."""
        for str_id, info in list(self._manifest.get("files", {}).items()):
            local_path = self._get_full_path(info)
            if local_path and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except Exception as e:
                    print(f"[SEngine] Error removing {local_path}: {e}")

        self._manifest = {"files": {}}
        self._save_manifest()

    def get_cache_size(self) -> int:
        """Get total size of cached files in bytes."""
        total = 0
        for str_id, info in self._manifest.get("files", {}).items():
            local_path = self._get_full_path(info)
            if local_path and os.path.exists(local_path):
                total += os.path.getsize(local_path)
        return total

    def get_cached_count(self) -> int:
        """Get number of cached LoRA files."""
        count = 0
        for str_id, info in self._manifest.get("files", {}).items():
            local_path = self._get_full_path(info)
            if local_path and os.path.exists(local_path):
                count += 1
        return count


# Global instance
_cache_manager: Optional[LoRACacheManager] = None


def get_cache_manager() -> LoRACacheManager:
    """Get or create the global LoRACacheManager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = LoRACacheManager()
    return _cache_manager

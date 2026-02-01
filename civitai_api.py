"""
Civitai API wrapper for fetching SWORKS_TEAM LoRAs.
"""
import os
import json
import time
import aiohttp
import asyncio
from typing import Optional, Dict, List, Any

# Cache settings
CACHE_DURATION = 3600  # 1 hour in seconds

class CivitaiAPI:
    """Client for interacting with Civitai API."""

    BASE_URL = "https://civitai.com/api/v1"
    DOWNLOAD_URL = "https://civitai.com/api/download/models"

    def __init__(self, api_key: str = "", cache_dir: str = None):
        self.api_key = api_key
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "api_cache.json")
        os.makedirs(cache_dir, exist_ok=True)

    def set_api_key(self, api_key: str):
        """Update the API key."""
        self.api_key = api_key

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authorization if API key is set."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _load_cache(self) -> Optional[Dict]:
        """Load cached API response if valid."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                # Check if cache is still valid
                if time.time() - cache_data.get('timestamp', 0) < CACHE_DURATION:
                    return cache_data.get('data')
        except Exception as e:
            print(f"[SEngine] Error loading cache: {e}")
        return None

    def _save_cache(self, data: Any):
        """Save API response to cache."""
        try:
            cache_data = {
                'timestamp': time.time(),
                'data': data
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            print(f"[SEngine] Error saving cache: {e}")

    def _filter_klein_loras(self, models: List[Dict]) -> List[Dict]:
        """Filter models to only include those compatible with klein-9b."""
        filtered = []
        for model in models:
            # Check all versions for klein-9b compatibility
            for version in model.get('modelVersions', []):
                base_models = version.get('baseModel', '')
                # Check if any base model contains klein-9b
                if 'klein' in base_models.lower() or 'klein-9b' in base_models.lower():
                    filtered.append(model)
                    break
        return filtered

    def _extract_lora_info(self, models: List[Dict]) -> List[Dict]:
        """Extract relevant information from model data."""
        loras = []
        for model in models:
            # Get the latest/first version
            versions = model.get('modelVersions', [])
            if not versions:
                continue

            version = versions[0]  # Latest version
            files = version.get('files', [])
            images = version.get('images', [])

            # Find the safetensors file
            lora_file = None
            for f in files:
                if f.get('name', '').endswith('.safetensors'):
                    lora_file = f
                    break
            if not lora_file and files:
                lora_file = files[0]

            # Get preview image
            preview_url = None
            if images:
                preview_url = images[0].get('url', '')

            # Get tags from model
            tags = model.get('tags', [])

            lora_info = {
                'id': model.get('id'),
                'name': model.get('name', 'Unknown'),
                'description': model.get('description', ''),
                'version_id': version.get('id'),
                'version_name': version.get('name', ''),
                'base_model': version.get('baseModel', ''),
                'preview_url': preview_url,
                'preview_images': [img.get('url') for img in images if img.get('url')],
                'download_url': version.get('downloadUrl', ''),
                'file_name': lora_file.get('name', '') if lora_file else '',
                'file_size_kb': lora_file.get('sizeKB', 0) if lora_file else 0,
                'trained_words': version.get('trainedWords', []),
                'tags': tags,
            }
            loras.append(lora_info)

        return loras

    async def fetch_sworks_loras(self, force_refresh: bool = False) -> List[Dict]:
        """
        Fetch all LoRAs from SWORKS_TEAM that are compatible with klein-9b.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of LoRA information dictionaries
        """
        # Check cache first
        if not force_refresh:
            cached = self._load_cache()
            if cached is not None:
                return cached

        # Fetch from API
        url = f"{self.BASE_URL}/models"
        params = {
            "username": "SWORKS_TEAM",
            "types": "LORA",
            "limit": 100,
            "sort": "Newest",
        }

        all_models = []

        try:
            async with aiohttp.ClientSession() as session:
                # Handle pagination
                while url:
                    async with session.get(
                        url,
                        params=params if not all_models else None,  # Only use params on first request
                        headers=self._get_headers()
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            print(f"[SEngine] API error {response.status}: {error_text}")
                            break

                        data = await response.json()
                        items = data.get('items', [])
                        all_models.extend(items)

                        # Check for next page
                        metadata = data.get('metadata', {})
                        url = metadata.get('nextPage')
                        params = None  # Clear params for subsequent requests

                        # Safety limit
                        if len(all_models) > 500:
                            break

        except Exception as e:
            print(f"[SEngine] Error fetching from Civitai: {e}")
            # Return cached data if available, even if expired
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f).get('data', [])
                except:
                    pass
            return []

        # Filter for klein-9b compatible LoRAs
        klein_models = self._filter_klein_loras(all_models)

        # Extract relevant info
        loras = self._extract_lora_info(klein_models)

        # Cache the results
        self._save_cache(loras)

        return loras

    def get_download_url(self, version_id: int) -> str:
        """Get the download URL for a specific model version."""
        return f"{self.DOWNLOAD_URL}/{version_id}"

    def fetch_sworks_loras_sync(self, force_refresh: bool = False) -> List[Dict]:
        """Synchronous wrapper for fetch_sworks_loras."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.fetch_sworks_loras(force_refresh))


# Global instance
_api_instance: Optional[CivitaiAPI] = None

def get_civitai_api(api_key: str = "") -> CivitaiAPI:
    """Get or create the global CivitaiAPI instance."""
    global _api_instance
    if _api_instance is None:
        _api_instance = CivitaiAPI(api_key)
    elif api_key and api_key != _api_instance.api_key:
        _api_instance.set_api_key(api_key)
    return _api_instance

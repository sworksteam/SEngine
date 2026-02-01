"""
SEngine - ComfyUI Plugin for SWORKS_TEAM LoRAs

A dynamic LoRA browser/merger node for Civitai, specifically designed
for klein-9b and klein-9b-base models.
"""
import os
import json
import asyncio
from aiohttp import web
from server import PromptServer

from .sengine_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .civitai_api import get_civitai_api
from .lora_cache import get_cache_manager

# Export node mappings
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

# Web directory for frontend JavaScript
WEB_DIRECTORY = "./web/js"

# Plugin version
__version__ = "1.0.0"


# ============================================================================
# Server Routes
# ============================================================================

@PromptServer.instance.routes.get("/sengine/loras")
async def get_loras(request):
    """
    Get list of available SWORKS_TEAM LoRAs from Civitai.

    Query params:
        api_key: Optional Civitai API key
        refresh: Set to "true" to force refresh from API
    """
    try:
        api_key = request.rel_url.query.get("api_key", "")
        force_refresh = request.rel_url.query.get("refresh", "").lower() == "true"

        api = get_civitai_api(api_key)
        loras = await api.fetch_sworks_loras(force_refresh=force_refresh)

        return web.json_response({
            "success": True,
            "loras": loras,
            "count": len(loras)
        })

    except Exception as e:
        print(f"[SEngine] Error in get_loras: {e}")
        return web.json_response({
            "success": False,
            "error": str(e),
            "loras": []
        }, status=500)


@PromptServer.instance.routes.get("/sengine/lora/{version_id}/status")
async def get_lora_status(request):
    """
    Check if a LoRA is downloaded and get its status.

    Path params:
        version_id: The Civitai model version ID
    """
    try:
        version_id = int(request.match_info["version_id"])
        cache_manager = get_cache_manager()

        is_downloaded = cache_manager.is_downloaded(version_id)
        progress = cache_manager.get_download_progress(version_id)
        local_path = cache_manager.get_local_path(version_id) if is_downloaded else None

        return web.json_response({
            "success": True,
            "version_id": version_id,
            "is_downloaded": is_downloaded,
            "downloading": progress >= 0,
            "progress": progress if progress >= 0 else None,
            "local_path": local_path
        })

    except Exception as e:
        print(f"[SEngine] Error in get_lora_status: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


@PromptServer.instance.routes.post("/sengine/lora/{version_id}/download")
async def download_lora(request):
    """
    Trigger download of a LoRA file.

    Path params:
        version_id: The Civitai model version ID

    Body (JSON):
        api_key: Civitai API key
        file_name: Original filename
    """
    try:
        version_id = int(request.match_info["version_id"])

        # Parse request body
        body = await request.json()
        api_key = body.get("api_key", "")
        file_name = body.get("file_name", f"{version_id}.safetensors")

        cache_manager = get_cache_manager()

        # Check if already downloaded
        if cache_manager.is_downloaded(version_id):
            return web.json_response({
                "success": True,
                "already_downloaded": True,
                "local_path": cache_manager.get_local_path(version_id)
            })

        # Download the LoRA
        success, result = await cache_manager.download_lora(
            version_id, file_name, api_key
        )

        if success:
            return web.json_response({
                "success": True,
                "local_path": result
            })
        else:
            return web.json_response({
                "success": False,
                "error": result
            }, status=500)

    except Exception as e:
        print(f"[SEngine] Error in download_lora: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


@PromptServer.instance.routes.get("/sengine/cache/info")
async def get_cache_info(request):
    """Get information about the LoRA cache."""
    try:
        cache_manager = get_cache_manager()

        return web.json_response({
            "success": True,
            "cached_count": cache_manager.get_cached_count(),
            "cache_size_bytes": cache_manager.get_cache_size(),
            "cache_size_mb": round(cache_manager.get_cache_size() / (1024 * 1024), 2)
        })

    except Exception as e:
        print(f"[SEngine] Error in get_cache_info: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


@PromptServer.instance.routes.post("/sengine/cache/clear")
async def clear_cache(request):
    """Clear all cached LoRA files."""
    try:
        cache_manager = get_cache_manager()
        cache_manager.clear_cache()

        return web.json_response({
            "success": True,
            "message": "Cache cleared"
        })

    except Exception as e:
        print(f"[SEngine] Error in clear_cache: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Print startup message
print(f"[SEngine] v{__version__} loaded - SWORKS_TEAM LoRA Browser for klein-9b")

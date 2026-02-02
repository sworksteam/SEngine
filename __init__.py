"""
SEngine - ComfyUI Plugin for SWORKS_TEAM LoRAs

A dynamic LoRA browser/merger node for Civitai, specifically designed
for klein-9b and klein-9b-base models.
"""
import os
import json
import time
import asyncio
from aiohttp import web
from server import PromptServer

from .sengine_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .civitai_api import get_civitai_api
from .lora_cache import get_cache_manager
from .civitai_upload import CivitaiUploader, create_img2img_composite

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


@PromptServer.instance.routes.post("/sengine/upload")
async def upload_to_civitai(request):
    """
    Upload an image to Civitai and create a post.

    Body (JSON):
        image_path: Path to the image file (or filename for output images)
        image_subfolder: Subfolder in output directory
        image_type: Type (output, input, temp)
        session_cookie: Civitai session cookie
        lora_version_ids: List of LoRA version IDs to tag
        prompt: Generation prompt
        negative_prompt: Negative prompt
        cfg_scale: CFG scale
        steps: Number of steps
        sampler: Sampler name
        seed: Generation seed
        title: Post title (optional)
    """
    try:
        import functools
        from pathlib import Path
        import folder_paths

        body = await request.json()

        image_filename = body.get("image_path")
        image_subfolder = body.get("image_subfolder", "")
        image_type = body.get("image_type", "output")
        session_cookie = body.get("session_cookie", "")

        # Construct the full image path
        if image_type == "output":
            base_dir = folder_paths.get_output_directory()
        elif image_type == "input":
            base_dir = folder_paths.get_input_directory()
        elif image_type == "temp":
            base_dir = folder_paths.get_temp_directory()
        else:
            base_dir = folder_paths.get_output_directory()

        if not image_filename:
            return web.json_response({
                "success": False,
                "error": "image_path (filename) is required"
            }, status=400)

        if image_subfolder:
            image_path = os.path.join(base_dir, image_subfolder, image_filename)
        else:
            image_path = os.path.join(base_dir, image_filename)

        if not session_cookie:
            return web.json_response({
                "success": False,
                "error": "session_cookie is required"
            }, status=400)

        if not os.path.exists(image_path):
            return web.json_response({
                "success": False,
                "error": f"Image not found: {image_path}"
            }, status=400)

        # Get optional parameters
        lora_version_ids = body.get("lora_version_ids", [])
        prompt = body.get("prompt")
        negative_prompt = body.get("negative_prompt")
        cfg_scale = body.get("cfg_scale")
        steps = body.get("steps")
        sampler = body.get("sampler")
        seed = body.get("seed")
        title = body.get("title")
        model_name = body.get("model_name")
        sengine_config = body.get("sengine_config")
        source_images = body.get("source_images", [])
        use_composite = body.get("use_composite", False)

        # Run upload in executor to not block
        loop = asyncio.get_event_loop()

        # Resolve source image paths (they're in the input directory)
        source_image_paths = []
        if source_images and use_composite:
            input_dir = folder_paths.get_input_directory()
            for src_filename in source_images:
                src_path = os.path.join(input_dir, src_filename)
                if os.path.exists(src_path):
                    source_image_paths.append(Path(src_path))

        def do_upload():
            upload_image_path = Path(image_path)
            composite_path = None

            # If user chose composite and we have source images, create it
            if use_composite and source_image_paths:
                import tempfile
                composite_path = Path(tempfile.gettempdir()) / f"sengine_composite_{int(time.time())}.png"
                if create_img2img_composite(source_image_paths, Path(image_path), composite_path):
                    print(f"[SEngine] Created img2img composite: {composite_path}")
                    upload_image_path = composite_path
                else:
                    print("[SEngine] Failed to create composite, uploading original")

            try:
                uploader = CivitaiUploader(session_cookie)
                result = uploader.create_post_with_image(
                    image_path=upload_image_path,
                    lora_version_ids=lora_version_ids,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    cfg_scale=cfg_scale,
                    steps=steps,
                    sampler=sampler,
                    seed=seed,
                    title=title,
                    model_name=model_name,
                    sengine_config=sengine_config,
                    publish=True,
                )
                return result
            finally:
                # Clean up composite file
                if composite_path and composite_path.exists():
                    try:
                        composite_path.unlink()
                    except:
                        pass

        post_id = await loop.run_in_executor(None, do_upload)

        if post_id:
            return web.json_response({
                "success": True,
                "post_id": post_id,
                "post_url": f"https://civitai.com/posts/{post_id}"
            })
        else:
            return web.json_response({
                "success": False,
                "error": "Upload failed"
            }, status=500)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[SEngine] Error in upload_to_civitai: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


@PromptServer.instance.routes.post("/sengine/preview-composite")
async def preview_composite(request):
    """
    Create a composite preview image for img2img workflows.
    Returns the composite as a base64 encoded image.
    """
    try:
        import base64
        import tempfile
        import folder_paths
        from pathlib import Path

        body = await request.json()

        image_filename = body.get("image_path")
        image_subfolder = body.get("image_subfolder", "")
        image_type = body.get("image_type", "output")
        source_images = body.get("source_images", [])

        if not source_images:
            return web.json_response({
                "success": False,
                "error": "No source images provided"
            }, status=400)

        # Get generated image path
        if image_type == "output":
            base_dir = folder_paths.get_output_directory()
        elif image_type == "input":
            base_dir = folder_paths.get_input_directory()
        elif image_type == "temp":
            base_dir = folder_paths.get_temp_directory()
        else:
            base_dir = folder_paths.get_output_directory()

        if image_subfolder:
            image_path = os.path.join(base_dir, image_subfolder, image_filename)
        else:
            image_path = os.path.join(base_dir, image_filename)

        if not os.path.exists(image_path):
            return web.json_response({
                "success": False,
                "error": f"Generated image not found: {image_path}"
            }, status=400)

        # Resolve source image paths
        input_dir = folder_paths.get_input_directory()
        source_image_paths = []
        for src_filename in source_images:
            src_path = os.path.join(input_dir, src_filename)
            if os.path.exists(src_path):
                source_image_paths.append(Path(src_path))

        if not source_image_paths:
            return web.json_response({
                "success": False,
                "error": "No valid source images found"
            }, status=400)

        # Create composite
        composite_path = Path(tempfile.gettempdir()) / f"sengine_preview_{int(time.time())}.jpg"

        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            create_img2img_composite,
            source_image_paths,
            Path(image_path),
            composite_path
        )

        if not success or not composite_path.exists():
            return web.json_response({
                "success": False,
                "error": "Failed to create composite"
            }, status=500)

        # Read and encode as base64
        with open(composite_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Clean up
        try:
            composite_path.unlink()
        except:
            pass

        return web.json_response({
            "success": True,
            "composite_base64": f"data:image/jpeg;base64,{image_data}"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[SEngine] Error in preview_composite: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


# Print startup message
print(f"[SEngine] v{__version__} loaded - SWORKS_TEAM LoRA Browser for klein-9b")

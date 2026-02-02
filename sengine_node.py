"""
SEngine LoRA Loader Node
"""
import json

import comfy.sd
import comfy.utils
from server import PromptServer

from .lora_cache import get_cache_manager


def send_progress(version_id, progress, status="downloading", name=""):
    """Send download progress to frontend via websocket."""
    try:
        PromptServer.instance.send_sync("sengine_progress", {
            "version_id": version_id,
            "progress": progress,
            "status": status,  # "downloading", "complete", "failed"
            "name": name
        })
    except:
        pass


# Module-level cache for loaded LoRA weights (persists across node instances)
_lora_cache = {}


def clear_lora_cache():
    """Clear the LoRA weight cache to free memory."""
    global _lora_cache
    count = len(_lora_cache)
    _lora_cache.clear()
    print(f"[SEngine] Cleared {count} LoRA(s) from cache")
    return count


def get_lora_cache_info():
    """Get info about cached LoRAs."""
    global _lora_cache
    return {
        "count": len(_lora_cache),
        "paths": list(_lora_cache.keys())
    }


class SEngineLoraLoader:
    """
    Dynamic LoRA loader controlled via SEngine sidebar.
    """

    def __init__(self):
        pass  # Use module-level cache instead of instance cache

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "overall_strength": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                    "display": "slider",
                }),
                "sengine_data": ("STRING", {
                    "default": "{}",
                    "multiline": True,
                }),
            },
            "optional": {
                "clip": ("CLIP",),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("MODEL", "CLIP")
    FUNCTION = "apply_loras"
    CATEGORY = "loaders"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def apply_loras(self, model, overall_strength=1.0, clip=None, sengine_data="{}"):
        """Apply selected LoRAs to the model and optionally clip."""

        print(f"[SEngine] Received sengine_data: {sengine_data[:200] if sengine_data else 'None'}...")
        print(f"[SEngine] Overall strength: {overall_strength}")

        # Parse data
        try:
            if isinstance(sengine_data, str) and sengine_data.strip():
                data = json.loads(sengine_data)
            else:
                data = {}
        except (json.JSONDecodeError, TypeError) as e:
            print(f"[SEngine] JSON parse error: {e}")
            return (model, clip)

        if not isinstance(data, dict):
            print(f"[SEngine] Data is not a dict: {type(data)}")
            return (model, clip)

        lora_list = data.get("loras", [])
        api_key = data.get("api_key", "")

        if not isinstance(lora_list, list):
            print(f"[SEngine] loras is not a list: {type(lora_list)}")
            return (model, clip)

        if not lora_list:
            print("[SEngine] No LoRAs to apply")
            return (model, clip)

        print(f"[SEngine] Applying {len(lora_list)} LoRA(s)")

        cache_manager = get_cache_manager()
        current_model = model
        current_clip = clip

        for i, lora_info in enumerate(lora_list):
            if not isinstance(lora_info, dict):
                print(f"[SEngine] Invalid lora entry {i}")
                continue

            version_id = lora_info.get("version_id")
            strength = float(lora_info.get("strength", 1.0))
            strength_clip = float(lora_info.get("strength_clip", strength))
            file_name = lora_info.get("file_name", f"{version_id}.safetensors")
            name = lora_info.get("name", "Unknown")
            download_url = lora_info.get("download_url", "")

            if not version_id:
                continue

            # Apply overall strength multiplier
            strength = strength * overall_strength
            strength_clip = strength_clip * overall_strength

            if strength == 0 and strength_clip == 0:
                print(f"[SEngine] Skipping {name} (effective strength=0)")
                continue

            # Get local path or download
            local_path = cache_manager.get_local_path(version_id)
            if not local_path:
                print(f"[SEngine] Downloading: {name} (version {version_id})")
                send_progress(version_id, 0, "downloading", name)

                # Throttle progress updates - only send every 5%
                last_reported = [0]
                def progress_cb(vid, prog):
                    if prog - last_reported[0] >= 0.05 or prog >= 1.0:
                        last_reported[0] = prog
                        send_progress(vid, prog, "downloading", name)

                success, result = cache_manager.download_lora_sync(
                    version_id, file_name, api_key,
                    progress_callback=progress_cb,
                    download_url=download_url
                )
                if not success:
                    print(f"[SEngine] Download failed: {result}")
                    send_progress(version_id, 0, "failed", name)
                    continue
                local_path = result
                send_progress(version_id, 1, "complete", name)
                print(f"[SEngine] Downloaded to: {local_path}")

            # Load and apply
            try:
                global _lora_cache
                if local_path not in _lora_cache:
                    print(f"[SEngine] Loading from disk: {local_path}")
                    try:
                        _lora_cache[local_path] = comfy.utils.load_torch_file(local_path, safe_load=True)
                    except Exception as load_error:
                        # Check if it's a corrupted file error
                        error_str = str(load_error)
                        if "incomplete metadata" in error_str or "not fully covered" in error_str or "SafetensorError" in str(type(load_error)):
                            print(f"[SEngine] Corrupted file detected, deleting: {local_path}")
                            import os
                            try:
                                os.remove(local_path)
                                # Remove from manifest so it can be re-downloaded
                                cache_manager._manifest.get("files", {}).pop(str(version_id), None)
                                cache_manager._save_manifest()
                                print(f"[SEngine] Deleted corrupted file. Re-run workflow to re-download {name}")
                            except Exception as del_error:
                                print(f"[SEngine] Error deleting corrupted file: {del_error}")
                        raise
                else:
                    print(f"[SEngine] Using cached: {name}")

                current_model, current_clip = comfy.sd.load_lora_for_models(
                    current_model,
                    current_clip,
                    _lora_cache[local_path],
                    strength,
                    strength_clip
                )
                print(f"[SEngine] Applied: {name} (M:{strength:.2f} C:{strength_clip:.2f})")

            except Exception as e:
                print(f"[SEngine] Error applying {name}: {e}")
                import traceback
                traceback.print_exc()

        return (current_model, current_clip)


NODE_CLASS_MAPPINGS = {
    "SEngineLoraLoader": SEngineLoraLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SEngineLoraLoader": "SEngine LoRA Loader",
}

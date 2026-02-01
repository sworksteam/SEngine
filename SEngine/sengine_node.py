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


class SEngineLoraLoader:
    """
    Dynamic LoRA loader controlled via SEngine sidebar.
    """

    def __init__(self):
        self.loaded_loras = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
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

    def apply_loras(self, model, clip=None, sengine_data="{}"):
        """Apply selected LoRAs to the model and optionally clip."""

        print(f"[SEngine] Received sengine_data: {sengine_data[:200] if sengine_data else 'None'}...")

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

            if strength == 0 and strength_clip == 0:
                print(f"[SEngine] Skipping {name} (strength=0)")
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
                if local_path not in self.loaded_loras:
                    print(f"[SEngine] Loading from disk: {local_path}")
                    self.loaded_loras[local_path] = comfy.utils.load_torch_file(local_path, safe_load=True)

                current_model, current_clip = comfy.sd.load_lora_for_models(
                    current_model,
                    current_clip,
                    self.loaded_loras[local_path],
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

"""
Civitai image upload and post creation.
"""
import os
import json
import time
import mimetypes
import requests
from pathlib import Path
from typing import Optional, Dict, List, Any
from PIL import Image
import blurhash
import numpy as np


BASE_URL = "https://civitai.com"
IMAGE_UPLOAD_URL = f"{BASE_URL}/api/v1/image-upload/multipart"
IMAGE_COMPLETE_URL = f"{BASE_URL}/api/upload/complete"
TRPC_URL = f"{BASE_URL}/api/trpc"
CHUNK_SIZE = 100 * 1024 * 1024  # 100MB


def create_img2img_composite(source_paths: List[Path], generated_path: Path, output_path: Path) -> bool:
    """
    Create a composite image showing source images -> generated image.
    Arranges source images vertically on the left, arrow in middle, generated on right.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Load generated image
        generated = Image.open(generated_path)
        gen_width, gen_height = generated.size

        # Load and resize source images to match generated height
        source_images = []
        for sp in source_paths:
            if Path(sp).exists():
                src = Image.open(sp)
                source_images.append(src)

        if not source_images:
            return False

        # Calculate layout
        # Stack source images vertically, scale to fit generated image height
        total_source_height = sum(img.height for img in source_images)
        scale_factor = gen_height / total_source_height if total_source_height > 0 else 1

        scaled_sources = []
        max_source_width = 0
        for src in source_images:
            new_height = int(src.height * scale_factor)
            new_width = int(src.width * scale_factor)
            scaled = src.resize((new_width, new_height), Image.Resampling.LANCZOS)
            scaled_sources.append(scaled)
            max_source_width = max(max_source_width, new_width)

        # Arrow space
        arrow_width = 60

        # Create composite canvas
        total_width = max_source_width + arrow_width + gen_width
        composite = Image.new("RGB", (total_width, gen_height), (18, 18, 18))

        # Paste source images (stacked vertically, centered horizontally)
        y_offset = 0
        for scaled in scaled_sources:
            x_offset = (max_source_width - scaled.width) // 2
            composite.paste(scaled, (x_offset, y_offset))
            y_offset += scaled.height

        # Draw arrow
        draw = ImageDraw.Draw(composite)
        arrow_x = max_source_width + arrow_width // 2
        arrow_y = gen_height // 2
        arrow_color = (120, 120, 120)

        # Arrow line
        draw.line([(arrow_x - 15, arrow_y), (arrow_x + 15, arrow_y)], fill=arrow_color, width=3)
        # Arrow head
        draw.polygon([
            (arrow_x + 15, arrow_y),
            (arrow_x + 5, arrow_y - 8),
            (arrow_x + 5, arrow_y + 8)
        ], fill=arrow_color)

        # Paste generated image
        composite.paste(generated, (max_source_width + arrow_width, 0))

        # Save composite
        composite.save(output_path, quality=95)

        # Clean up
        generated.close()
        for src in source_images:
            src.close()
        for scaled in scaled_sources:
            scaled.close()

        return True

    except Exception as e:
        print(f"[SEngine] Error creating composite: {e}")
        return False


class CivitaiUploader:
    """Handles uploading images and creating posts on Civitai."""

    def __init__(self, session_cookie: str):
        self.session_cookie = session_cookie
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a session with auth cookies and headers."""
        session = requests.Session()

        # Handle cookie format - extract just the token if full cookie string provided
        cookie = self.session_cookie.strip()
        if not cookie.startswith("__Secure-civitai-token="):
            cookie = f"__Secure-civitai-token={cookie}"

        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/posts/create",
            "Content-Type": "application/json",
            "Cookie": cookie,
            "x-client": "web",
            "x-client-version": "5.0.1395",
            "x-client-date": str(int(time.time() * 1000)),
        })
        return session

    def _get_image_info(self, file_path: Path) -> dict:
        """Get image dimensions, size, mime type, and blurhash."""
        file_path = Path(file_path)
        file_size = file_path.stat().st_size

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "image/png"

        with Image.open(file_path) as img:
            width, height = img.size
            # Generate proper blurhash (resize for performance)
            thumb = img.copy()
            thumb.thumbnail((100, 100))
            if thumb.mode != "RGB":
                thumb = thumb.convert("RGB")
            hash_str = blurhash.encode(np.array(thumb), components_x=4, components_y=4)

        return {
            "size": file_size,
            "width": width,
            "height": height,
            "mimeType": mime_type,
            "hash": hash_str,
        }

    def upload_image(self, file_path: Path) -> Optional[dict]:
        """Upload an image to Civitai's storage."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        info = self._get_image_info(file_path)
        filename = file_path.name

        print(f"[SEngine] Uploading: {filename} ({info['size']} bytes)")

        # Step 1: Initiate multipart upload
        init_response = self.session.post(IMAGE_UPLOAD_URL, json={
            "filename": filename,
            "type": "image",
            "size": info["size"],
            "mimeType": info["mimeType"],
        })

        if init_response.status_code != 200:
            print(f"[SEngine] Upload init failed: {init_response.status_code}")
            return None

        init_data = init_response.json()
        urls = init_data.get("urls", [])
        bucket = init_data.get("bucket")
        key = init_data.get("key")
        upload_id = init_data.get("uploadId")

        # Step 2: Upload file chunks
        parts = []
        with open(file_path, "rb") as f:
            for i, url_info in enumerate(urls):
                part_number = i + 1
                url = url_info.get("url") if isinstance(url_info, dict) else url_info
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break

                put_response = requests.put(url, data=chunk, headers={
                    "Content-Type": "application/octet-stream",
                })
                if put_response.status_code not in (200, 204):
                    print(f"[SEngine] Upload part {part_number} failed")
                    return None

                etag = put_response.headers.get("ETag", "").strip('"')
                parts.append({"ETag": f'"{etag}"', "PartNumber": part_number})

        # Step 3: Complete multipart upload
        complete_response = self.session.post(IMAGE_COMPLETE_URL, json={
            "bucket": bucket,
            "key": key,
            "type": "image",
            "uploadId": upload_id,
            "parts": parts,
        })

        if complete_response.status_code != 200:
            print(f"[SEngine] Upload complete failed: {complete_response.status_code}")
            return None

        print(f"[SEngine] Upload complete: {key}")
        return {
            "url": key,
            "name": filename,
            **info,
        }

    def create_post(self, model_version_id: int = None) -> Optional[dict]:
        """Create a new post on Civitai."""
        payload = {
            "json": {
                "modelVersionId": model_version_id,
                "tag": None,
                "collectionId": None,
                "authed": True,
            },
            "meta": {
                "values": {
                    "modelVersionId": ["undefined"],
                    "tag": ["undefined"],
                    "collectionId": ["undefined"],
                }
            }
        }

        response = self.session.post(f"{TRPC_URL}/post.create", json=payload)
        if response.status_code != 200:
            print(f"[SEngine] Create post failed: {response.status_code}")
            return None

        result = response.json()
        if "result" in result:
            data = result.get("result", {}).get("data", {})
            return data.get("json", data)
        return result

    def add_image_to_post(self, post_id: int, image_data: dict, index: int = 0, model_version_id: int = None) -> Optional[dict]:
        """Add an uploaded image to a post."""
        payload = {
            "json": {
                "name": image_data["name"],
                "url": image_data["url"],
                "hash": image_data.get("hash", ""),
                "height": image_data["height"],
                "width": image_data["width"],
                "postId": post_id,
                "modelVersionId": model_version_id,
                "index": index,
                "mimeType": image_data["mimeType"],
                "meta": None,
                "nsfwLevel": "None",
                "type": "image",
                "metadata": {
                    "size": image_data["size"],
                    "width": image_data["width"],
                    "height": image_data["height"],
                    "hash": image_data.get("hash", ""),
                },
                "externalDetailsUrl": None,
                "authed": True,
            },
            "meta": {
                "values": {
                    "meta": ["undefined"],
                    "externalDetailsUrl": ["undefined"],
                }
            }
        }

        # Mark modelVersionId as undefined if not provided
        if model_version_id is None:
            payload["meta"]["values"]["modelVersionId"] = ["undefined"]

        response = self.session.post(f"{TRPC_URL}/post.addImage", json=payload)
        if response.status_code != 200:
            print(f"[SEngine] Add image failed: {response.status_code}")
            return None

        result = response.json()
        if "result" in result:
            data = result.get("result", {}).get("data", {})
            return data.get("json", data)
        return result

    def add_resource_to_image(self, image_ids: List[int], model_version_id: int) -> Optional[dict]:
        """Add a resource (LoRA) to images."""
        payload = {
            "json": {
                "id": image_ids,
                "modelVersionId": model_version_id,
                "authed": True,
            }
        }

        response = self.session.post(f"{TRPC_URL}/post.addResourceToImage", json=payload)
        if response.status_code != 200:
            print(f"[SEngine] Add resource failed: {response.status_code}")
            return None

        return response.json()

    def update_image_meta(
        self,
        image_id: int,
        prompt: str = None,
        negative_prompt: str = None,
        cfg_scale: float = None,
        steps: int = None,
        sampler: str = None,
        seed: int = None,
    ) -> Optional[dict]:
        """Update image generation metadata."""
        meta = {}
        if prompt is not None:
            meta["prompt"] = prompt
        if negative_prompt is not None:
            meta["negativePrompt"] = negative_prompt
        if cfg_scale is not None:
            meta["cfgScale"] = cfg_scale
        if steps is not None:
            meta["steps"] = steps
        if sampler is not None:
            meta["sampler"] = sampler
        if seed is not None:
            meta["seed"] = seed

        if not meta:
            return None

        payload = {
            "json": {
                "id": image_id,
                "meta": meta,
                "authed": True,
            }
        }

        response = self.session.post(f"{TRPC_URL}/post.updateImage", json=payload)
        if response.status_code != 200:
            print(f"[SEngine] Update meta failed: {response.status_code}")
            return None

        return response.json()

    def refresh_image_resources(self, image_id: int) -> Optional[dict]:
        """Refresh resources for an image."""
        payload = {
            "json": {
                "id": image_id,
                "authed": True,
            }
        }

        response = self.session.post(f"{TRPC_URL}/image.refreshImageResources", json=payload)
        return response.json() if response.status_code == 200 else None

    def add_tool_to_image(self, image_id: int, tool_id: int, notes: str = None) -> Optional[dict]:
        """Add a tool (e.g., Flux) to an image with optional notes."""
        print(f"[SEngine] Adding tool {tool_id} to image {image_id}...")

        # First add the tool
        add_payload = {
            "json": {
                "data": [{"imageId": image_id, "toolId": tool_id}],
                "authed": True,
            }
        }

        response = self.session.post(f"{TRPC_URL}/image.addTools", json=add_payload)
        if response.status_code != 200:
            print(f"[SEngine] Add tool failed: {response.status_code}")
            return None

        # If notes provided, update the tool with notes
        if notes:
            update_payload = {
                "json": {
                    "data": [{"imageId": image_id, "toolId": tool_id, "notes": notes}],
                    "authed": True,
                }
            }

            response = self.session.post(f"{TRPC_URL}/image.updateTools", json=update_payload)
            if response.status_code != 200:
                print(f"[SEngine] Update tool notes failed: {response.status_code}")
                return None

        print(f"[SEngine] Added tool with notes: {notes}")
        return response.json()

    def publish_post(self, post_id: int, title: str = None) -> Optional[dict]:
        """Publish a post."""
        from datetime import datetime, timezone

        published_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

        payload = {
            "json": {
                "id": post_id,
                "title": title,
                "publishedAt": published_at,
                "collectionId": None,
                "collectionTagId": None,
                "authed": True,
            },
            "meta": {
                "values": {
                    "title": ["undefined"],
                    "publishedAt": ["Date"],
                    "collectionId": ["undefined"],
                }
            }
        }

        if title is not None:
            del payload["meta"]["values"]["title"]

        response = self.session.post(f"{TRPC_URL}/post.update", json=payload)
        if response.status_code != 200:
            print(f"[SEngine] Publish failed: {response.status_code}")
            return None

        return response.json()

    # Tool IDs
    FLUX_TOOL_ID = 199
    COMFYUI_TOOL_ID = 86

    def create_post_with_image(
        self,
        image_path: Path,
        lora_version_ids: List[int] = None,
        prompt: str = None,
        negative_prompt: str = None,
        cfg_scale: float = None,
        steps: int = None,
        sampler: str = None,
        seed: int = None,
        title: str = None,
        model_name: str = None,
        sengine_config: dict = None,
        publish: bool = True,
    ) -> Optional[int]:
        """Full workflow: upload image, create post, add metadata and resources, publish."""

        # Step 1: Upload image
        print("[SEngine] Uploading image to Civitai...")
        image_data = self.upload_image(image_path)
        if not image_data:
            return None

        time.sleep(1)

        # Step 2: Create post
        print("[SEngine] Creating post...")
        post = self.create_post()
        if not post:
            return None

        post_id = post.get("id")
        time.sleep(1)

        # Step 3: Add image to post (use first LoRA as primary model association)
        print("[SEngine] Adding image to post...")
        primary_model_id = lora_version_ids[0] if lora_version_ids else None
        image = self.add_image_to_post(post_id, image_data, model_version_id=primary_model_id)
        if not image:
            return None

        image_id = image.get("id")
        time.sleep(2)

        # Step 4: Update metadata
        if any(x is not None for x in [prompt, negative_prompt, cfg_scale, steps, sampler, seed]):
            print("[SEngine] Updating metadata...")
            self.update_image_meta(
                image_id,
                prompt=prompt,
                negative_prompt=negative_prompt,
                cfg_scale=cfg_scale,
                steps=steps,
                sampler=sampler,
                seed=seed,
            )
            time.sleep(1)

        # Step 5: Add LoRA resources
        if lora_version_ids:
            print(f"[SEngine] Adding {len(lora_version_ids)} LoRA resource(s)...")
            for version_id in lora_version_ids:
                self.add_resource_to_image([image_id], version_id)
                time.sleep(0.5)
            self.refresh_image_resources(image_id)

        # Step 6: Add Flux tool with model name
        if model_name:
            print(f"[SEngine] Adding Flux tool with model: {model_name}")
            self.add_tool_to_image(image_id, self.FLUX_TOOL_ID, notes=model_name)
            time.sleep(0.5)

        # Step 7: Add ComfyUI tool with SEngine configuration
        if sengine_config:
            notes_lines = ["SEngine Configuration:"]
            overall = sengine_config.get("overall_strength", 1.0)
            notes_lines.append(f"overall_strength: {overall}")
            for lora in sengine_config.get("loras", []):
                if lora["strength"] > 0:
                    notes_lines.append(f"{lora['name']}: {lora['strength']}")
            comfyui_notes = "\n".join(notes_lines)
            print(f"[SEngine] Adding ComfyUI tool with config")
            self.add_tool_to_image(image_id, self.COMFYUI_TOOL_ID, notes=comfyui_notes)
            time.sleep(0.5)

        # Step 8: Publish
        if publish:
            print("[SEngine] Publishing post...")
            self.publish_post(post_id, title=title)

        print(f"[SEngine] Done! Post URL: https://civitai.com/posts/{post_id}")
        return post_id

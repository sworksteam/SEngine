# SEngine - SWORKS_TEAM LoRA Browser for ComfyUI

A ComfyUI plugin that provides a sidebar interface for browsing, downloading, and applying SWORKS_TEAM LoRAs from Civitai. Current implementation uses **klein-9b** and **klein-9b-base** models.

![SEngine Sidebar](https://img.shields.io/badge/ComfyUI-Custom_Node-blue)

## Features

- **Sidebar Browser** - Browse all SWORKS_TEAM LoRAs with image previews
- **Tag Filtering** - Filter LoRAs by tags using a multi-select dropdown
- **Search** - Search by name, trained words, or tags
- **Auto-Download** - LoRAs are automatically downloaded on first use
- **Dynamic Node** - Strength sliders appear on the node for each selected LoRA
- **Overall Strength** - Master strength slider (0.0 - 1.0) to control all LoRAs at once
- **Reorder LoRAs** - Change the order LoRAs are applied using up/down buttons
- **Standard Storage** - Downloads go to ComfyUI's `models/loras/` folder
- **Civitai Upload** - One-click upload generated images to Civitai with:
  - Auto-extracted metadata (prompt, seed, sampler, CFG, steps)
  - Automatic LoRA resource tagging
  - Flux tool tagging with model name
  - ComfyUI tool tagging with SEngine configuration
  - Image-to-image composite support (shows source + generated images)

## Installation

### Option 1: Git Clone (Recommended)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/SWORKS_TEAM/SEngine.git
pip install -r SEngine/requirements.txt
```

### Option 2: Manual Download

1. Download the repository as a ZIP file
2. Extract to `ComfyUI/custom_nodes/SEngine`
3. Install requirements: `pip install -r requirements.txt`

### Option 3: ComfyUI Manager

Search for "SEngine" in ComfyUI Manager and click Install.

---

After installation, restart ComfyUI.

## Requirements

- ComfyUI (recent version with sidebar support)
- Python packages (install via `pip install -r requirements.txt`):
  - `Pillow` (usually included with ComfyUI)
  - `blurhash` (for image upload)
  - `numpy` (usually included with ComfyUI)
  - `requests` (for Civitai upload)

## Usage

### 1. Open the Sidebar

Click the **bolt icon** in ComfyUI's sidebar to open the SEngine panel.

### 2. Enter API Key

Enter your [Civitai API key](https://civitai.com/user/account) in the API Key field. This enables:
- Faster downloads
- Access to any restricted models

The API key is saved locally in your browser.

### 3. Browse and Select LoRAs

- LoRAs load automatically on startup
- Click the **refresh** button to update the list
- Use the **tag dropdown** to filter by category
- Use the **search box** to find specific LoRAs
- **Click a LoRA** to select/deselect it

### 4. Connect the Node

When you select your first LoRA, an **SEngine LoRA Loader** node is automatically created.

Connect it to your workflow:

```
[Load Diffusion Model] → MODEL → [SEngine LoRA Loader] → MODEL → [BasicGuider]
```

### 5. Adjust Strengths

- **Overall Strength** slider (0.0 - 1.0) controls the master effect of all LoRAs
- Each selected LoRA gets a **strength slider** on the node (0.0 - 2.0)
- Adjust in the sidebar or directly on the node
- Use **up/down buttons** in the sidebar to reorder LoRAs
- LoRAs set to 0.0 strength are effectively disabled

### 6. Run Your Workflow

- LoRAs are downloaded automatically if not already cached
- Download progress is shown in the sidebar
- Downloaded LoRAs are stored in `ComfyUI/models/loras/`

### 7. Upload to Civitai (Optional)

Share your generated images directly to Civitai:

1. **Get your session cookie** from Civitai:
   - Log into Civitai in your browser
   - Open DevTools (F12) → Application → Cookies
   - Copy the value of `__Secure-civitai-token`

2. **Paste the cookie** in the "Civitai session cookie" field at the bottom of the sidebar

3. **Generate an image** - the upload button will activate

4. **Click "Upload Last Image"** - this will:
   - Upload the image to Civitai
   - Create a post with auto-extracted metadata (prompt, seed, sampler, CFG, steps)
   - Tag the post with all LoRAs used in SEngine
   - Add Flux tool tag with the model name (from Load Diffusion Model node)
   - Add ComfyUI tool tag with SEngine configuration (overall strength + LoRA strengths)
   - Auto-publish the post

#### Image-to-Image Workflows

If your workflow includes **Load Image** nodes, SEngine will detect this as an image-to-image workflow and show a preview modal with options:

- **Upload Composite** - Creates a combined image showing source images → generated image
- **Upload Original Only** - Uploads just the generated image
- **Cancel** - Cancels the upload

The composite image displays source images stacked on the left with an arrow pointing to the generated image on the right.

## Node Inputs/Outputs

| Input | Type | Description |
|-------|------|-------------|
| model | MODEL | Base model to apply LoRAs to |
| clip | CLIP | (Optional) CLIP model for text encoder LoRA weights |

| Output | Type | Description |
|--------|------|-------------|
| MODEL | MODEL | Model with LoRAs applied |
| CLIP | CLIP | CLIP with LoRAs applied |

## Node Widgets

| Widget | Range | Description |
|--------|-------|-------------|
| overall_strength | 0.0 - 1.0 | Master strength multiplier for all LoRAs |
| [LoRA Name] | 0.0 - 2.0 | Individual strength for each selected LoRA |

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| Downloaded LoRAs | `ComfyUI/models/loras/` | Standard ComfyUI loras folder |
| API Cache | `SEngine/cache/api_cache.json` | Cached LoRA list (1 hour) |
| Download Manifest | `SEngine/cache/manifest.json` | Tracks downloaded files |

## Troubleshooting

### LoRAs not loading
- Check the ComfyUI console for error messages
- Ensure your API key is correct
- Try clicking the refresh button

### Sidebar not appearing
- Make sure you're using a recent version of ComfyUI with sidebar support
- Check browser console (F12) for JavaScript errors

### Downloads failing
- Verify your Civitai API key is valid
- Check your internet connection
- Some models may require authentication

### Upload failing
- Verify your session cookie is valid (they expire periodically)
- Re-copy the `__Secure-civitai-token` cookie from Civitai
- Check the ComfyUI console for error messages

### Image-to-image not detected
- Ensure you're using a standard "LoadImage" node
- Check browser console (F12) for debug messages showing detected node types

## License

MIT License

## Credits

- **SWORKS_TEAM** - LoRA creators
- Built for the ComfyUI community

# SEngine - SWORKS_TEAM LoRA Browser for ComfyUI

A ComfyUI plugin that provides a sidebar interface for browsing, downloading, and applying SWORKS_TEAM LoRAs from Civitai. Current implementation uses **klein-9b** and **klein-9b-base** models.

![SEngine Sidebar](https://img.shields.io/badge/ComfyUI-Custom_Node-blue)

## Features

- **Sidebar Browser** - Browse all SWORKS_TEAM LoRAs with image previews
- **Tag Filtering** - Filter LoRAs by tags using a multi-select dropdown
- **Search** - Search by name, trained words, or tags
- **Auto-Download** - LoRAs are automatically downloaded on first use
- **Dynamic Node** - Strength sliders appear on the node for each selected LoRA
- **Reorder LoRAs** - Change the order LoRAs are applied using up/down buttons
- **Standard Storage** - Downloads go to ComfyUI's `models/loras/` folder

## Installation

### Option 1: Git Clone (Recommended)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/SWORKS_TEAM/SEngine.git
```

### Option 2: Manual Download

1. Download the repository as a ZIP file
2. Extract to `ComfyUI/custom_nodes/SEngine`

### Option 3: ComfyUI Manager (pull request created, PENDING)

Search for "SEngine" in ComfyUI Manager and click Install.

---

After installation, restart ComfyUI.

## Requirements

- ComfyUI (recent version with sidebar support)
- Python packages: `aiohttp` (usually included with ComfyUI)

## Usage

### 1. Open the Sidebar

Click the **⚡ bolt icon** in ComfyUI's sidebar to open the SEngine panel.

### 2. Enter API Key

Enter your [Civitai API key](https://civitai.com/user/account) in the API Key field. This enables:
- Faster downloads
- Access to any restricted models

The API key is saved locally in your browser.

### 3. Browse and Select LoRAs

- LoRAs load automatically on startup
- Click the **↻ refresh** button to update the list
- Use the **tag dropdown** to filter by category
- Use the **search box** to find specific LoRAs
- **Click a LoRA** to select/deselect it

### 4. Connect the Node

When you select your first LoRA, an **SEngine LoRA Loader** node is automatically created.

Connect it to your workflow:

```
[Load Checkpoint] → MODEL → [SEngine LoRA Loader] → MODEL → [KSampler]
                  → CLIP  → [SEngine LoRA Loader] → CLIP  → [CLIP Text Encode]
```

### 5. Adjust Strengths

- Each selected LoRA gets a **strength slider** on the node (0.0 - 2.0)
- Adjust in the sidebar or directly on the node
- Use **▲/▼ buttons** in the sidebar to reorder LoRAs

### 6. Run Your Workflow

- LoRAs are downloaded automatically if not already cached
- Download progress is shown in the sidebar
- Downloaded LoRAs are stored in `ComfyUI/models/loras/`

## Node Inputs/Outputs

| Input | Type | Description |
|-------|------|-------------|
| model | MODEL | Base model to apply LoRAs to |
| clip | CLIP | (Optional) CLIP model for text encoder LoRA weights |

| Output | Type | Description |
|--------|------|-------------|
| MODEL | MODEL | Model with LoRAs applied |
| CLIP | CLIP | CLIP with LoRAs applied |

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

## License

MIT License

## Credits

- **SWORKS_TEAM** - LoRA creators
- Built for the ComfyUI community


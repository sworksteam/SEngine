/**
 * SEngine - Reactive LoRA Browser with Image Previews
 */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_TYPE = "SEngineLoraLoader";

// Track download states
const downloadStates = {};

// ============================================================================
// Styles
// ============================================================================

const STYLES = `
.sengine-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #1e1e1e;
    color: #e0e0e0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 12px;
    overflow: hidden;
}
.sengine-header {
    padding: 16px;
    background: linear-gradient(180deg, #2a2a2a 0%, #222 100%);
    border-bottom: 1px solid #3a3a3a;
}
.sengine-title {
    font-size: 15px;
    font-weight: 600;
    color: #fff;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.sengine-title::before { content: "⚡"; }
.sengine-api-row { margin-bottom: 10px; }
.sengine-label {
    font-size: 10px;
    color: #888;
    margin-bottom: 4px;
    display: block;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.sengine-input {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid #444;
    border-radius: 6px;
    background: #2a2a2a;
    color: #fff;
    font-size: 12px;
    box-sizing: border-box;
}
.sengine-input:focus { border-color: #5a5; outline: none; }
.sengine-target {
    padding: 8px 12px;
    background: #252525;
    border-radius: 6px;
    font-size: 11px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.sengine-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #555;
}
.sengine-dot.active { background: #5a5; box-shadow: 0 0 6px #5a5; }
.sengine-target-text { color: #777; }
.sengine-target-text.active { color: #8c8; }
.sengine-toolbar {
    padding: 10px 16px;
    display: flex;
    gap: 8px;
    background: #252525;
    border-bottom: 1px solid #333;
}
.sengine-search {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #444;
    border-radius: 6px;
    background: #1e1e1e;
    color: #fff;
    font-size: 12px;
}
.sengine-search:focus { border-color: #5a5; outline: none; }
.sengine-btn {
    padding: 8px 14px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    background: #3a3a3a;
    color: #fff;
}
.sengine-btn:hover { background: #4a4a4a; }
.sengine-filter-row {
    padding: 8px 16px;
    background: #252525;
    border-bottom: 1px solid #333;
}
.sengine-filter-container {
    position: relative;
}
.sengine-filter-btn {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #444;
    border-radius: 6px;
    background: #1e1e1e;
    color: #ccc;
    font-size: 12px;
    cursor: pointer;
    text-align: left;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.sengine-filter-btn:hover { border-color: #555; }
.sengine-filter-btn.active { border-color: #5a5; }
.sengine-filter-arrow { font-size: 10px; color: #666; }
.sengine-filter-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    margin-top: 4px;
    background: #2a2a2a;
    border: 1px solid #444;
    border-radius: 6px;
    max-height: 200px;
    overflow-y: auto;
    z-index: 1000;
    display: none;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
.sengine-filter-dropdown.open { display: block; }
.sengine-filter-option {
    padding: 8px 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    color: #bbb;
}
.sengine-filter-option:hover { background: #333; }
.sengine-filter-option.selected { background: #2a3a2a; color: #8c8; }
.sengine-filter-checkbox {
    width: 14px;
    height: 14px;
    border: 1px solid #555;
    border-radius: 3px;
    background: #1e1e1e;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    color: #5a5;
}
.sengine-filter-option.selected .sengine-filter-checkbox {
    background: #3a5a3a;
    border-color: #5a5;
}
.sengine-filter-count {
    margin-left: auto;
    color: #666;
    font-size: 10px;
}
.sengine-selected-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 6px;
}
.sengine-selected-tag {
    padding: 2px 8px;
    background: #2a3a2a;
    border: 1px solid #5a5;
    border-radius: 10px;
    font-size: 10px;
    color: #8c8;
    display: flex;
    align-items: center;
    gap: 4px;
}
.sengine-selected-tag-remove {
    cursor: pointer;
    opacity: 0.7;
}
.sengine-selected-tag-remove:hover { opacity: 1; }
.sengine-browser {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    background: #1a1a1a;
}
.sengine-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
}
.sengine-lora {
    background: #2a2a2a;
    border-radius: 8px;
    overflow: hidden;
    cursor: pointer;
    border: 2px solid transparent;
    transition: all 0.15s;
}
.sengine-lora:hover {
    background: #333;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.sengine-lora.selected { border-color: #5a5; background: #2a3a2a; }
.sengine-lora-img {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    background: #222;
    display: block;
}
.sengine-lora-placeholder {
    width: 100%;
    aspect-ratio: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    font-weight: bold;
    background: linear-gradient(135deg, #333 0%, #222 100%);
}
.sengine-lora-info { padding: 8px; }
.sengine-lora-name {
    font-size: 10px;
    color: #bbb;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.sengine-lora.selected .sengine-lora-name { color: #8c8; }
.sengine-status {
    padding: 8px 16px;
    font-size: 11px;
    color: #666;
    background: #1a1a1a;
    border-top: 1px solid #333;
    border-bottom: 1px solid #333;
}
.sengine-selected {
    background: #222;
    max-height: 220px;
    display: flex;
    flex-direction: column;
}
.sengine-selected-header {
    padding: 10px 16px;
    font-size: 11px;
    font-weight: 600;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    background: #252525;
    border-bottom: 1px solid #333;
}
.sengine-selected-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
}
.sengine-item {
    padding: 10px;
    margin-bottom: 6px;
    background: #2a2a2a;
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.sengine-item:hover { background: #333; }
.sengine-item-thumb {
    width: 36px;
    height: 36px;
    border-radius: 4px;
    object-fit: cover;
    background: #333;
}
.sengine-item-details { flex: 1; min-width: 0; }
.sengine-item-name {
    font-size: 11px;
    color: #ccc;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 4px;
}
.sengine-item-strength { display: flex; align-items: center; gap: 6px; }
.sengine-strength-input {
    width: 50px;
    padding: 4px 6px;
    border: 1px solid #444;
    border-radius: 4px;
    background: #1e1e1e;
    color: #fff;
    font-size: 11px;
    text-align: center;
}
.sengine-strength-input:focus { border-color: #5a5; outline: none; }
.sengine-remove {
    width: 24px;
    height: 24px;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: #666;
    cursor: pointer;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.sengine-remove:hover { background: #522; color: #f88; }
.sengine-reorder {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-right: 4px;
}
.sengine-reorder-btn {
    width: 20px;
    height: 14px;
    border: none;
    border-radius: 3px;
    background: #333;
    color: #888;
    cursor: pointer;
    font-size: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
}
.sengine-reorder-btn:hover { background: #444; color: #fff; }
.sengine-reorder-btn:disabled { opacity: 0.3; cursor: default; }
.sengine-reorder-btn:disabled:hover { background: #333; color: #888; }
.sengine-empty {
    padding: 30px 20px;
    text-align: center;
    color: #555;
    font-size: 12px;
}
.sengine-loading {
    padding: 40px 20px;
    text-align: center;
    color: #666;
}
.sengine-progress {
    height: 16px;
    background: #333;
    border-radius: 8px;
    overflow: hidden;
    position: relative;
}
.sengine-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #4a4 0%, #5b5 100%);
    border-radius: 8px;
    transition: width 0.2s ease;
}
.sengine-progress span {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 9px;
    color: #fff;
    text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}
`;

// ============================================================================
// API
// ============================================================================

const sengineAPI = {
    cache: null,
    cacheTime: 0,
    async fetchLoras(apiKey = "", refresh = false) {
        if (!refresh && this.cache && Date.now() - this.cacheTime < 60000) {
            return this.cache;
        }
        try {
            const params = new URLSearchParams();
            if (apiKey) params.set("api_key", apiKey);
            if (refresh) params.set("refresh", "true");
            const resp = await api.fetchApi(`/sengine/loras?${params}`);
            const data = await resp.json();
            if (data.success) {
                this.cache = data.loras;
                this.cacheTime = Date.now();
            }
            return this.cache || [];
        } catch (e) {
            console.error("[SEngine]", e);
            return this.cache || [];
        }
    }
};

// ============================================================================
// Manager
// ============================================================================

class SEngineManager {
    constructor() {
        this.panel = null;
        this.loras = [];
        this.selectedLoras = [];
        this.searchQuery = "";
        this.selectedTags = [];
        this.apiKey = localStorage.getItem("sengine_api_key") || "";
        this.targetNode = null;
    }

    getOrCreateNode() {
        let node = app.graph._nodes.find(n => n.type === NODE_TYPE);
        if (!node) {
            node = LiteGraph.createNode(NODE_TYPE);
            const canvas = app.canvas;
            if (canvas) {
                const cx = (-canvas.ds.offset[0] + canvas.canvas.width / 2) / canvas.ds.scale;
                const cy = (-canvas.ds.offset[1] + canvas.canvas.height / 2) / canvas.ds.scale;
                node.pos = [cx - 100, cy - 50];
            } else {
                node.pos = [100, 100];
            }
            app.graph.add(node);
        }
        this.setTargetNode(node);
        return node;
    }

    setTargetNode(node) {
        this.targetNode = node;
        if (node) {
            // Try to load from widget first, then from property
            const dataWidget = node.widgets?.find(w => w.name === "sengine_data");
            const jsonStr = dataWidget?.value || node.sengineData || "{}";

            try {
                const data = JSON.parse(jsonStr);
                this.selectedLoras = data.loras || [];
                if (data.api_key) this.apiKey = data.api_key;
            } catch (e) {
                this.selectedLoras = [];
            }
        } else {
            this.selectedLoras = [];
        }
        this.updateUI();
        this.renderGrid();
        this.renderSelected();
    }

    saveToNode() {
        if (!this.targetNode) return;

        const data = {
            api_key: this.apiKey,
            loras: this.selectedLoras.map(l => ({
                version_id: l.version_id,
                name: l.name,
                strength: l.strength,
                strength_clip: l.strength_clip,
                file_name: l.file_name,
                download_url: l.download_url || "",
                preview_url: l.preview_url || ""
            }))
        };

        const jsonStr = JSON.stringify(data);

        // Store on node property for serialization
        this.targetNode.sengineData = jsonStr;

        // Also update the actual widget for execution
        const dataWidget = this.targetNode.widgets?.find(w => w.name === "sengine_data");
        if (dataWidget) {
            dataWidget.value = jsonStr;
        }

        this.rebuildNodeWidgets();
    }

    rebuildNodeWidgets() {
        const node = this.targetNode;
        if (!node) return;

        // Keep only the sengine_data widget (hidden but needed for execution)
        const dataWidget = node.widgets?.find(w => w.name === "sengine_data");
        node.widgets = dataWidget ? [dataWidget] : [];

        // Hide the data widget
        if (dataWidget) {
            dataWidget.computeSize = () => [0, -4];
            dataWidget.type = "hidden";
        }

        // Add slider for each LoRA
        this.selectedLoras.forEach((lora, idx) => {
            const state = downloadStates[lora.version_id];
            const isDownloading = state?.status === "downloading";
            const isFailed = state?.status === "failed";

            let displayName = lora.name.length > 16
                ? lora.name.substring(0, 14) + ".."
                : lora.name;

            if (isDownloading) {
                const pct = Math.round((state.progress || 0) * 100);
                displayName = `⏳ ${pct}% ${displayName}`;
            } else if (isFailed) {
                displayName = `❌ ${displayName}`;
            }

            node.addWidget("number", displayName, lora.strength, (value) => {
                this.selectedLoras[idx].strength = value;
                this.selectedLoras[idx].strength_clip = value;
                this.saveToNode();
                this.renderSelected();
            }, { min: 0, max: 2, step: 0.05, precision: 2 });
        });

        // Update title and color
        const downloading = this.selectedLoras.filter(l => downloadStates[l.version_id]?.status === "downloading").length;
        const failed = this.selectedLoras.filter(l => downloadStates[l.version_id]?.status === "failed").length;

        if (downloading > 0) {
            node.title = `SEngine ⏳ ${downloading} downloading...`;
            node.bgcolor = "#2a3a2a";
        } else if (failed > 0) {
            node.title = `SEngine ❌ ${failed} failed`;
            node.bgcolor = "#3a2a2a";
        } else if (this.selectedLoras.length > 0) {
            node.title = `SEngine (${this.selectedLoras.length})`;
            node.bgcolor = null;
        } else {
            node.title = "SEngine LoRA Loader";
            node.bgcolor = null;
        }

        // Resize
        const h = 30 + this.selectedLoras.length * 24;
        node.size = [Math.max(node.size?.[0] || 200, 200), Math.max(h, 60)];

        app.graph?.setDirtyCanvas(true, true);
    }

    toggleLora(lora) {
        if (!this.targetNode) {
            this.getOrCreateNode();
        }

        const idx = this.selectedLoras.findIndex(l => l.version_id === lora.version_id);
        if (idx >= 0) {
            this.selectedLoras.splice(idx, 1);
        } else {
            this.selectedLoras.push({
                version_id: lora.version_id,
                name: lora.name,
                strength: 1.0,
                strength_clip: 1.0,
                file_name: lora.file_name,
                download_url: lora.download_url || "",
                preview_url: lora.preview_url || ""
            });
        }

        this.saveToNode();
        this.renderGrid();
        this.renderSelected();
    }

    updateStrength(idx, value) {
        if (this.selectedLoras[idx]) {
            this.selectedLoras[idx].strength = value;
            this.selectedLoras[idx].strength_clip = value;
            this.saveToNode();
        }
    }

    removeLora(idx) {
        this.selectedLoras.splice(idx, 1);
        this.saveToNode();
        this.renderGrid();
        this.renderSelected();
    }

    moveLoraUp(idx) {
        if (idx <= 0 || idx >= this.selectedLoras.length) return;
        const temp = this.selectedLoras[idx];
        this.selectedLoras[idx] = this.selectedLoras[idx - 1];
        this.selectedLoras[idx - 1] = temp;
        this.saveToNode();
        this.renderSelected();
    }

    moveLoraDown(idx) {
        if (idx < 0 || idx >= this.selectedLoras.length - 1) return;
        const temp = this.selectedLoras[idx];
        this.selectedLoras[idx] = this.selectedLoras[idx + 1];
        this.selectedLoras[idx + 1] = temp;
        this.saveToNode();
        this.renderSelected();
    }

    toggleTag(tag) {
        const idx = this.selectedTags.indexOf(tag);
        if (idx >= 0) {
            this.selectedTags.splice(idx, 1);
        } else {
            this.selectedTags.push(tag);
        }
        this.renderTags();
        this.renderGrid();
    }

    clearTags() {
        this.selectedTags = [];
        this.renderTags();
        this.renderGrid();
    }

    getAllTags() {
        const tagCounts = {};
        this.loras.forEach(lora => {
            (lora.tags || []).forEach(tag => {
                tagCounts[tag] = (tagCounts[tag] || 0) + 1;
            });
        });
        // Sort by count descending
        return Object.entries(tagCounts)
            .sort((a, b) => b[1] - a[1])
            .map(([tag, count]) => ({ tag, count }));
    }

    // ========== UI ==========

    createPanel() {
        if (!document.getElementById("sengine-styles")) {
            const styleEl = document.createElement("style");
            styleEl.id = "sengine-styles";
            styleEl.textContent = STYLES;
            document.head.appendChild(styleEl);
        }

        const panel = document.createElement("div");
        panel.className = "sengine-panel";
        panel.innerHTML = `
            <div class="sengine-header">
                <div class="sengine-title">SEngine LoRAs</div>
                <div class="sengine-api-row">
                    <label class="sengine-label">Civitai API Key</label>
                    <input type="password" class="sengine-input sengine-api-key" placeholder="Enter API key for downloads...">
                </div>
                <div class="sengine-target">
                    <div class="sengine-dot"></div>
                    <span class="sengine-target-text">Click a LoRA to create node</span>
                </div>
            </div>
            <div class="sengine-toolbar">
                <input type="text" class="sengine-search" placeholder="Search LoRAs...">
                <button class="sengine-btn sengine-refresh">↻</button>
            </div>
            <div class="sengine-filter-row">
                <div class="sengine-filter-container">
                    <button class="sengine-filter-btn">
                        <span class="sengine-filter-text">Filter by tags...</span>
                        <span class="sengine-filter-arrow">▼</span>
                    </button>
                    <div class="sengine-filter-dropdown"></div>
                </div>
                <div class="sengine-selected-tags"></div>
            </div>
            <div class="sengine-browser">
                <div class="sengine-empty">Click ↻ to load LoRAs</div>
            </div>
            <div class="sengine-status"></div>
            <div class="sengine-selected">
                <div class="sengine-selected-header">Selected (<span class="sengine-count">0</span>)</div>
                <div class="sengine-selected-list">
                    <div class="sengine-empty">Select LoRAs above</div>
                </div>
            </div>
        `;

        this.panel = panel;

        const apiInput = panel.querySelector(".sengine-api-key");
        apiInput.value = this.apiKey;
        apiInput.oninput = (e) => {
            this.apiKey = e.target.value;
            localStorage.setItem("sengine_api_key", this.apiKey);
            if (this.targetNode) this.saveToNode();
        };

        panel.querySelector(".sengine-search").oninput = (e) => {
            this.searchQuery = e.target.value;
            this.renderGrid();
        };

        panel.querySelector(".sengine-refresh").onclick = () => this.loadLoras(true);

        // Setup filter dropdown after panel is ready
        setTimeout(() => this.setupFilterDropdown(), 0);

        return panel;
    }

    updateUI() {
        if (!this.panel) return;
        const dot = this.panel.querySelector(".sengine-dot");
        const text = this.panel.querySelector(".sengine-target-text");

        if (this.targetNode) {
            dot?.classList.add("active");
            text?.classList.add("active");
            if (text) text.textContent = `Node #${this.targetNode.id}`;
        } else {
            dot?.classList.remove("active");
            text?.classList.remove("active");
            if (text) text.textContent = "Click a LoRA to create node";
        }
    }

    async loadLoras(refresh = false) {
        const browser = this.panel?.querySelector(".sengine-browser");
        if (browser) browser.innerHTML = '<div class="sengine-loading">Loading LoRAs...</div>';
        this.loras = await sengineAPI.fetchLoras(this.apiKey, refresh);
        this.renderTags();
        this.renderGrid();
    }

    renderTags() {
        const filterRow = this.panel?.querySelector(".sengine-filter-row");
        const dropdown = this.panel?.querySelector(".sengine-filter-dropdown");
        const filterBtn = this.panel?.querySelector(".sengine-filter-btn");
        const filterText = this.panel?.querySelector(".sengine-filter-text");
        const selectedTagsContainer = this.panel?.querySelector(".sengine-selected-tags");

        if (!dropdown || !filterRow) return;

        const allTags = this.getAllTags();
        if (!allTags.length) {
            filterRow.style.display = "none";
            return;
        }

        filterRow.style.display = "block";

        // Update button text
        if (filterText) {
            filterText.textContent = this.selectedTags.length > 0
                ? `${this.selectedTags.length} tag${this.selectedTags.length > 1 ? 's' : ''} selected`
                : "Filter by tags...";
        }
        if (filterBtn) {
            filterBtn.classList.toggle("active", this.selectedTags.length > 0);
        }

        // Render dropdown options
        dropdown.innerHTML = "";
        allTags.forEach(({ tag, count }) => {
            const isSelected = this.selectedTags.includes(tag);
            const el = document.createElement("div");
            el.className = `sengine-filter-option ${isSelected ? 'selected' : ''}`;
            el.innerHTML = `
                <span class="sengine-filter-checkbox">${isSelected ? '✓' : ''}</span>
                <span>${tag}</span>
                <span class="sengine-filter-count">${count}</span>
            `;
            el.onclick = (e) => {
                e.stopPropagation();
                this.toggleTag(tag);
            };
            dropdown.appendChild(el);
        });

        // Render selected tags as removable chips
        if (selectedTagsContainer) {
            selectedTagsContainer.innerHTML = "";
            this.selectedTags.forEach(tag => {
                const chip = document.createElement("span");
                chip.className = "sengine-selected-tag";
                chip.innerHTML = `${tag}<span class="sengine-selected-tag-remove">✕</span>`;
                chip.querySelector(".sengine-selected-tag-remove").onclick = (e) => {
                    e.stopPropagation();
                    this.toggleTag(tag);
                };
                selectedTagsContainer.appendChild(chip);
            });
        }
    }

    setupFilterDropdown() {
        const filterBtn = this.panel?.querySelector(".sengine-filter-btn");
        const dropdown = this.panel?.querySelector(".sengine-filter-dropdown");

        if (!filterBtn || !dropdown) return;

        filterBtn.onclick = (e) => {
            e.stopPropagation();
            dropdown.classList.toggle("open");
        };

        // Close dropdown when clicking outside
        document.addEventListener("click", (e) => {
            if (!this.panel?.contains(e.target) || !e.target.closest(".sengine-filter-container")) {
                dropdown.classList.remove("open");
            }
        });
    }

    renderGrid() {
        const browser = this.panel?.querySelector(".sengine-browser");
        const status = this.panel?.querySelector(".sengine-status");
        if (!browser) return;

        let list = this.loras;

        // Filter by selected tags (AND logic - must have all selected tags)
        if (this.selectedTags.length > 0) {
            list = list.filter(l =>
                this.selectedTags.every(tag => (l.tags || []).includes(tag))
            );
        }

        // Filter by search query
        if (this.searchQuery) {
            const q = this.searchQuery.toLowerCase();
            list = list.filter(l =>
                l.name.toLowerCase().includes(q) ||
                (l.trained_words || []).some(w => w.toLowerCase().includes(q)) ||
                (l.tags || []).some(t => t.toLowerCase().includes(q))
            );
        }

        if (!this.loras.length) {
            browser.innerHTML = '<div class="sengine-empty">Click ↻ to load LoRAs</div>';
            if (status) status.textContent = "";
            return;
        }

        if (!list.length) {
            browser.innerHTML = '<div class="sengine-empty">No matches found</div>';
            if (status) status.textContent = `0 of ${this.loras.length} LoRAs`;
            return;
        }

        const grid = document.createElement("div");
        grid.className = "sengine-grid";

        list.forEach(lora => {
            const isSelected = this.selectedLoras.some(l => l.version_id === lora.version_id);
            const previewUrl = lora.preview_url || "";

            const el = document.createElement("div");
            el.className = `sengine-lora ${isSelected ? 'selected' : ''}`;
            el.title = lora.name;

            if (previewUrl) {
                el.innerHTML = `
                    <img class="sengine-lora-img" src="${previewUrl}" alt="" loading="lazy">
                    <div class="sengine-lora-info">
                        <div class="sengine-lora-name">${lora.name}</div>
                    </div>
                `;
            } else {
                const hue = lora.name.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 360;
                el.innerHTML = `
                    <div class="sengine-lora-placeholder" style="background:linear-gradient(135deg, hsl(${hue},30%,25%) 0%, hsl(${hue},25%,18%) 100%); color:hsl(${hue},45%,55%);">
                        ${lora.name[0].toUpperCase()}
                    </div>
                    <div class="sengine-lora-info">
                        <div class="sengine-lora-name">${lora.name}</div>
                    </div>
                `;
            }

            el.onclick = () => this.toggleLora(lora);
            grid.appendChild(el);
        });

        browser.innerHTML = "";
        browser.appendChild(grid);
        if (status) status.textContent = `${list.length} of ${this.loras.length} LoRAs`;
    }

    renderSelected() {
        if (!this.panel) return;

        const list = this.panel.querySelector(".sengine-selected-list");
        const count = this.panel.querySelector(".sengine-count");
        if (!list) return;

        if (count) count.textContent = this.selectedLoras.length;

        if (!this.selectedLoras.length) {
            list.innerHTML = '<div class="sengine-empty">Select LoRAs above</div>';
            return;
        }

        list.innerHTML = "";
        const totalLoras = this.selectedLoras.length;
        this.selectedLoras.forEach((lora, idx) => {
            const state = downloadStates[lora.version_id];
            const isDownloading = state?.status === "downloading";
            const isFailed = state?.status === "failed";

            const el = document.createElement("div");
            el.className = "sengine-item";
            if (isFailed) el.style.background = "#422";

            const thumbHtml = lora.preview_url
                ? `<img class="sengine-item-thumb" src="${lora.preview_url}" alt="">`
                : `<div class="sengine-item-thumb" style="display:flex;align-items:center;justify-content:center;font-weight:bold;color:#666;">${lora.name[0]}</div>`;

            let statusHtml = "";
            if (isDownloading) {
                const pct = Math.round((state.progress || 0) * 100);
                statusHtml = `<div class="sengine-progress"><div class="sengine-progress-bar" style="width:${pct}%"></div><span>${pct}%</span></div>`;
            } else if (isFailed) {
                statusHtml = `<div style="color:#f66;font-size:10px;">Download failed</div>`;
            }

            el.innerHTML = `
                <div class="sengine-reorder">
                    <button class="sengine-reorder-btn sengine-move-up" ${idx === 0 ? 'disabled' : ''} title="Move up">▲</button>
                    <button class="sengine-reorder-btn sengine-move-down" ${idx === totalLoras - 1 ? 'disabled' : ''} title="Move down">▼</button>
                </div>
                ${thumbHtml}
                <div class="sengine-item-details">
                    <div class="sengine-item-name" title="${lora.name}" style="${isFailed ? 'color:#f88;' : ''}">${lora.name}</div>
                    ${statusHtml || `<div class="sengine-item-strength">
                        <input type="number" class="sengine-strength-input" value="${lora.strength.toFixed(2)}" min="0" max="2" step="0.05">
                    </div>`}
                </div>
                <button class="sengine-remove">×</button>
            `;

            const strengthInput = el.querySelector(".sengine-strength-input");
            if (strengthInput) {
                strengthInput.onchange = (e) => {
                    const v = Math.max(0, Math.min(2, parseFloat(e.target.value) || 0));
                    e.target.value = v.toFixed(2);
                    this.updateStrength(idx, v);
                };
            }

            el.querySelector(".sengine-move-up").onclick = () => this.moveLoraUp(idx);
            el.querySelector(".sengine-move-down").onclick = () => this.moveLoraDown(idx);
            el.querySelector(".sengine-remove").onclick = () => this.removeLora(idx);
            list.appendChild(el);
        });
    }
}

const sengine = new SEngineManager();

// ============================================================================
// Extension
// ============================================================================

app.registerExtension({
    name: "SEngine.LoraLoader",

    async setup() {
        // Throttle UI updates during download
        let lastUIUpdate = 0;
        const UI_UPDATE_INTERVAL = 500; // Update UI at most every 500ms

        // Listen for download progress
        api.addEventListener("sengine_progress", (event) => {
            const { version_id, progress, status, name } = event.detail;
            const prevStatus = downloadStates[version_id]?.status;
            downloadStates[version_id] = { progress, status, name };

            const now = Date.now();
            const statusChanged = status !== prevStatus;

            // Only update sidebar UI, don't touch node during execution
            if (statusChanged || now - lastUIUpdate > UI_UPDATE_INTERVAL) {
                lastUIUpdate = now;
                sengine.renderSelected();
            }

            if (status === "complete" || status === "failed") {
                setTimeout(() => {
                    delete downloadStates[version_id];
                    // Only rebuild node after all downloads done
                    if (sengine.targetNode && Object.keys(downloadStates).length === 0) {
                        sengine.rebuildNodeWidgets();
                    }
                    sengine.renderSelected();
                }, 1000);
            }
        });

        const panel = sengine.createPanel();

        // Load LoRAs on startup
        sengine.loadLoras();

        if (app.extensionManager?.registerSidebarTab) {
            app.extensionManager.registerSidebarTab({
                id: "sengine",
                icon: "pi pi-bolt",
                title: "SEngine",
                tooltip: "SEngine LoRA Browser",
                type: "custom",
                render: (el) => {
                    el.appendChild(panel);
                }
            });
        } else {
            const btn = document.createElement("button");
            btn.innerHTML = "⚡";
            btn.style.cssText = "position:fixed;bottom:20px;right:20px;width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#5a5 0%,#383 100%);color:#fff;border:none;font-size:20px;cursor:pointer;z-index:1000;box-shadow:0 4px 15px rgba(0,0,0,.3);";

            const floatPanel = document.createElement("div");
            floatPanel.style.cssText = "position:fixed;bottom:78px;right:20px;width:320px;height:520px;border-radius:12px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.4);z-index:999;display:none;";
            floatPanel.appendChild(panel);

            let open = false;
            btn.onclick = () => {
                open = !open;
                floatPanel.style.display = open ? "block" : "none";
            };

            document.body.appendChild(btn);
            document.body.appendChild(floatPanel);
        }
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_TYPE) return;

        // Context menu
        const origMenu = nodeType.prototype.getExtraMenuOptions;
        nodeType.prototype.getExtraMenuOptions = function(canvas, options) {
            origMenu?.apply(this, arguments);
            options.push(null, {
                content: "Clear All LoRAs",
                callback: () => {
                    this.sengineData = "{}";
                    this.title = "SEngine LoRA Loader";
                    if (sengine.targetNode === this) {
                        sengine.selectedLoras = [];
                        sengine.rebuildNodeWidgets();
                        sengine.renderGrid();
                        sengine.renderSelected();
                    }
                    app.graph.setDirtyCanvas(true, true);
                }
            });
        };

        // On created
        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            origCreated?.apply(this, arguments);

            // Hide the sengine_data widget
            const dataWidget = this.widgets?.find(w => w.name === "sengine_data");
            if (dataWidget) {
                dataWidget.computeSize = () => [0, -4];
                dataWidget.type = "hidden";
            }

            this.sengineData = "{}";
            sengine.setTargetNode(this);
        };

        // On selected
        const origSelected = nodeType.prototype.onSelected;
        nodeType.prototype.onSelected = function() {
            origSelected?.apply(this, arguments);
            sengine.setTargetNode(this);
        };

        // Serialize - save sengineData
        const origSerialize = nodeType.prototype.serialize;
        nodeType.prototype.serialize = function() {
            const data = origSerialize ? origSerialize.call(this) : {};
            data.sengineData = this.sengineData || "{}";
            return data;
        };

        // Configure - restore sengineData
        const origConfigure = nodeType.prototype.configure;
        nodeType.prototype.configure = function(data) {
            origConfigure?.call(this, data);

            // Hide the sengine_data widget
            const dataWidget = this.widgets?.find(w => w.name === "sengine_data");
            if (dataWidget) {
                dataWidget.computeSize = () => [0, -4];
                dataWidget.type = "hidden";

                // Restore value from sengineData if widget is empty
                if (data.sengineData && (!dataWidget.value || dataWidget.value === "{}")) {
                    dataWidget.value = data.sengineData;
                }
            }

            this.sengineData = data.sengineData || dataWidget?.value || "{}";

            // Rebuild after a delay
            setTimeout(() => {
                sengine.setTargetNode(this);
                sengine.rebuildNodeWidgets();
            }, 100);
        };
    }
});

console.log("[SEngine] Loaded");

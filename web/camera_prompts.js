/* Camera Prompt Presets: file upload + dynamic JSON title dropdown. */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const ROUTE = "/camera_prompt_presets";

async function getJson(path, options) {
    const response = await api.fetchApi(path, options);
    let body;
    try {
        body = await response.json();
    } catch (_) {
        throw new Error(`Unexpected server response (${response.status})`);
    }
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    return body;
}

function updateCombo(widget, names, desired) {
    const values = names.length ? names : ["(no choices found)"];
    // Built-in LiteGraph COMBO widgets expose the selectable values here.
    widget.options.values = values;
    widget.value = values.includes(desired) ? desired : values[0];
}

function reportError(error) {
    console.error("[Camera Prompt Presets]", error);
    window.alert(`Camera Prompt Presets: ${error.message || String(error)}`);
}

function uploadDialog(node) {
    const picker = document.createElement("input");
    picker.type = "file";
    picker.accept = ".json,application/json";
    picker.addEventListener("change", async () => {
        const file = picker.files?.[0];
        if (!file) return;
        if (!file.name.toLowerCase().endsWith(".json")) {
            reportError(new Error("Please choose a .json file."));
            return;
        }
        try {
            const form = new FormData();
            form.append("file", file, file.name);
            const uploaded = await getJson(`${ROUTE}/upload`, { method: "POST", body: form });
            await node.cameraRefreshLibraries(uploaded.library);
        } catch (error) {
            reportError(error);
        }
    }, { once: true });
    picker.click();
}

app.registerExtension({
    name: "Cyberdelia.CameraPromptPresets",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "CameraPromptPresets") return;
        const onCreated = nodeType.prototype.onNodeCreated;
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onNodeCreated = function () {
            const result = onCreated?.apply(this, arguments);
            const node = this;
            const libraryWidget = node.widgets?.find(w => w.name === "library");
            const presetWidget = node.widgets?.find(w => w.name === "preset");
            if (!libraryWidget || !presetWidget) return result;

            let generation = 0;
            const priorLibraryCallback = libraryWidget.callback;

            node.cameraRefreshPresets = async (preferTitle) => {
                const sequence = ++generation;
                const library = libraryWidget.value;
                const response = await getJson(`${ROUTE}/presets?library=${encodeURIComponent(library)}`);
                if (sequence !== generation || libraryWidget.value !== library) return;
                updateCombo(presetWidget, response.presets.map(p => p.title), preferTitle ?? presetWidget.value);
                node.setDirtyCanvas?.(true, true);
            };

            node.cameraRefreshLibraries = async (preferLibrary, preferTitle) => {
                const response = await getJson(`${ROUTE}/libraries`);
                const desired = preferLibrary ?? libraryWidget.value;
                updateCombo(libraryWidget, response.libraries, desired);
                await node.cameraRefreshPresets(preferTitle);
            };

            libraryWidget.callback = function (value, ...rest) {
                priorLibraryCallback?.call(this, value, ...rest);
                node.cameraRefreshPresets().catch(reportError);
            };

            node.addWidget("button", "Upload JSON...", "", () => uploadDialog(node));
            node.addWidget("button", "Refresh presets", "", () => {
                node.cameraRefreshLibraries().catch(reportError);
            });
            node.setSize?.([Math.max(node.size?.[0] || 300, 325), Math.max(node.size?.[1] || 220, 240)]);

            // New nodes refresh here; workflow-loaded nodes refresh in onConfigure.
            queueMicrotask(() => {
                if (!node._cameraConfigured) node.cameraRefreshLibraries().catch(reportError);
            });
            return result;
        };
        nodeType.prototype.onConfigure = function () {
            const result = onConfigure?.apply(this, arguments);
            this._cameraConfigured = true;
            const library = this.widgets?.find(w => w.name === "library")?.value;
            const title = this.widgets?.find(w => w.name === "preset")?.value;
            queueMicrotask(() => this.cameraRefreshLibraries?.(library, title).catch(reportError));
            return result;
        };
    },
});

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

const NO_PRESET = "None (no camera prompt)";
const WARNING_PREFIX = "⚠ Camera preset: ";

function updateCombo(widget, names, desired, { preserveMissing = false, fallback = undefined } = {}) {
    const values = names.length ? [...names] : ["(no choices found)"];
    widget.options.values = values;
    if (values.includes(desired)) {
        widget.value = desired;
        return true;
    }
    if (preserveMissing && typeof desired === "string" && desired.length) {
        // Keep exactly what the saved workflow requested, even if unavailable.
        widget.value = desired;
        return false;
    }
    widget.value = values.includes(fallback) ? fallback : values[0];
    return true;
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
            await node.cameraRefreshLibraries({ preferLibrary: uploaded.library, preserveMissing: false });
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
            const originalTitle = node.title.startsWith(WARNING_PREFIX)
                ? "Camera Prompt Presets (JSON)" : node.title;
            const priorLibraryCallback = libraryWidget.callback;

            node.cameraSetWarning = (message) => {
                const title = message ? `${WARNING_PREFIX}${message}` : originalTitle;
                if (node.title !== title) {
                    node.title = title; // Visible in canvas and Vue; queue validation also rejects missing selections.
                    node.setDirtyCanvas?.(true, true);
                }
                if (message && node._cameraWarning !== message) {
                    console.warn(`[Camera Prompt Presets] ${message}`);
                }
                node._cameraWarning = message;
            };

            node.cameraRefreshPresets = async ({ preferTitle, preserveMissing = true } = {}) => {
                const sequence = ++generation;
                const library = libraryWidget.value;
                const response = await getJson(`${ROUTE}/presets?library=${encodeURIComponent(library)}`);
                if (sequence !== generation || libraryWidget.value !== library) return;
                const titles = [NO_PRESET, ...response.presets.map(p => p.title)];
                const desired = preferTitle ?? presetWidget.value;
                const valid = updateCombo(presetWidget, titles, desired, {
                    preserveMissing,
                    fallback: response.presets[0]?.title ?? NO_PRESET,
                });
                node.cameraSetWarning(valid ? "" : `Missing preset: ${String(desired).slice(0, 65)}`);
                node.setDirtyCanvas?.(true, true);
            };

            node.cameraRefreshLibraries = async ({ preferLibrary, preferTitle, preserveMissing = true } = {}) => {
                const response = await getJson(`${ROUTE}/libraries`);
                const desired = preferLibrary ?? libraryWidget.value;
                const valid = updateCombo(libraryWidget, response.libraries, desired, {
                    preserveMissing,
                    fallback: response.default,
                });
                if (!valid) {
                    ++generation; // Cancel an earlier preset request for another library.
                    node.cameraSetWarning(`Missing library: ${String(desired).slice(0, 65)}`);
                    node.setDirtyCanvas?.(true, true);
                    return;
                }
                await node.cameraRefreshPresets({ preferTitle, preserveMissing });
            };

            libraryWidget.callback = function (value, ...rest) {
                priorLibraryCallback?.call(this, value, ...rest);
                // An explicit user change may select a default; reopening a workflow may not.
                node.cameraRefreshPresets({ preserveMissing: false }).catch(reportError);
            };

            const uploadButton = node.addWidget("button", "Upload JSON...", "", () => uploadDialog(node));
            const refreshButton = node.addWidget("button", "Refresh libraries", "", () => {
                node.cameraRefreshLibraries({ preserveMissing: true }).catch(reportError);
            });
            uploadButton.serialize = false;
            refreshButton.serialize = false;
            node.setSize?.([Math.max(node.size?.[0] || 300, 325), Math.max(node.size?.[1] || 220, 240)]);

            // New nodes can use the default; saved workflows must keep their exact choices.
            queueMicrotask(() => {
                if (!node._cameraConfigured) {
                    node.cameraRefreshLibraries({ preserveMissing: false }).catch(reportError);
                }
            });
            return result;
        };
        nodeType.prototype.onConfigure = function () {
            const result = onConfigure?.apply(this, arguments);
            this._cameraConfigured = true;
            const library = this.widgets?.find(w => w.name === "library")?.value;
            const title = this.widgets?.find(w => w.name === "preset")?.value;
            queueMicrotask(() => this.cameraRefreshLibraries?.({
                preferLibrary: library, preferTitle: title, preserveMissing: true,
            }).catch(reportError));
            return result;
        };
    },
});

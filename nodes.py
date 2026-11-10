"""User-editable JSON camera preset libraries for ComfyUI.

No external dependencies other than packages provided by ComfyUI.
Uploaded JSON files are stored in ComfyUI/input/camera_prompt_presets.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import folder_paths
from aiohttp import web
from server import PromptServer

NODE_FOLDER = Path(__file__).resolve().parent
BUNDLED_FOLDER = NODE_FOLDER / "libraries"
UPLOAD_FOLDER = Path(folder_paths.get_input_directory()) / "camera_prompt_presets"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_PRESETS = 500
MAX_PROMPT_LENGTH = 12000
NO_PRESET = "None (no camera prompt)"
FILENAME_RE = re.compile(r"^[\w .()\-]{1,100}\.json$", re.IGNORECASE)


def _libraries() -> dict[str, Path]:
    """Only show regular .json files directly in two approved folders."""
    files = {}
    for prefix, folder in (("built_in", BUNDLED_FOLDER), ("uploaded", UPLOAD_FOLDER)):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir(), key=lambda p: p.name.casefold()):
            if path.is_file() and not path.is_symlink() and path.suffix.casefold() == ".json":
                files[f"{prefix}:{path.name}"] = path
    return files


def _resolve_library(library: str) -> Path:
    path = _libraries().get(library)
    if path is None:
        raise ValueError(f"Unknown JSON library: {library!r}. Choose or upload a library.")
    return path


def _read_and_validate(data: bytes) -> list[dict[str, str]]:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("JSON file exceeds the 2 MB limit")
    try:
        raw = json.loads(data.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid UTF-8 JSON: {exc}") from exc
    if isinstance(raw, dict):
        raw = raw.get("presets")
    if not isinstance(raw, list) or not raw:
        raise ValueError('JSON must contain a non-empty "presets" array')
    if len(raw) > MAX_PRESETS:
        raise ValueError(f"JSON contains more than {MAX_PRESETS} presets")

    normalized = []
    seen = set()
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Preset #{i} must be an object")
        title = item.get("title")
        prompt = item.get("prompt")
        category = item.get("category", "Other")
        if not isinstance(title, str) or not title.strip() or len(title) > 160:
            raise ValueError(f"Preset #{i} needs a non-empty title of at most 160 characters")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_LENGTH:
            raise ValueError(f"Preset #{i} needs a prompt of at most {MAX_PROMPT_LENGTH} characters")
        if not isinstance(category, str) or len(category) > 120:
            raise ValueError(f"Preset #{i} has an invalid category")
        title = title.strip()
        if title.casefold() in seen:
            raise ValueError(f"Duplicate preset title: {title}")
        seen.add(title.casefold())
        normalized.append({"title": title, "prompt": prompt.strip(), "category": category.strip() or "Other"})
    if NO_PRESET.casefold() in seen:
        raise ValueError(f"Preset title {NO_PRESET!r} is reserved for the built-in no-effect choice")
    return normalized


def _load_presets(library: str) -> list[dict[str, str]]:
    return _read_and_validate(_resolve_library(library).read_bytes())


def _default_library() -> str:
    libraries = _libraries()
    preferred = "built_in:default.json"
    return preferred if preferred in libraries else next(iter(libraries), "(no libraries found)")


class CameraPromptPresets:
    """Append one named suffix from an uploaded or bundled JSON library."""

    @classmethod
    def INPUT_TYPES(cls):
        names = list(_libraries()) or ["(no libraries found)"]
        preferred = _default_library()
        try:
            preset_titles = [p["title"] for p in _load_presets(preferred)]
        except (ValueError, OSError):
            preset_titles = ["(invalid library)"]
        return {
            "required": {
                "base_prompt": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False}),
                "library": (names, {"default": preferred}),
                "preset": ([NO_PRESET, *preset_titles], {"default": preset_titles[0]}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("final_prompt", "camera_suffix", "preset_title")
    FUNCTION = "compose"
    CATEGORY = "prompt/camera"
    DESCRIPTION = "Upload a JSON preset library, choose a title, and append its prompt to your base prompt."

    @classmethod
    def VALIDATE_INPUTS(cls, library, preset, **kwargs):
        if preset == NO_PRESET:
            return True
        # Explicitly validate against current JSON rather than the stale dropdown
        # options in the original /object_info response.
        try:
            names = {item["title"] for item in _load_presets(library)}
            if preset not in names:
                return f"Preset {preset!r} is not in JSON library {library!r}"
        except (ValueError, OSError) as exc:
            return str(exc)
        return True

    @classmethod
    def IS_CHANGED(cls, base_prompt, library, preset):
        """Refresh downstream prompts when JSON changes, even under the same filename."""
        if preset == NO_PRESET:
            return "camera-prompt-disabled"
        try:
            contents = _resolve_library(library).read_bytes()
            digest = hashlib.sha256(contents).hexdigest()
        except (ValueError, OSError):
            digest = "missing"
        return f"{library}|{preset}|{digest}"

    def compose(self, base_prompt, library, preset):
        if preset == NO_PRESET:
            return ((base_prompt or "").strip(), "", NO_PRESET)
        selected = next((p for p in _load_presets(library) if p["title"] == preset), None)
        if selected is None:
            raise ValueError(f"Preset {preset!r} is not in selected JSON library")
        suffix = selected["prompt"].strip()
        base = (base_prompt or "").strip()
        return ((base + "\n\n" + suffix) if base else suffix, suffix, selected["title"])


NODE_CLASS_MAPPINGS = {"CameraPromptPresets": CameraPromptPresets}
NODE_DISPLAY_NAME_MAPPINGS = {"CameraPromptPresets": "Camera Prompt Presets (JSON)"}


def _bad(message, status=400):
    return web.json_response({"error": message}, status=status)


@PromptServer.instance.routes.get("/camera_prompt_presets/libraries")
async def list_libraries(request):
    return web.json_response({"libraries": list(_libraries()), "default": _default_library()})


@PromptServer.instance.routes.get("/camera_prompt_presets/presets")
async def list_presets(request):
    try:
        library = request.query.get("library", "")
        data = _load_presets(library)
    except (OSError, ValueError) as exc:
        return _bad(str(exc))
    return web.json_response({"presets": [{"title": d["title"], "category": d["category"]} for d in data]})


@PromptServer.instance.routes.post("/camera_prompt_presets/upload")
async def upload_library(request):
    try:
        reader = await request.multipart()
        field = await reader.next()
        if field is None or field.name != "file" or not field.filename:
            return _bad('Upload one JSON file with form field "file"')
        filename = field.filename
        if Path(filename).name != filename or "\\" in filename or not FILENAME_RE.fullmatch(filename):
            return _bad("Invalid filename. Use a simple .json filename (max 100 characters)")

        chunks = []
        size = 0
        while True:
            chunk = await field.read_chunk(size=65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                return _bad("JSON exceeds the 2 MB upload limit", status=413)
            chunks.append(chunk)
        content = b"".join(chunks)
        presets = _read_and_validate(content)
        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

        # Create temporary file in the target directory, then replace atomically.
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", prefix=".camera_", dir=UPLOAD_FOLDER, delete=False) as tmp:
                temp_file = Path(tmp.name)
                tmp.write(content)
            destination = UPLOAD_FOLDER / filename
            if destination.is_symlink():
                return _bad("Refusing to overwrite a symbolic link")
            os.replace(temp_file, destination)
        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

        return web.json_response({"library": f"uploaded:{filename}", "count": len(presets)})
    except (OSError, ValueError) as exc:
        return _bad(str(exc))

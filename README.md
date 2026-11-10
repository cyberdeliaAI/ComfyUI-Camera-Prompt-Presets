# Camera Prompt Presets — ComfyUI node

Choose a **JSON library** and a **named camera prompt** from a dropdown. The node automatically appends the chosen camera-style suffix to your existing prompt. No CSV, NegPiP or negative prompts required.

## Installation

1. With GitHub access to this private repository, open a terminal in your ComfyUI `custom_nodes` directory.
2. Clone the repository:

   ```bash
   git clone https://github.com/cyberdeliaAI/ComfyUI-Camera-Prompt-Presets.git
   ```

   Or download ZIP via GitHub **Code → Download ZIP** and extract the folder into `ComfyUI/custom_nodes/`. For a private repository, GitHub authentication is required.
3. Restart ComfyUI and refresh the browser (hard refresh if needed).
4. Add node **prompt → camera → Camera Prompt Presets (JSON)**.
5. Connect `final_prompt` to the positive text encoder of your Krea 2 workflow.

No pip packages are required beyond the normal ComfyUI installation.

## How to use

- `base_prompt`: type a scene prompt or convert this widget to an input and connect another STRING node.
- `library`: choose between the included `early_mobile_phone.json`, `other_camera_looks.json`, and your own uploaded JSON libraries.
- `preset`: dynamically shows the **titles in the selected JSON**.
- `Upload JSON...`: pick a JSON file from your computer. It is checked and stored on the ComfyUI server in `ComfyUI/input/camera_prompt_presets/`. After upload, the new file is selected automatically.
- `Refresh presets`: refresh the library list and choices after editing a JSON on disk.

Outputs:

1. `final_prompt` — base prompt + two newlines + camera suffix
2. `camera_suffix` — selected camera prompt only
3. `preset_title` — selected title

When you queue the workflow, the server reads the selected JSON file again. Edited libraries are automatically detected as changed by ComfyUI caching. **The dropdown refreshes when you switch libraries, upload, or press Refresh presets.**

## JSON format

```json
{
  "presets": [
    {
      "title": "Early phone - Medium",
      "category": "Mobile Phone",
      "prompt": "An authentic amateur snapshot from a cheap 2005 mobile phone..."
    },
    {
      "title": "Indoor harsh flash",
      "category": "Flash",
      "prompt": "A casual early-2000s snapshot with flat direct flash..."
    }
  ]
}
```

The `title` and `prompt` fields are required; `category` is optional and reserved for later filtering/grouping. It does not currently create a separate category dropdown. Preset titles must be unique within each library. The default preset is **01 | General early-phone snapshot**.

The bundled `early_mobile_phone.json` library includes **24 full prompts** and **10 compact prompts** from the Krea 2 mobile-phone prompt collection. The included `other_camera_looks.json` contains **14 more camera styles**, such as cheap digital compacts, webcams, VHS, disposable film, instant film and early smartphone cameras.

## Notes

- Uploaded files remain in `ComfyUI/input/camera_prompt_presets/` and may be edited in any text editor. Re-uploading a filename replaces that uploaded file.
- The `library` selection is saved as a reference in the workflow. If you move the workflow to another ComfyUI computer, also copy the JSON file.
- Changing the JSON files does **not** require restarting ComfyUI; press `Refresh presets` to update the dropdown list.
- Intended for **self-hosted ComfyUI** installations with access to custom nodes and their server extensions; this has not been validated on ComfyUI Cloud or other restricted hosts.
- This is a new implementation and has passed local Python and JavaScript checks, but has **not yet been tested in a running ComfyUI editor**.

## Troubleshooting

- **Dropdown does not update**: hard refresh the ComfyUI browser, then click `Refresh presets`.
- **Workflow reports invalid preset**: the title was renamed or removed from JSON; choose another preset.
- **Uploaded file missing after moving computers**: copy the corresponding `.json` from `input/camera_prompt_presets/`.
- **Syntax error**: JSON requires double-quoted keys/values and no trailing commas.

## Local checks

Run `python -m unittest discover -s tests -v` in this folder to exercise the JSON parser and prompt composition. Frontend syntax can be checked with `node --check web/camera_prompts.js`. These checks are not a substitute for testing the browser dropdown with your installed version of ComfyUI.

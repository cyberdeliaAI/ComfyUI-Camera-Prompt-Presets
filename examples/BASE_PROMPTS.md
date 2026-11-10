# Example base prompts for Krea 2

These are **scene prompts** deliberately written without camera or lighting instructions. Enter one as `base_prompt` in the ComfyUI node, then select **one** camera preset from the `library` and `preset` dropdowns.

The node outputs `final_prompt` (scene + selected camera effect), `camera_suffix` (effect alone), and `preset_title`.

## 1. Everyday moment

**Base prompt**

> Two friends sitting on a worn couch in a modest living room, laughing at something outside the frame. One is holding a game controller, and the other has a bowl of snacks on their lap. The composition feels spontaneous.

**Try** `built_in:default.json` → `Mobile Phone | Medium (2005)`

## 2. Party photo

**Base prompt**

> Three friends standing close together at a crowded birthday party, one raising a paper cup and the others smiling directly at the camera. A few people are partially visible behind them.

**Try** `Mobile Phone | Indoor flash` or upload `examples/custom_camera_presets.json` and choose `2003 | Nightclub with harsh flash`

## 3. Street candid

**Base prompt**

> A person carrying a grocery bag beside a row of bicycles on a narrow residential street, surrounded by ordinary parked cars and brick houses. The subject is caught mid-step and does not appear to be posing.

**Try** `Mobile Phone | Outdoor daylight`

## 4. Office memory

**Base prompt**

> Two colleagues standing near a cluttered desk in a small office, a stack of paper folders and an old desktop monitor in the background, photographed during an ordinary workday.

**Try** `Mobile Phone | Fluorescent office`

## 5. Found computer photo

**Base prompt**

> A teenager sitting cross-legged on a bedroom floor, surrounded by scattered CD cases and a small portable stereo. The room feels personal and lived-in.

**Try** `Mobile Phone | Recovered file`

## 6. Other camera medium

**Base prompt**

> A family at a picnic table in a small park, paper plates, juice cartons and a birthday cake on the table, everyone distracted by something happening off camera.

**Try** `Film | 1990s disposable camera`

## Custom libraries

Copy `examples/minimal.json` for the simplest format. Use `examples/custom_camera_presets.json` if you also want categories, a library name and version.

To use an example JSON in the node:

1. Open ComfyUI and find **Camera Prompt Presets (JSON)**.
2. Click **Upload JSON...**, choose the example JSON saved on your computer.
3. Select a preset title from the updated dropdown.
4. Connect `final_prompt` to your positive Krea 2 text encoder.

**Note:** The files in `examples/` are *templates*, not built-in dropdown libraries. To make one selectable, upload it or copy it into `libraries/` and click **Refresh presets**.

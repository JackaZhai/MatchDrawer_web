# ComfyUI Node Workbench Design

**Goal**

Add a left-sidebar feature named **生图工作台** to MatchDrawer. The feature should feel like a lightweight native ComfyUI node editor inside this project while executing real workflows through a real ComfyUI backend.

The workbench will support importing, editing, and running common GrsAI ComfyUI workflows, especially the ComfyUI-GrsAI capabilities for text-to-image, image-to-image, multi-image fusion, and batch generation. The project should also be able to manage a local ComfyUI runtime under an ignored project directory so users can install, start, stop, and check ComfyUI from MatchDrawer instead of manually wiring every piece.

**Scope**

- Add a left navigation entry named **生图工作台**.
- Build a native node-canvas UI in this project, not an iframe of the ComfyUI web UI.
- Drive the canvas from ComfyUI API workflow JSON.
- Support import, visual display, basic node dragging, selected-node property editing, workflow execution, status display, and result preview.
- Deeply edit only common GrsAI workflow nodes in the first version.
- Preserve unknown workflow nodes as generic node cards and keep their original JSON intact.
- Add a backend ComfyUI API adapter for health checks, object metadata, image upload, prompt submission, history polling, image proxying, and queue/status handling.
- Add a local ComfyUI runtime manager that can install/update/start/stop/check a local ComfyUI checkout and the ComfyUI-GrsAI custom node.
- Support remote ComfyUI URLs as an alternative to the managed local runtime.

**Non-Goals**

- Do not vendor the full ComfyUI source tree into the MatchDrawer Git repository.
- Do not reimplement ComfyUI's execution engine, plugin loader, model manager, or queue executor.
- Do not attempt a full clone of the ComfyUI frontend in the first version.
- Do not support unrestricted editing of every possible custom node schema in the first version.
- Do not implement a full plugin marketplace or ComfyUI Manager replacement.
- Do not replace the existing 图像生成, GPT 画图, or PaperBanana pages.

**Current State**

- MatchDrawer is a Flask plus vanilla JavaScript app with existing left navigation, provider key storage, image generation pages, and PaperBanana integration.
- Existing image generation flows are routed through local backend APIs rather than direct browser calls.
- The project already stores generated job artifacts under ignored data directories.
- ComfyUI exposes built-in HTTP and WebSocket routes for `/prompt`, `/history/{prompt_id}`, `/view`, `/upload/image`, `/object_info`, `/queue`, `/system_stats`, and `/ws`.
- ComfyUI-GrsAI is a ComfyUI custom-node package. Its README describes support for text-to-image, image-to-image, multi-image fusion, batch generation, Nano Banana models, aspect ratio controls, image size controls, and GrsAI API key configuration.

**Chosen Approach**

Use a **Workflow JSON driven lightweight node canvas**.

The frontend imports an API-format ComfyUI workflow JSON, renders the workflow as nodes and connections, lets users edit known GrsAI node inputs in a focused property panel, and submits the updated JSON to the backend. The backend forwards the workflow to a configured ComfyUI instance and normalizes ComfyUI queue/history/image responses for the frontend.

This gives the user a ComfyUI-like experience without copying the whole ComfyUI frontend or rewriting the execution engine.

**Alternatives Considered**

1. Embed real ComfyUI through iframe or reverse proxy
   - Pros: fastest way to expose the exact ComfyUI UI.
   - Cons: weak product integration, harder authentication/proxy handling, and less control over MatchDrawer-specific workflows.

2. Build a full arbitrary workflow editor
   - Pros: closer to full ComfyUI behavior.
   - Cons: requires dynamic schema editing, complex connection validation, context menus, shortcuts, node search, groups, and plugin edge cases.

3. Template-only form workbench
   - Pros: fastest reliable product path.
   - Cons: not close enough to the user's desired ComfyUI interface.

The chosen approach is the middle path: a real node canvas for common GrsAI workflows, with unknown-node preservation for safety.

**Frontend Design**

The new page uses the existing MatchDrawer shell and left navigation.

Primary regions:

- Left app sidebar: existing MatchDrawer navigation plus **生图工作台**.
- Workbench toolbar: ComfyUI connection status, import workflow, save template, run, stop, and refresh status actions.
- Node library rail: GrsAI common nodes and template shortcuts.
- Canvas: pan/zoom surface showing imported workflow nodes and links.
- Property panel: selected node editor with dedicated controls for known GrsAI nodes and raw JSON preview for unknown nodes.
- Bottom run panel: queue status, current executing node, logs/errors, prompt id, and generated result thumbnails.

First-version interactions:

- Import API-format workflow JSON.
- Render node cards from workflow node IDs and `class_type`.
- Render links from workflow input references.
- Drag nodes and persist their UI positions separately from execution inputs.
- Select a node and edit supported input fields.
- Preserve unsupported input fields and unknown node JSON without mutation.
- Upload reference images through the backend and bind returned ComfyUI filenames to workflow inputs.
- Submit workflow to ComfyUI.
- Poll history and optionally subscribe to WebSocket progress when available.
- Preview/download output images through the MatchDrawer backend proxy.

Known GrsAI node editing targets:

- Prompt / negative prompt text fields where present.
- Model selector for GrsAI-supported models such as GPT Image, Flux, Nano Banana, and Nano Banana Pro variants when discoverable.
- Aspect ratio selector.
- Image size selector for Nano Banana Pro / Pro VT style nodes.
- Seed, steps, guidance/cfg, batch count, and related common generation parameters when present in the workflow JSON.
- Reference image slots for image-to-image and multi-image fusion workflows.

Unknown node behavior:

- Display as a generic card with `class_type`, node ID, and input count.
- Do not provide deep editing controls.
- Preserve original JSON through import, save, and submit.
- Surface node-level validation errors returned by ComfyUI.

**Backend Design**

Add a ComfyUI service layer and API routes under `/api/comfyui`.

Proposed routes:

- `GET /api/comfyui/status`
  - Returns configured mode, base URL, reachability, `/system_stats` summary, queue summary, and whether object info can be loaded.

- `POST /api/comfyui/config`
  - Saves local/remote mode, remote base URL, and runtime preferences.

- `GET /api/comfyui/object-info`
  - Proxies ComfyUI `/object_info` and caches a compact version for frontend node recognition.

- `POST /api/comfyui/workflows/import`
  - Accepts workflow JSON, validates that it looks like ComfyUI API format, extracts nodes/connections, and returns a normalized canvas model.

- `POST /api/comfyui/upload-image`
  - Accepts image files or data URLs, forwards to ComfyUI `/upload/image`, and returns ComfyUI filename/subfolder/type metadata.

- `POST /api/comfyui/prompt`
  - Accepts edited workflow JSON, optional client ID, and run metadata; posts to ComfyUI `/prompt`.

- `GET /api/comfyui/history/<prompt_id>`
  - Proxies ComfyUI `/history/{prompt_id}` and normalizes output image references.

- `GET /api/comfyui/view`
  - Proxies ComfyUI `/view` with filename, subfolder, and type parameters.

- `POST /api/comfyui/queue`
  - Optional first-version queue controls for clear/interrupt when safe.

Backend responsibilities:

- Enforce login on all routes.
- Keep browser clients from calling arbitrary local URLs directly.
- Normalize and validate ComfyUI base URLs.
- Time out upstream calls with readable errors.
- Store local runtime state under ignored project data/runtime directories.
- Keep workflow templates and user workflow metadata separate from generated outputs.

**Local ComfyUI Runtime Manager**

The project should manage a local ComfyUI runtime without committing ComfyUI source code.

Suggested ignored paths:

- `data/comfyui/runtime/` for the local ComfyUI checkout and Python environment.
- `data/comfyui/workflows/` for user-imported workflow copies and templates.
- `data/comfyui/jobs/` for local run metadata.

Runtime manager functions:

- Check whether local ComfyUI exists.
- Install ComfyUI into the runtime directory.
- Install or update `https://github.com/31702160136/ComfyUI-GrsAI.git` under `custom_nodes/`.
- Install Python dependencies into the ComfyUI environment.
- Write or update the ComfyUI-GrsAI `.env` file with the GrsAI API key when explicitly configured.
- Start ComfyUI on a configured host/port, defaulting to `127.0.0.1:8188`.
- Stop a managed ComfyUI process.
- Detect unmanaged ComfyUI already listening on the configured port.
- Report runtime state in the UI.

Security boundary:

- Do not automatically download or install ComfyUI without a visible user action.
- Do not expose API keys in frontend state or logs.
- Store GrsAI keys through the existing encrypted API key service where possible; if a ComfyUI-GrsAI `.env` file must be written, make that an explicit local-runtime action.
- Keep runtime directories ignored by Git.

**Data Flow**

1. User opens **生图工作台**.
2. Frontend calls `GET /api/comfyui/status`.
3. If no ComfyUI is connected, the page offers:
   - configure remote URL, or
   - install/start managed local ComfyUI.
4. User imports a ComfyUI API workflow JSON or chooses a bundled GrsAI starter template.
5. Backend parses the workflow into normalized canvas nodes and links.
6. Frontend renders the node canvas.
7. User edits known GrsAI node inputs in the property panel.
8. User uploads reference images if needed.
9. Frontend submits edited workflow JSON to `/api/comfyui/prompt`.
10. Backend posts to ComfyUI `/prompt`.
11. Frontend polls `/api/comfyui/history/<prompt_id>` or receives WebSocket progress.
12. Backend normalizes output file references.
13. Frontend displays output thumbnails through `/api/comfyui/view`.

**Error Handling**

User-facing errors should be specific and actionable:

- ComfyUI is not running.
- Configured ComfyUI URL is unreachable.
- ComfyUI returned invalid JSON.
- Workflow is not API-format JSON.
- Workflow validation failed in ComfyUI.
- ComfyUI-GrsAI nodes are missing from `/object_info`.
- GrsAI API key is missing from the managed ComfyUI runtime.
- Reference image upload failed.
- Prompt submission failed.
- History not ready yet.
- Output file is missing or cannot be proxied.
- Managed runtime install/start/stop failed.

For ComfyUI node validation failures, preserve the `node_errors` payload and show it beside the affected node when node IDs can be matched.

**Testing**

Backend tests:

- Status endpoint returns disconnected state when ComfyUI is unreachable.
- Status endpoint normalizes a reachable ComfyUI response.
- Workflow import accepts valid API workflow JSON.
- Workflow import rejects invalid or UI-only workflow JSON with a readable error.
- Unknown nodes are preserved in normalized output.
- Known GrsAI nodes are recognized by `class_type` or object-info metadata.
- Prompt submission sends the edited workflow to `/prompt`.
- History normalization extracts output image references.
- Image proxy forwards filename/subfolder/type safely.
- Runtime manager reports missing, installed, running, stopped, and unmanaged-running states.

Frontend/static tests:

- Sidebar includes **生图工作台**.
- Page config and i18n include the new page.
- Node canvas renders sample GrsAI workflow nodes and links.
- Property panel edits known node inputs without deleting unknown fields.
- Unknown nodes render as generic cards.
- Run button uses backend ComfyUI routes, not direct ComfyUI browser URLs.

Manual/browser verification:

- Open the app and verify the new page is reachable from the left sidebar.
- Confirm disconnected ComfyUI state is clear.
- Import a sample GrsAI API workflow.
- Edit prompt/model/aspect/image size.
- Run against a live ComfyUI instance.
- Confirm output images appear and download.
- Stop/start managed local ComfyUI if enabled in the environment.

**Implementation Notes**

- Use existing Flask blueprint patterns under `src/routes/api_routes.py` or a new route module if the file grows too large.
- Use a dedicated `src/services/comfyui_service.py` for upstream ComfyUI HTTP calls.
- Use a separate `src/services/comfyui_runtime_service.py` for local install/start/stop state.
- Keep canvas JavaScript isolated in a new file such as `static/js/comfyui-workbench.js`.
- Keep CSS in the existing app CSS structure unless a dedicated `comfyui-workbench.css` becomes cleaner.
- Prefer polling history first; add WebSocket progress after the basic prompt/history/view loop is reliable.
- Store starter workflow templates as compact JSON fixtures under a tracked templates/integrations directory only if they are small and license-compatible.
- Do not commit generated images, ComfyUI runtime files, Python virtual environments, or downloaded model artifacts.

**First-Version Implementation Decisions**

- Use `data/comfyui/runtime/` for the managed local ComfyUI runtime because the existing repository already ignores `data/**`.
- Expose local ComfyUI install/start/stop/check actions in the UI, but every download/install/start action must be triggered by an explicit user click.
- Bundle a small set of starter GrsAI API workflow templates if they are compact and license-compatible; users can still import their own workflow JSON.
- Make polling `/history/{prompt_id}` the required first-version progress mechanism. Add `/ws` progress after prompt submission, history polling, and image proxying are already reliable.

**References**

- ComfyUI server routes: <https://docs.comfy.org/development/comfyui-server/comms_routes>
- ComfyUI-GrsAI repository and README: <https://github.com/31702160136/ComfyUI-GrsAI>

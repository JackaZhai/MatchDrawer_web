# Unified Image Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge "图像生成" and "GPT 画图" into one page with one prompt input, selectable `nano-banana-pro` / `GPT Image` models, and homepage drawing history.

**Architecture:** Keep the existing Flask template and plain JavaScript architecture. Reuse the current GPT Image module by adding a small public API and rendering it inside the existing image-generation page instead of keeping a separate page/nav item. Add a small frontend-only unified history adapter in `static/js/app.js`.

**Tech Stack:** Flask/Jinja templates, vanilla JavaScript, localStorage, existing CSS.

---

### Task 1: Template Merge

**Files:**
- Modify: `templates/index.html`

- [ ] Remove the `data-page="gpt-image"` sidebar item.
- [ ] Add a unified image model selector to `#page-image-generation` with `nano-banana-pro` and `GPT Image`.
- [ ] Add a `gptImageUnifiedPanel` area inside `#page-image-generation` that contains the existing GPT controls and gallery.
- [ ] Keep the old `#page-gpt-image` section removed to prevent duplicate page routing.

### Task 2: Unified History UI

**Files:**
- Modify: `templates/index.html`
- Modify: `static/js/app.js`
- Modify: `static/css/app.css`

- [ ] Replace homepage emphasis with a `recentImageHistoryGrid` section.
- [ ] Add helpers in `app.js`:
  - `loadUnifiedImageHistory()`
  - `saveUnifiedImageHistory(records)`
  - `addUnifiedImageHistory(record)`
  - `refreshImageHistory()`
- [ ] Import existing `gpt_image_tasks_v1` into the unified history view without deleting the original GPT storage.
- [ ] Render empty, running, failed, and completed history cards.

### Task 3: Generation Routing

**Files:**
- Modify: `static/js/app.js`
- Modify: `static/js/gpt-image.js`

- [ ] In `app.js`, add image mode state based on `#unifiedImageModelSelect`.
- [ ] If model is `nano-banana-pro`, run existing `generateImage('generic')`.
- [ ] If model is `GPT Image`, call a new `window.GPTImage.submitFromUnifiedPage()` method.
- [ ] In `gpt-image.js`, expose a public method that reads `#promptInput`, syncs GPT params, submits GPT generation, and records unified history on completion/failure.

### Task 4: Styling And Responsive Polish

**Files:**
- Modify: `static/css/app.css`
- Modify: `static/css/main.css` only if existing selectors are insufficient.

- [ ] Make the unified page use the brandy/neutral palette, no gradients.
- [ ] Ensure the model-specific panel fills the available width in portrait and desktop.
- [ ] Keep bottom navigation centered in portrait.
- [ ] Prevent homepage history text and thumbnails from overlapping.

### Task 5: Verification

**Commands:**
- `node --check static/js/app.js`
- `node --check static/js/gpt-image.js`
- `python -m unittest tests.test_auth_management_assets tests.test_admin_user_routes tests.test_auth_api tests.test_auth_management_api -v`
- `git diff --check`

**Expected:** All commands pass. Then verify the local app shows one "图像生成" nav entry and no separate "GPT 画图" entry.

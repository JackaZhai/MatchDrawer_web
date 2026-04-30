# Generation And PaperBanana Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split generic image generation and the PaperBanana workflow into two separate left-nav pages.

**Architecture:** Keep the backend API unchanged and separate the UI at the template and client-state layer. Generic generation keeps only basic image inputs, while PaperBanana owns workflow configuration and stage monitoring. Regression coverage stays at the rendered-page level.

**Tech Stack:** Flask, Jinja2 templates, vanilla JavaScript, CSS, Python `unittest`

---

### Task 1: Lock The New Page Separation In Smoke Tests

**Files:**
- Modify: `tests/test_brand_surfaces.py`
- Test: `tests/test_brand_surfaces.py`

- [ ] **Step 1: Write the failing assertions**

Add assertions so `/` contains both `图像生成` and `PaperBanana`, and the rendered HTML keeps `PaperBanana 专业工作流` separate from the generic generation label.

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `./.venv/bin/python -m unittest tests.test_brand_surfaces -v`

- [ ] **Step 3: Implement the minimal UI split**

Update the template and client code so the generic page no longer embeds the workflow controls, and a new `PaperBanana` page contains them.

- [ ] **Step 4: Run the smoke test to verify it passes**

Run: `./.venv/bin/python -m unittest tests.test_brand_surfaces -v`

### Task 2: Wire Two Separate Frontend Entry Points

**Files:**
- Modify: `templates/index.html`
- Modify: `static/js/app.js`
- Modify: `static/css/app.css`
- Test: `tests/test_brand_surfaces.py`

- [ ] **Step 1: Split navigation and page sections**
- [ ] **Step 2: Keep generic generation submission on the image page**
- [ ] **Step 3: Move PaperBanana-only controls and status UI into the new page**
- [ ] **Step 4: Run regression tests**

Run: `./.venv/bin/python -m unittest tests.test_brand_surfaces tests.test_deploy_branding tests.test_user_model -v`

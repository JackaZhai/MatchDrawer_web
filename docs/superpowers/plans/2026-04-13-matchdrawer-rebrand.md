# MatchDrawer Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebrand the Flask app from `SCIdrawer` to `MatchDrawer`, broaden the product positioning beyond paper figures, and keep the full `PaperBanana` workflow directly visible and functional.

**Architecture:** Lock the new brand and positioning with small smoke tests first, then update the Jinja templates, JavaScript copy, docs, and deployment assets to match the new product name. Preserve the existing `PaperBanana` routes, service classes, and workflow semantics so the rebrand changes presentation and deployment naming without destabilizing the generation pipeline.

**Tech Stack:** Flask, Jinja2 templates, vanilla JavaScript, CSS, Python `unittest`, Bash deployment scripts, systemd, nginx

---

## File Map

- Create: `tests/__init__.py` — make the `tests` package importable for `python -m unittest`.
- Create: `tests/test_brand_surfaces.py` — smoke tests for `/login`, `/`, and `/manual` brand text and positioning.
- Create: `tests/test_deploy_branding.py` — checks for renamed deploy assets, updated path examples, and removal of old `SCIdrawer` branding strings.
- Modify: `app.py:1-4` — update the app-level docstring branding.
- Modify: `templates/index.html:6-35`, `templates/index.html:88-124`, `templates/index.html:172-176`, `templates/index.html:207-257`, `templates/index.html:293-305`, `templates/index.html:492-500` — change visible brand text, general-use prompt examples, and visible `PaperBanana` wording.
- Modify: `templates/login.html:6-7`, `templates/login.html:199-228` — change title, hero copy, and login notes to `MatchDrawer`.
- Modify: `templates/manual.html:6-11`, `templates/manual.html:103-151`, `templates/manual.html:191-271` — broaden help copy beyond scientific figures while keeping `PaperBanana` guidance visible.
- Modify: `static/js/app.js:1-3`, `static/js/app.js:143-172`, `static/js/app.js:221-242`, `static/js/app.js:1694-1697` — update brand comments, runtime log text, and `PaperBanana` status copy.
- Modify: `static/css/app.css:1-3` — rename the file header comment.
- Modify: `static/css/design-system.css:1-3` — rename the file header comment.
- Modify: `README.md:1-79` — rename the product, update deployment paths, and switch deploy file references to `matchdrawer.*`.
- Modify: `.env.example:1-32` — rename service comments and example `PAPERBANANA_ROOT` path.
- Modify: `scripts/deploy_linux.sh:4-24` — update default app path, deploy filenames, and systemd unit name.
- Rename: `deploy/systemd/scidrawer.service` -> `deploy/systemd/matchdrawer.service`
- Rename: `deploy/nginx/scidrawer.conf` -> `deploy/nginx/matchdrawer.conf`

### Task 1: Lock MatchDrawer Branding On Public Pages

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_brand_surfaces.py`
- Modify: `app.py:1-4`
- Modify: `templates/index.html:6-35`, `templates/index.html:88-124`, `templates/index.html:172-176`, `templates/index.html:207-257`, `templates/index.html:293-305`
- Modify: `templates/login.html:6-7`, `templates/login.html:199-228`
- Modify: `templates/manual.html:6-11`, `templates/manual.html:103-151`, `templates/manual.html:191-271`
- Modify: `static/js/app.js:1-3`, `static/js/app.js:143-172`, `static/js/app.js:221-242`, `static/js/app.js:1694-1697`
- Modify: `static/css/app.css:1-3`
- Modify: `static/css/design-system.css:1-3`
- Test: `tests/test_brand_surfaces.py`

- [x] **Step 1: Write the failing smoke tests**

```python
# tests/__init__.py
"""Test package for MatchDrawer smoke coverage."""
```

```python
# tests/test_brand_surfaces.py
import importlib
import os
import tempfile
import unittest
from pathlib import Path


def build_test_client():
    tmpdir = tempfile.TemporaryDirectory()
    data_dir = Path(tmpdir.name) / "data"
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["DB_PATH"] = str(data_dir / "app.db")
    os.environ["APP_SECRET_KEY"] = "test-secret"

    import src.config as config_module
    import src.services.auth as auth_module
    import src.services.database as database_module

    config_module._config_instance = None
    auth_module._auth_service = None
    database_module.db_manager = None

    import app as app_module

    app_module = importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return tmpdir, app_module.app.test_client()


class BrandSurfacesTest(unittest.TestCase):
    def setUp(self):
        self.previous_env = {
            key: os.environ.get(key)
            for key in ("DATA_DIR", "DB_PATH", "APP_SECRET_KEY")
        }
        self.tmpdir, self.client = build_test_client()

    def tearDown(self):
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_login_page_uses_matchdrawer_brand(self):
        response = self.client.get("/login")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("MatchDrawer", html)
        self.assertIn("通用画图平台", html)
        self.assertIn("PaperBanana 工作流", html)

    def test_dashboard_promotes_general_diagram_work_and_visible_paperbanana(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("MatchDrawer", html)
        self.assertIn("架构图模板", html)
        self.assertIn("PaperBanana 专业工作流", html)

    def test_manual_mentions_general_drawing_scope(self):
        response = self.client.get("/manual")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("MatchDrawer 使用指南", html)
        self.assertIn("论文图、流程图、架构图、机制图", html)
        self.assertIn("PaperBanana 专业工作流", html)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run the smoke tests to verify they fail**

Run: `python -m unittest tests.test_brand_surfaces -v`

Expected: FAIL in all three tests, with assertion errors for missing `MatchDrawer`, missing `架构图模板`, and missing `PaperBanana 专业工作流`.

- [x] **Step 3: Implement the minimal branding and positioning changes**

```python
# app.py
"""
MatchDrawer - AI Drawing Platform
通用画图与专业工作流网页版本
"""
```

```html
<!-- templates/login.html -->
<title>登录 | MatchDrawer</title>

<section class="login-hero">
    <div>
        <img src="{{ url_for('static', filename='app-icon.png') }}" alt="MatchDrawer">
        <h1>MatchDrawer</h1>
        <p>面向论文图、流程图、架构图、机制图与产品示意图的通用画图平台，保留完整的 PaperBanana 专业工作流。</p>
    </div>
    <div class="login-notes">
        <div class="login-note">支持通用图像生成与 PaperBanana 工作流。</div>
        <div class="login-note">首次启动会自动创建默认账户，便于本地调试、部署迁移与工作流验证。</div>
    </div>
</section>
<section class="login-panel">
    <h2>登录</h2>
    <p>登录后进入 MatchDrawer 控制台，可直接开始通用画图，或切换到 PaperBanana 进行多阶段专业生成。</p>
</section>
```

```html
<!-- templates/index.html -->
<title>控制台 | MatchDrawer</title>

<div class="brand-logo">
    <img src="{{ url_for('static', filename='app-icon.png') }}" alt="MatchDrawer Logo" class="brand-logo-image">
</div>
<div class="brand-text">
    <div class="brand-title">MatchDrawer</div>
</div>

<div class="workflow-item">
    <div class="workflow-index">01</div>
    <div>
        <div class="workflow-title">先定义输出类型</div>
        <div class="workflow-desc">先明确流程图、架构图、机制图、对比图或产品示意图，减少提示词歧义。</div>
    </div>
</div>
<div class="workflow-item">
    <div class="workflow-index">02</div>
    <div>
        <div class="workflow-title">使用模板快速起稿</div>
        <div class="workflow-desc">先用通用模板起稿，再根据业务或科研语境补充细节。</div>
    </div>
</div>
<div class="workflow-item">
    <div class="workflow-index">03</div>
    <div>
        <div class="workflow-title">复杂任务切换专业工作流</div>
        <div class="workflow-desc">需要多阶段规划、检索和审图时，直接启用 PaperBanana 专业工作流。</div>
    </div>
</div>
<div class="prompt-chips">
    <button type="button" class="prompt-chip" data-fill-prompt="Design a user permission flowchart for a SaaS workspace. Show admin, editor, and viewer paths after login. Use a clean white background, clear arrows, and concise English labels.">
        权限流程图模板
    </button>
    <button type="button" class="prompt-chip" data-fill-prompt="Create a system architecture diagram for an AI assistant platform with web client, API gateway, worker queue, vector store, and monitoring. Use balanced spacing, simple color blocks, and English labels.">
        架构图模板
    </button>
    <button type="button" class="prompt-chip" data-fill-prompt="Create a mechanism diagram for oxidative stress in neuronal aging. Include mitochondria, ROS accumulation, DNA damage response, and downstream inflammation pathways. Use a clean white background, journal-ready style, English labels, and clear directional arrows.">
        机制图模板
    </button>
</div>

<textarea id="promptInput" class="form-textarea prompt-editor"
          placeholder="例如：设计一张权限流程图，展示用户登录后的角色分流逻辑；或绘制一个 AI 系统架构图，标出客户端、网关、任务队列和模型服务之间的关系"
          rows="6"></textarea>

<label class="form-label">PaperBanana 专业工作流</label>
<div class="parameter-hint workflow-summary" id="generationWorkflowSummary">
    当前流程预览：PaperBanana 完整流程（含审图与评估）
</div>
<div class="parameter-hint">通用图像任务可直接生成；复杂结构化任务建议使用 PaperBanana。</div>
<div class="paper-status-message" id="paperStageMessage">提交任务后会显示 PaperBanana 专业工作流的当前处理阶段。</div>
```

```html
<!-- templates/manual.html -->
<title>用户手册 | MatchDrawer</title>

<div class="brand-logo">
    <img src="{{ url_for('static', filename='app-icon.png') }}" alt="MatchDrawer Logo" class="brand-logo-image">
</div>
<div class="brand-text">
    <div class="brand-title">MatchDrawer</div>
</div>
<div class="page-title">
    <h1>用户手册</h1>
    <p class="page-subtitle">MatchDrawer 使用指南</p>
</div>

<section class="manual-section" id="image-generation">
    <h3>图像生成</h3>
    <div class="manual-list">
        <p>支持文本提示词 + 参数控制，并可上传参考图。MatchDrawer 可用于论文图、流程图、架构图、机制图、对比图和产品示意图；对于复杂、多阶段、需要规划与审图的任务，可直接启用 PaperBanana 专业工作流。</p>

        <h4 style="margin-top: 1.5rem; margin-bottom: 0.5rem; color: var(--color-text-primary);">4.2 通用画图指南</h4>
        <p>为了获得结构化、可复用的图像结果，请把提示词写成简短设计说明，先交代目标图类型，再补充布局、风格和标签要求。</p>
        <p>一个实用的 MatchDrawer Prompt，通常需要包含以下要素：</p>
        <ul style="margin-left: 1.5rem; margin-bottom: 1rem;">
            <li><strong>图类型</strong>：流程图 / 架构图 / 机制图 / 对比图 / 示意图</li>
            <li><strong>核心元素</strong>：哪些模块、角色、设备或概念必须出现</li>
            <li><strong>风格要求</strong>：简洁、技术感、可汇报、可论文使用或品牌化展示</li>
            <li><strong>布局关系</strong>：箭头、层级、时序、并列或对照关系</li>
            <li><strong>限制条件</strong>：避免艺术化装饰、无关背景和多余纹理</li>
        </ul>
        <p>当任务需要检索参考、分阶段规划、风格修正和审图回路时，优先选择 PaperBanana 专业工作流。</p>
    </div>
</section>
```

```javascript
// static/js/app.js
/* ============================================
   MatchDrawer - 主应用脚本
   ============================================ */
'paper.message.idle_hint': '提交任务后会显示 PaperBanana 专业工作流当前处理阶段。',
'paper.message.task_submitted_waiting': '任务已提交，等待 PaperBanana 专业工作流启动...',
'paper.message.idle_hint': 'PaperBanana professional workflow stages will appear after submitting a task.',
'paper.message.task_submitted_waiting': 'Task submitted. Waiting for the PaperBanana professional workflow to start...',
console.log("初始化 MatchDrawer 应用...");
```

```css
/* static/css/app.css */
/* ============================================
   MatchDrawer - 应用特定样式
   ============================================ */
```

```css
/* static/css/design-system.css */
/* ============================================
   MatchDrawer - 现代设计系统
   ============================================ */
```

- [x] **Step 4: Run the smoke tests to verify they pass**

Run: `python -m unittest tests.test_brand_surfaces -v`

Expected: PASS with `Ran 3 tests` and `OK`.

- [x] **Step 5: Commit the public rebrand changes**

```bash
git add tests/__init__.py tests/test_brand_surfaces.py app.py templates/index.html templates/login.html templates/manual.html static/js/app.js static/css/app.css static/css/design-system.css
git commit -m "feat: rebrand public UI as MatchDrawer"
```

### Task 2: Rename Deploy Assets And Documentation

**Files:**
- Create: `tests/test_deploy_branding.py`
- Modify: `README.md:1-79`
- Modify: `.env.example:1-32`
- Modify: `scripts/deploy_linux.sh:4-24`
- Modify: `templates/index.html:492-500`
- Rename: `deploy/systemd/scidrawer.service` -> `deploy/systemd/matchdrawer.service`
- Rename: `deploy/nginx/scidrawer.conf` -> `deploy/nginx/matchdrawer.conf`
- Test: `tests/test_deploy_branding.py`

- [x] **Step 1: Write the failing deploy and docs checks**

```python
# tests/test_deploy_branding.py
import unittest
from pathlib import Path


class DeployBrandingTest(unittest.TestCase):
    def test_renamed_deploy_assets_exist(self):
        self.assertTrue(Path("deploy/systemd/matchdrawer.service").exists())
        self.assertTrue(Path("deploy/nginx/matchdrawer.conf").exists())

    def test_docs_and_scripts_use_matchdrawer_paths(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        env_example = Path(".env.example").read_text(encoding="utf-8")
        script = Path("scripts/deploy_linux.sh").read_text(encoding="utf-8")
        systemd = Path("deploy/systemd/matchdrawer.service").read_text(encoding="utf-8")
        nginx = Path("deploy/nginx/matchdrawer.conf").read_text(encoding="utf-8")

        self.assertIn("MatchDrawer Web", readme)
        self.assertIn("/opt/matchdrawer/MatchDrawer_web", readme)
        self.assertIn("deploy/systemd/matchdrawer.service", readme)
        self.assertIn("deploy/nginx/matchdrawer.conf", readme)
        self.assertIn("# MatchDrawer 服务配置", env_example)
        self.assertIn("/opt/matchdrawer/MatchDrawer_web/integrations/PaperBanana", env_example)
        self.assertIn('APP_DIR="${APP_DIR:-/opt/matchdrawer/MatchDrawer_web}"', script)
        self.assertIn("sudo systemctl enable --now matchdrawer", script)
        self.assertIn("Description=MatchDrawer Web", systemd)
        self.assertIn("WorkingDirectory=/opt/matchdrawer/MatchDrawer_web", systemd)
        self.assertIn("alias /opt/matchdrawer/MatchDrawer_web/static/", nginx)

    def test_old_scidrawer_brand_is_removed_from_tracked_files(self):
        tracked_files = [
            Path("README.md"),
            Path(".env.example"),
            Path("scripts/deploy_linux.sh"),
            Path("app.py"),
            Path("templates/index.html"),
            Path("templates/login.html"),
            Path("templates/manual.html"),
            Path("static/js/app.js"),
            Path("static/css/app.css"),
            Path("static/css/design-system.css"),
            Path("deploy/systemd/matchdrawer.service"),
            Path("deploy/nginx/matchdrawer.conf"),
        ]

        for path in tracked_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("scidrawer", text.lower(), path.as_posix())


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run the deploy and docs checks to verify they fail**

Run: `python -m unittest tests.test_deploy_branding -v`

Expected: FAIL because `deploy/systemd/matchdrawer.service` and `deploy/nginx/matchdrawer.conf` do not exist yet, and `README.md` / `.env.example` still reference `scidrawer`.

- [x] **Step 3: Implement the deploy rename and documentation updates**

```markdown
# README.md
# MatchDrawer Web

`MatchDrawer_web` is the web-first repository for MatchDrawer. It contains the Flask-based browser console for general diagram work, while preserving the full `PaperBanana` professional workflow for complex structured generation tasks.

## Run Locally

python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py

## Deploy On Linux

git clone <your-repo-url> /opt/matchdrawer/MatchDrawer_web
cd /opt/matchdrawer/MatchDrawer_web
/usr/bin/python3.14 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

Deployment templates:

- systemd: [deploy/systemd/matchdrawer.service](deploy/systemd/matchdrawer.service)
- nginx: [deploy/nginx/matchdrawer.conf](deploy/nginx/matchdrawer.conf)
- gunicorn config: [gunicorn.conf.py](gunicorn.conf.py)
- helper script: [scripts/deploy_linux.sh](scripts/deploy_linux.sh)

Notes:

- Keep `integrations/PaperBanana` present on the server.
- Reverse proxy `/static/` with nginx when possible.
- For production, do not run `python app.py` directly.
```

```dotenv
# .env.example
# MatchDrawer 服务配置
# Linux 服务器部署时，可复制此文件为 .env 并填写实际值
APP_SECRET_KEY=your-very-secure-secret-key-change-this
AUTH_USERNAME=admin
AUTH_PASSWORD=banana123
NANO_BANANA_API_KEY=your-actual-api-key-here
NANO_BANANA_HOST=https://grsaiapi.com
PORT=8788
DATA_DIR=data
DB_PATH=data/app.db
MAX_LOGIN_ATTEMPTS=5
LOCK_MINUTES=10
MAX_REFERENCE_IMAGES=3
MAX_REFERENCE_IMAGE_BYTES=5242880
# PAPERBANANA_ROOT=/opt/matchdrawer/MatchDrawer_web/integrations/PaperBanana
```

```bash
# scripts/deploy_linux.sh
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/matchdrawer/MatchDrawer_web}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3.14}"

cd "$APP_DIR"

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p data logs

echo "Deployment dependencies installed."
echo "Next steps:"
echo "1. Edit $APP_DIR/.env"
echo "2. Install deploy/systemd/matchdrawer.service to /etc/systemd/system/"
echo "3. Install deploy/nginx/matchdrawer.conf to your nginx sites config"
echo "4. Start with: sudo systemctl enable --now matchdrawer"
```

```ini
# deploy/systemd/matchdrawer.service
[Unit]
Description=MatchDrawer Web
After=network.target

[Service]
Type=simple
User=matchdrawer
Group=matchdrawer
WorkingDirectory=/opt/matchdrawer/MatchDrawer_web
EnvironmentFile=/opt/matchdrawer/MatchDrawer_web/.env
ExecStart=/opt/matchdrawer/MatchDrawer_web/.venv/bin/gunicorn -c /opt/matchdrawer/MatchDrawer_web/gunicorn.conf.py app:app
Restart=always
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

```nginx
# deploy/nginx/matchdrawer.conf
server {
    listen 80;
    server_name _;

    client_max_body_size 20m;

    location /static/ {
        alias /opt/matchdrawer/MatchDrawer_web/static/;
        access_log off;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8788;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 60;
    }
}
```

```html
<!-- templates/index.html -->
<div class="settings-name" data-i18n="settings.repo.name">项目仓库</div>
<div class="settings-description">
    <a class="settings-link" href="https://github.com/JackaZhai/MatchDrawer_web" target="_blank" rel="noopener noreferrer">
        <i class="fab fa-github" aria-hidden="true"></i>
        <span>https://github.com/JackaZhai/MatchDrawer_web</span>
    </a>
</div>
```

- [x] **Step 4: Run the full regression checks**

Run: `python -m unittest tests.test_brand_surfaces tests.test_deploy_branding -v`

Expected: PASS with `Ran 6 tests` and `OK`.

Run: `rg -n "SCIdrawer|scidrawer" README.md .env.example app.py templates static/js static/css scripts deploy`

Expected: no output.

- [x] **Step 5: Commit the deploy and docs rename**

```bash
git add README.md .env.example scripts/deploy_linux.sh templates/index.html tests/test_deploy_branding.py deploy/systemd/matchdrawer.service deploy/nginx/matchdrawer.conf
git rm deploy/systemd/scidrawer.service deploy/nginx/scidrawer.conf
git commit -m "chore: rename deploy assets for MatchDrawer"
```

## Operational Follow-Up

These steps are intentionally outside the git commit flow because the repository root path and remote URL are not tracked content:

1. Rename the local checkout after the code changes and tests pass.

```bash
cd ..
mv SCIdrawer_web MatchDrawer_web
```

2. If the GitHub repository is renamed too, update the local remote immediately after reopening the renamed checkout.

```bash
cd MatchDrawer_web
git remote set-url origin https://github.com/JackaZhai/MatchDrawer_web.git
```

3. Re-open the terminal, editor, and deployment scripts from `MatchDrawer_web` before continuing with releases or server rollout.

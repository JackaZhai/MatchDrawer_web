import json
import subprocess
import textwrap
import unittest
from pathlib import Path


class ComfyUIWorkbenchAssetsTest(unittest.TestCase):
    ASSET_PATHS = (
        "templates/index.html",
        "static/js/app.js",
        "static/js/comfyui-workbench.js",
        "static/css/comfyui-workbench.css",
    )

    def test_sidebar_and_page_shell_exist(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")

        self.assertIn('data-page="image-generation"', html)
        self.assertIn('id="page-image-generation"', html)
        self.assertNotIn('id="unifiedImageModelSelect"', html)
        self.assertIn('id="generationImageModelSelect"', html)
        self.assertIn('<option value="gpt-image-2">GPT Image</option>', html)
        self.assertNotIn('data-page="gpt-image"', html)
        self.assertNotIn('id="page-gpt-image"', html)
        self.assertIn('data-page="comfyui-workbench"', html)
        self.assertIn("生图工作台", html)
        self.assertIn('id="page-comfyui-workbench"', html)
        self.assertIn("js/comfyui-workbench.js", html)
        self.assertIn("css/comfyui-workbench.css", html)

    def test_workbench_and_paperbanana_sidebar_icons_are_distinct(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")

        workbench_nav = html.split('data-page="comfyui-workbench"', 1)[1].split("</a>", 1)[0]
        paperbanana_nav = html.split('data-page="paperbanana"', 1)[1].split("</a>", 1)[0]

        self.assertIn("fa-toolbox", workbench_nav)
        self.assertNotIn("fa-project-diagram", workbench_nav)
        self.assertNotIn("fa-diagram-project", workbench_nav)
        self.assertIn("fa-diagram-project", paperbanana_nav)
        self.assertNotEqual(workbench_nav, paperbanana_nav)

    def test_app_registers_page_config_and_i18n(self):
        app_js = Path("static/js/app.js").read_text(encoding="utf-8")

        self.assertIn("'nav.comfyui_workbench': '生图工作台'", app_js)
        self.assertIn("'page.comfyui_workbench': '生图工作台'", app_js)
        self.assertIn("'comfyui-workbench':", app_js)
        self.assertIn("ComfyUIWorkbench.init", app_js)

    def test_workbench_js_uses_backend_routes_only(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")

        self.assertIn("window.ComfyUIWorkbench", workbench_js)
        self.assertIn("/api/comfyui/status", workbench_js)
        self.assertIn("/api/comfyui/prompt", workbench_js)
        self.assertIn("/api/comfyui/workflows/starter/", workbench_js)
        self.assertIn("/api/comfyui/upload-image", workbench_js)
        self.assertNotIn("127.0.0.1:8188", workbench_js)
        self.assertNotIn("localhost:8188", workbench_js)

    def test_comfyui_workbench_assets_do_not_hardcode_upstream_host(self):
        for asset_path in self.ASSET_PATHS:
            with self.subTest(asset=asset_path):
                content = Path(asset_path).read_text(encoding="utf-8")

                self.assertNotIn("127.0.0.1:8188", content)
                self.assertNotIn("localhost:8188", content)

    def test_css_uses_existing_background_token(self):
        css = Path("static/css/comfyui-workbench.css").read_text(encoding="utf-8")

        self.assertNotIn("--color-bg-main", css)
        self.assertIn("--color-bg-primary", css)

    def test_workbench_node_templates_are_generic(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")
        workbench_shell = html.split('id="page-comfyui-workbench"', 1)[1].split('id="comfyPropertyPanel"', 1)[0]

        self.assertIn('data-template="text-image"', workbench_shell)
        self.assertIn('data-template="image-fusion"', workbench_shell)
        self.assertIn('data-template="batch-generate"', workbench_shell)
        self.assertIn("<span>Text / Image</span>", workbench_shell)
        self.assertNotIn("GrsAI", workbench_shell)
        self.assertNotIn("grsai-", workbench_shell)

    def test_workbench_loads_starter_workflows_from_template_buttons(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")

        self.assertIn("async function loadTemplateWorkflow", workbench_js)
        self.assertIn("API.starterWorkflow(name)", workbench_js)
        self.assertIn("await normalizeWorkflow(payload.workflow, payload.name || name)", workbench_js)
        self.assertIn("DOM.root.querySelectorAll('[data-template]')", workbench_js)
        self.assertIn("loadTemplateWorkflow(button.getAttribute('data-template'))", workbench_js)
        self.assertIn("loadTemplateWorkflow,", workbench_js)

    def test_workbench_js_contains_import_render_and_selection_paths(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")

        self.assertIn("async function importWorkflowFile", workbench_js)
        self.assertIn("function renderCanvas", workbench_js)
        self.assertIn("function renderLinks", workbench_js)
        self.assertIn("function selectNode", workbench_js)
        self.assertIn("comfy-node-card", workbench_js)

    def test_workbench_maps_provider_specific_node_kinds_to_generic_ui(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")
        css = Path("static/css/comfyui-workbench.css").read_text(encoding="utf-8")

        self.assertIn("function nodeKindClass", workbench_js)
        self.assertIn("function nodeKindLabel", workbench_js)
        self.assertIn("Custom Node", workbench_js)
        self.assertNotIn(".comfy-node-grsai", css)
        self.assertNotIn("comfy-node-${escapeHtml(node.kind", workbench_js)
        self.assertNotIn("comfy-node-${nodeKindClass(node.kind)", workbench_js)
        self.assertNotIn("escapeHtml(node.kind || 'unknown')", workbench_js)

    def test_workbench_canvas_layout_handles_large_and_negative_workflows(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")
        css = Path("static/css/comfyui-workbench.css").read_text(encoding="utf-8")

        self.assertIn("function layoutViewport", workbench_js)
        self.assertIn("function normalizeNodePosition", workbench_js)
        self.assertIn("setCanvasDimensions", workbench_js)
        self.assertIn("overflow: auto", css)

    def test_workbench_supports_draggable_nodes_and_port_connections(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")
        css = Path("static/css/comfyui-workbench.css").read_text(encoding="utf-8")

        self.assertIn("function moveNode", workbench_js)
        self.assertIn("function connectNodes", workbench_js)
        self.assertIn("function beginNodeDrag", workbench_js)
        self.assertIn("function handlePortClick", workbench_js)
        self.assertIn("data-port-type", workbench_js)
        self.assertIn("data-input-name", workbench_js)
        self.assertIn("data-output-index", workbench_js)
        self.assertIn("pointerdown", workbench_js)
        self.assertIn("pointermove", workbench_js)
        self.assertIn("pointerup", workbench_js)
        self.assertIn(".comfy-port", css)
        self.assertIn(".comfy-input-port", css)
        self.assertIn(".comfy-output-port", css)
        self.assertIn(".comfy-node-card.is-connecting", css)

    def test_image_tools_keep_independent_model_settings(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")
        app_js = Path("static/js/app.js").read_text(encoding="utf-8")
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")
        gpt_js = Path("static/js/gpt-image.js").read_text(encoding="utf-8")

        self.assertIn('id="comfyImageProviderSelect"', html)
        self.assertIn('id="comfyImageModelInput"', html)
        self.assertIn('id="comfyImageSizeSelect"', html)
        self.assertIn("COMFY_SOURCE_KEY", workbench_js)
        self.assertIn("loadWorkbenchImageSource", workbench_js)

        self.assertNotIn('id="unifiedImageModelSelect"', html)
        self.assertIn('id="generationImageModelSelect"', html)
        self.assertIn('<option value="gpt-image-2">GPT Image</option>', html)
        self.assertIn('id="gptUnifiedParamsPanel"', html)
        self.assertIn('id="gptUnifiedControlsMount"', html)
        self.assertIn('id="gptUnifiedGalleryMount"', html)
        self.assertIn("mountUnifiedGptWorkspace", app_js)
        self.assertIn("syncUnifiedImageMode", app_js)
        self.assertIn("routeUnifiedImageGeneration", app_js)
        self.assertIn("submitFromUnifiedPage", app_js)
        self.assertIn("function isUnifiedGptMode", gpt_js)
        self.assertIn("async function submitFromUnifiedPage", gpt_js)
        self.assertIn('id="paperImageProviderSelect"', html)
        self.assertIn('id="paperImageModelSelect"', html)
        self.assertIn('id="paperImageSizeSelect"', html)
        self.assertIn("paperImageProvider", app_js)
        self.assertIn("paperImageSize", app_js)
        self.assertNotIn("沿用“图像生成”页面", html)

        self.assertNotIn("getCurrentComfyImageSource", app_js)
        self.assertNotIn("notifyComfyImageSource", app_js)
        self.assertNotIn("refreshImageSourceFromImagePage", app_js)
        self.assertNotIn("getCurrentComfyImageSource", workbench_js)
        self.assertNotIn("generationImageProvider", workbench_js)
        self.assertNotIn("generationImageSize", workbench_js)
        self.assertNotIn("getCurrentComfyImageSource", gpt_js)
        self.assertNotIn("generationImageProvider", gpt_js)
        self.assertNotIn("generationImageSize", gpt_js)

    def test_paperbanana_model_selects_are_visible_workflow_controls(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        paper_page = html.split('id="page-paperbanana"', 1)[1].split('id="page-api-keys"', 1)[0]

        self.assertIn('class="form-group paper-model-field"', paper_page)
        self.assertIn('for="generationTextModelSelect"', paper_page)
        self.assertIn('for="paperImageModelSelect"', paper_page)
        self.assertIn("PaperBanana 语言模型", paper_page)
        self.assertIn("PaperBanana 生图模型", paper_page)
        self.assertIn("paper-provider-field", paper_page)
        self.assertNotIn('class="form-group provider-locked-field"', paper_page)
        self.assertIn(".paper-provider-field", css)

    def test_image_generation_completion_scrolls_preview_into_view(self):
        app_js = Path("static/js/app.js").read_text(encoding="utf-8")

        self.assertIn("function scrollGenerationPreviewIntoView", app_js)
        self.assertIn("previewContainer.scrollIntoView", app_js)
        self.assertIn("scrollGenerationPreviewIntoView(finalMode)", app_js)

    def test_image_generation_preview_keeps_visible_height(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")

        self.assertIn(".image-generation .preview-container.preview-container-tall", css)
        self.assertIn("height: auto;", css)
        self.assertIn("min-height: 32rem;", css)
        self.assertNotIn(".image-generation .preview-container {\n  min-height: 0;", css)

    def test_image_generation_action_dock_matches_panel_surface(self):
        css = Path("static/css/app.css").read_text(encoding="utf-8")
        action_dock_sticky = css.split(".action-dock-sticky {", 1)[1].split("}", 1)[0]

        self.assertIn("background: var(--color-bg-surface);", action_dock_sticky)
        self.assertNotIn("background: var(--color-bg-primary);", action_dock_sticky)

    def test_dashboard_start_generation_uses_stable_action_icon(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")
        image_history_card = html.split('class="content-card image-history-card"', 1)[1].split('class="content-card"', 1)[0]

        self.assertIn('data-target="image-generation"', image_history_card)
        self.assertIn('<i class="fas fa-magic"></i>', image_history_card)
        self.assertNotIn('<i class="fas fa-palette"></i>', image_history_card)

    def test_dashboard_does_not_render_secondary_helper_cards(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")
        dashboard_page = html.split('id="page-dashboard"', 1)[1].split('id="page-image-generation"', 1)[0]

        self.assertIn("最近画图", dashboard_page)
        self.assertIn("模型状态", dashboard_page)
        self.assertNotIn("推荐工作流", dashboard_page)
        self.assertNotIn("权限流程图模板", dashboard_page)
        self.assertNotIn("架构图模板", dashboard_page)
        self.assertNotIn("机制图模板", dashboard_page)
        self.assertNotIn("最近活动", dashboard_page)
        self.assertNotIn('id="refreshActivities"', dashboard_page)
        self.assertNotIn('id="activitiesList"', dashboard_page)

    def test_dashboard_recent_image_history_limits_to_six_items(self):
        app_js = Path("static/js/app.js").read_text(encoding="utf-8")

        self.assertIn("const DASHBOARD_IMAGE_HISTORY_LIMIT = 6;", app_js)
        self.assertIn("loadUnifiedImageHistory().slice(0, DASHBOARD_IMAGE_HISTORY_LIMIT)", app_js)
        self.assertNotIn("loadUnifiedImageHistory().slice(0, 8)", app_js)

    def test_light_monochrome_theme_keeps_primary_text_dark(self):
        mono_css = Path("static/css/mono.css").read_text(encoding="utf-8")
        light_theme_block = mono_css.split('[data-theme="light"] {', 1)[1].split("}", 1)[0]

        self.assertIn("--color-primary: #111111;", light_theme_block)
        self.assertIn("--color-primary-hover: #000000;", light_theme_block)
        self.assertIn("--color-primary-light: rgba(0, 0, 0, 0.08);", light_theme_block)
        self.assertIn("--color-text-muted: #555555;", light_theme_block)
        self.assertNotIn("--color-primary: #ffffff;", light_theme_block)

    def test_unified_gpt_params_use_labeled_responsive_panel(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")
        css = Path("static/css/app.css").read_text(encoding="utf-8")
        app_js = Path("static/js/app.js").read_text(encoding="utf-8")

        self.assertIn("gpt-control-panel", html)
        self.assertIn("gpt-control-grid", html)
        for field_id, label in (
            ("gptModelSelect", "模型"),
            ("gptSizeSelect", "尺寸"),
            ("gptQualitySelect", "质量"),
            ("gptFormatSelect", "格式"),
            ("gptNInput", "数量"),
        ):
            self.assertIn(f'for="{field_id}"', html)
            self.assertIn(f"<span>{label}</span>", html)

        self.assertIn(".gpt-unified-controls-mount .gpt-control-panel", css)
        self.assertIn(".gpt-unified-controls-mount .gpt-control-grid", css)
        self.assertIn("grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));", css)
        self.assertIn(".gpt-unified-controls-mount .gpt-param-field", css)
        self.assertIn("classList.toggle('gpt-image-mode', isGpt)", app_js)
        self.assertIn("#page-image-generation.gpt-image-mode .generation-workbench", css)
        self.assertIn("grid-template-columns: minmax(28rem, 0.78fr) minmax(18rem, 1fr);", css)
        self.assertIn("#page-image-generation.gpt-image-mode .gpt-unified-controls-mount .gpt-control-grid", css)
        self.assertIn("grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr));", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr);", css)

    def test_gpt_quick_prompt_buttons_are_removed_from_gallery_header(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")
        gallery_head = html.split('class="gpt-gallery-head"', 1)[1].split('id="gptGalleryGrid"', 1)[0]

        self.assertNotIn('id="gptQuickPrompts"', gallery_head)
        self.assertNotIn('class="gpt-prompt-chip"', gallery_head)
        self.assertNotIn("data-fill-gpt-prompt", gallery_head)
        for label in ("产品展示图", "科技插画", "海报配图", "人物头像"):
            self.assertNotIn(label, gallery_head)

    def test_unified_gpt_gallery_does_not_show_toolbar(self):
        html = Path("templates/index.html").read_text(encoding="utf-8")
        app_js = Path("static/js/app.js").read_text(encoding="utf-8")
        gpt_source = html.split('id="gpt-image-source-host"', 1)[1].split('class="gpt-gallery-shell"', 1)[0]

        self.assertNotIn('class="gpt-toolbar"', gpt_source)
        self.assertNotIn("GPT Image 画图工作台", gpt_source)
        self.assertNotIn('id="gptImageSourceSummary"', gpt_source)
        self.assertNotIn('id="gptGalleryCount"', gpt_source)
        self.assertNotIn('id="gptExportBtn"', gpt_source)
        self.assertNotIn('id="gptImportBtn"', gpt_source)
        self.assertNotIn('id="gptSettingsBtn"', gpt_source)
        self.assertNotIn("DOM.gptUnifiedGalleryMount.appendChild(toolbar)", app_js)

    def test_workbench_renders_editable_known_workflow_inputs(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")

        self.assertIn("function renderKnownGrsaiInputs", workbench_js)
        self.assertIn("function updateSelectedNodeInput", workbench_js)
        for input_name in (
            "prompt",
            "negative_prompt",
            "model",
            "aspectRatio",
            "imageSize",
            "seed",
            "steps",
            "cfg",
            "batch_size",
        ):
            self.assertIn(f"'{input_name}'", workbench_js)
        self.assertIn("Array.isArray(value)", workbench_js)
        self.assertIn("State.workflow[node.id].inputs[name] = parsedValue", workbench_js)
        self.assertIn("node.inputs[name] = parsedValue", workbench_js)
        self.assertIn("data-comfy-input-name", workbench_js)

    def test_workbench_uploads_images_for_load_image_nodes(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")
        css = Path("static/css/comfyui-workbench.css").read_text(encoding="utf-8")

        self.assertIn("function isLoadImageNode", workbench_js)
        self.assertIn("function renderLoadImageInputs", workbench_js)
        self.assertIn("function readFileAsDataUrl", workbench_js)
        self.assertIn("async function uploadImageForSelectedNode", workbench_js)
        self.assertIn("data-comfy-image-upload", workbench_js)
        self.assertIn("API.uploadImage", workbench_js)
        self.assertIn("new FileReader", workbench_js)
        self.assertIn("updateSelectedNodeInput('image', uploadedName)", workbench_js)
        self.assertIn("uploadImageForSelectedNode,", workbench_js)
        self.assertIn(".comfy-image-upload", css)
        self.assertIn(".comfy-upload-button", css)

    def test_workbench_runs_prompt_and_polls_backend_history(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")

        self.assertIn("async function runWorkflow", workbench_js)
        self.assertIn("function pollHistory", workbench_js)
        self.assertIn("renderResults", workbench_js)
        self.assertIn("workflow: State.workflow", workbench_js)
        self.assertIn("clientId: 'matchdrawer-web'", workbench_js)
        self.assertIn("API.prompt", workbench_js)
        self.assertIn("API.history(promptId)", workbench_js)
        self.assertIn("payload.prompt_id || payload.promptId", workbench_js)
        self.assertIn("DOM.runBtn.disabled = true", workbench_js)
        self.assertIn("DOM.runBtn.disabled = false", workbench_js)
        self.assertIn("setTimeout", workbench_js)

    def test_workbench_handles_normalized_backend_history_payload(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")

        self.assertIn("payload.status === 'succeeded'", workbench_js)
        self.assertIn("renderResults(payload.results || [])", workbench_js)
        self.assertIn("payload.status || 'running'", workbench_js)
        self.assertIn("normalized backend history", workbench_js)

    def test_poll_history_renders_normalized_backend_results_in_node(self):
        script = textwrap.dedent(
            r"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync('static/js/comfyui-workbench.js', 'utf8');

            function createElement(id) {
                return {
                    id,
                    textContent: '',
                    innerHTML: '',
                    disabled: id === 'comfyRunBtn',
                    value: '',
                    files: [],
                    style: {},
                    parentElement: { clientWidth: 960, clientHeight: 640 },
                    classList: {
                        toggle() {},
                        remove() {},
                    },
                    addEventListener() {},
                    setAttribute() {},
                    querySelectorAll() { return []; },
                    querySelector() { return null; },
                };
            }

            const elements = {};
            [
                'comfyWorkbenchRoot',
                'comfyConnectionStatus',
                'comfyImportBtn',
                'comfyImportInput',
                'comfyInstallBtn',
                'comfyStartBtn',
                'comfyRunBtn',
                'comfyCanvas',
                'comfyLinkLayer',
                'comfyEmptyState',
                'comfyPropertyPanel',
                'comfyRunLog',
                'comfyResults',
            ].forEach((id) => {
                elements[id] = createElement(id);
            });

            const sandbox = {
                console,
                setTimeout,
                clearTimeout,
                document: {
                    getElementById(id) {
                        return elements[id] || null;
                    },
                },
                fetch(url) {
                    if (url === '/api/comfyui/status') {
                        return Promise.resolve({
                            ok: true,
                            json: () => Promise.resolve({ connection: { connected: true } }),
                        });
                    }
                    if (url === '/api/comfyui/history/abc') {
                        return Promise.resolve({
                            ok: true,
                            json: () => Promise.resolve({
                                promptId: 'abc',
                                status: 'succeeded',
                                results: [{ filename: 'out.png', type: 'output' }],
                            }),
                        });
                    }
                    throw new Error(`unexpected fetch ${url}`);
                },
            };
            sandbox.window = {
                setTimeout,
                clearTimeout,
            };

            (async () => {
                vm.runInNewContext(source, sandbox, { filename: 'comfyui-workbench.js' });
                sandbox.window.ComfyUIWorkbench.init();
                sandbox.window.ComfyUIWorkbench.pollHistory('abc');
                await Promise.resolve();
                await new Promise((resolve) => setTimeout(resolve, 0));
                await Promise.resolve();

                console.log(JSON.stringify({
                    resultsHtml: elements.comfyResults.innerHTML,
                    runDisabled: elements.comfyRunBtn.disabled,
                    logText: elements.comfyRunLog.textContent,
                }));
            })().catch((error) => {
                console.error(error && error.stack ? error.stack : error);
                process.exit(1);
            });
            """
        )
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertIn("out.png", payload["resultsHtml"])
        self.assertIn("/api/comfyui/view", payload["resultsHtml"])
        self.assertFalse(payload["runDisabled"])
        self.assertIn("生成完成", payload["logText"])

    def test_template_button_imports_starter_workflow_in_node(self):
        script = textwrap.dedent(
            r"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync('static/js/comfyui-workbench.js', 'utf8');

            let templateClickHandler = null;
            const templateButton = {
                addEventListener(event, handler) {
                    if (event === 'click') {
                        templateClickHandler = handler;
                    }
                },
                getAttribute(name) {
                    return name === 'data-template' ? 'image-fusion' : null;
                },
            };

            function createElement(id) {
                return {
                    id,
                    textContent: '',
                    innerHTML: '',
                    disabled: false,
                    value: '',
                    files: [],
                    style: {},
                    parentElement: { clientWidth: 960, clientHeight: 640 },
                    classList: {
                        toggle() {},
                        remove() {},
                    },
                    addEventListener() {},
                    setAttribute() {},
                    querySelectorAll(selector) {
                        if (id === 'comfyWorkbenchRoot' && selector === '[data-template]') {
                            return [templateButton];
                        }
                        return [];
                    },
                    querySelector() { return null; },
                };
            }

            const elements = {};
            [
                'comfyWorkbenchRoot',
                'comfyConnectionStatus',
                'comfyImportBtn',
                'comfyImportInput',
                'comfyInstallBtn',
                'comfyStartBtn',
                'comfyRunBtn',
                'comfyCanvas',
                'comfyLinkLayer',
                'comfyEmptyState',
                'comfyPropertyPanel',
                'comfyRunLog',
                'comfyResults',
            ].forEach((id) => {
                elements[id] = createElement(id);
            });

            const calls = [];
            const starterWorkflow = {
                '1': { class_type: 'LoadImage', inputs: { image: 'input.png' } },
            };
            const sandbox = {
                console,
                setTimeout,
                clearTimeout,
                document: {
                    getElementById(id) {
                        return elements[id] || null;
                    },
                },
                fetch(url, options = {}) {
                    calls.push({ url, options });
                    if (url === '/api/comfyui/status') {
                        return Promise.resolve({
                            ok: true,
                            json: () => Promise.resolve({ connection: { connected: true } }),
                        });
                    }
                    if (url === '/api/comfyui/workflows/starter/image-fusion') {
                        return Promise.resolve({
                            ok: true,
                            json: () => Promise.resolve({ name: 'image-fusion', workflow: starterWorkflow }),
                        });
                    }
                    if (url === '/api/comfyui/workflows/import') {
                        const workflow = JSON.parse(options.body).workflow;
                        return Promise.resolve({
                            ok: true,
                            json: () => Promise.resolve({
                                workflow,
                                nodes: [{
                                    id: '1',
                                    title: 'LoadImage',
                                    classType: 'LoadImage',
                                    kind: 'core',
                                    inputs: { image: 'input.png' },
                                    position: { x: 120, y: 120 },
                                }],
                                links: [],
                                nodeCount: 1,
                            }),
                        });
                    }
                    throw new Error(`unexpected fetch ${url}`);
                },
            };
            sandbox.window = {
                setTimeout,
                clearTimeout,
            };

            (async () => {
                vm.runInNewContext(source, sandbox, { filename: 'comfyui-workbench.js' });
                sandbox.window.ComfyUIWorkbench.init();
                if (!templateClickHandler) {
                    throw new Error('template click handler was not registered');
                }
                await templateClickHandler();
                await Promise.resolve();

                console.log(JSON.stringify({
                    starterCalled: calls.some((call) => call.url === '/api/comfyui/workflows/starter/image-fusion'),
                    importCalled: calls.some((call) => call.url === '/api/comfyui/workflows/import'),
                    nodeCount: sandbox.window.ComfyUIWorkbench._state.nodes.length,
                    logText: elements.comfyRunLog.textContent,
                }));
            })().catch((error) => {
                console.error(error && error.stack ? error.stack : error);
                process.exit(1);
            });
            """
        )
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertTrue(payload["starterCalled"])
        self.assertTrue(payload["importCalled"])
        self.assertEqual(payload["nodeCount"], 1)
        self.assertIn("image-fusion", payload["logText"])

    def test_upload_image_updates_load_image_node_in_node(self):
        script = textwrap.dedent(
            r"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync('static/js/comfyui-workbench.js', 'utf8');

            function createElement(id) {
                return {
                    id,
                    textContent: '',
                    innerHTML: '',
                    disabled: false,
                    value: '',
                    files: [],
                    style: {},
                    parentElement: { clientWidth: 960, clientHeight: 640 },
                    classList: {
                        toggle() {},
                        remove() {},
                    },
                    addEventListener() {},
                    setAttribute() {},
                    querySelectorAll() { return []; },
                    querySelector() { return null; },
                };
            }

            const elements = {};
            [
                'comfyWorkbenchRoot',
                'comfyConnectionStatus',
                'comfyImportBtn',
                'comfyImportInput',
                'comfyInstallBtn',
                'comfyStartBtn',
                'comfyRunBtn',
                'comfyCanvas',
                'comfyLinkLayer',
                'comfyEmptyState',
                'comfyPropertyPanel',
                'comfyRunLog',
                'comfyResults',
            ].forEach((id) => {
                elements[id] = createElement(id);
            });

            let uploadBody = null;
            function FileReader() {}
            FileReader.prototype.readAsDataURL = function readAsDataURL(file) {
                this.result = `data:image/png;base64,${file.name}`;
                this.onload();
            };

            const sandbox = {
                console,
                setTimeout,
                clearTimeout,
                FileReader,
                document: {
                    getElementById(id) {
                        return elements[id] || null;
                    },
                },
                fetch(url, options = {}) {
                    if (url === '/api/comfyui/status') {
                        return Promise.resolve({
                            ok: true,
                            json: () => Promise.resolve({ connection: { connected: true } }),
                        });
                    }
                    if (url === '/api/comfyui/upload-image') {
                        uploadBody = JSON.parse(options.body);
                        return Promise.resolve({
                            ok: true,
                            json: () => Promise.resolve({ name: 'uploaded/ref.png' }),
                        });
                    }
                    throw new Error(`unexpected fetch ${url}`);
                },
            };
            sandbox.window = {
                setTimeout,
                clearTimeout,
            };

            (async () => {
                vm.runInNewContext(source, sandbox, { filename: 'comfyui-workbench.js' });
                sandbox.window.ComfyUIWorkbench.init();

                const state = sandbox.window.ComfyUIWorkbench._state;
                state.workflow = {
                    '1': { class_type: 'LoadImage', inputs: { image: 'old.png' } },
                };
                state.nodes = [{
                    id: '1',
                    title: 'LoadImage',
                    classType: 'LoadImage',
                    kind: 'core',
                    inputs: { image: 'old.png' },
                    position: { x: 120, y: 120 },
                }];
                state.selectedNodeId = '1';

                await sandbox.window.ComfyUIWorkbench.uploadImageForSelectedNode({ name: 'ref.png' });

                console.log(JSON.stringify({
                    uploadBody,
                    nodeImage: state.nodes[0].inputs.image,
                    workflowImage: state.workflow['1'].inputs.image,
                    logText: elements.comfyRunLog.textContent,
                    panelHtml: elements.comfyPropertyPanel.innerHTML,
                }));
            })().catch((error) => {
                console.error(error && error.stack ? error.stack : error);
                process.exit(1);
            });
            """
        )
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["uploadBody"]["filename"], "ref.png")
        self.assertIn("data:image/png;base64,ref.png", payload["uploadBody"]["image"])
        self.assertEqual(payload["nodeImage"], "uploaded/ref.png")
        self.assertEqual(payload["workflowImage"], "uploaded/ref.png")
        self.assertIn("已上传参考图", payload["logText"])
        self.assertIn("uploaded/ref.png", payload["panelHtml"])

    def test_dragging_and_connecting_nodes_updates_workflow_in_node(self):
        script = textwrap.dedent(
            r"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync('static/js/comfyui-workbench.js', 'utf8');

            function createElement(id) {
                return {
                    id,
                    textContent: '',
                    innerHTML: '',
                    disabled: false,
                    value: '',
                    files: [],
                    style: {},
                    parentElement: { clientWidth: 960, clientHeight: 640 },
                    classList: {
                        toggle() {},
                        remove() {},
                    },
                    addEventListener() {},
                    setAttribute() {},
                    querySelectorAll() { return []; },
                    querySelector() { return null; },
                };
            }

            const elements = {};
            [
                'comfyWorkbenchRoot',
                'comfyConnectionStatus',
                'comfyImportBtn',
                'comfyImportInput',
                'comfyInstallBtn',
                'comfyStartBtn',
                'comfyRunBtn',
                'comfyCanvas',
                'comfyLinkLayer',
                'comfyEmptyState',
                'comfyPropertyPanel',
                'comfyRunLog',
                'comfyResults',
            ].forEach((id) => {
                elements[id] = createElement(id);
            });

            const sandbox = {
                console,
                setTimeout,
                clearTimeout,
                document: {
                    addEventListener() {},
                    removeEventListener() {},
                    getElementById(id) {
                        return elements[id] || null;
                    },
                },
                fetch(url) {
                    if (url === '/api/comfyui/status') {
                        return Promise.resolve({
                            ok: true,
                            json: () => Promise.resolve({ connection: { connected: true } }),
                        });
                    }
                    throw new Error(`unexpected fetch ${url}`);
                },
            };
            sandbox.window = {
                setTimeout,
                clearTimeout,
            };

            (async () => {
                vm.runInNewContext(source, sandbox, { filename: 'comfyui-workbench.js' });
                sandbox.window.ComfyUIWorkbench.init();

                const state = sandbox.window.ComfyUIWorkbench._state;
                state.workflow = {
                    '1': {
                        class_type: 'LoadImage',
                        inputs: { image: 'input.png' },
                        _meta: { title: 'Load reference' },
                    },
                    '2': {
                        class_type: 'GrsAINanoBananaTextImage',
                        inputs: { prompt: 'make an image', model: 'nano-banana-pro' },
                        _meta: { title: 'Generate' },
                    },
                };
                state.nodes = [{
                    id: '1',
                    title: 'Load reference',
                    classType: 'LoadImage',
                    kind: 'core',
                    inputs: { image: 'input.png' },
                    position: { x: 120, y: 120 },
                }, {
                    id: '2',
                    title: 'Generate',
                    classType: 'GrsAINanoBananaTextImage',
                    kind: 'grsai',
                    inputs: { prompt: 'make an image', model: 'nano-banana-pro' },
                    position: { x: 340, y: 230 },
                }];
                state.links = [];

                sandbox.window.ComfyUIWorkbench.moveNode('1', 420, 260);
                sandbox.window.ComfyUIWorkbench.connectNodes({
                    fromNode: '1',
                    fromOutput: 0,
                    toNode: '2',
                    toInput: 'image1',
                });
                sandbox.window.ComfyUIWorkbench.connectNodes({
                    fromNode: '1',
                    fromOutput: 0,
                    toNode: '2',
                    toInput: 'image1',
                });

                console.log(JSON.stringify({
                    nodePosition: state.nodes[0].position,
                    workflowPosition: state.workflow['1']._meta.position,
                    linkCount: state.links.length,
                    firstLink: state.links[0],
                    workflowInput: state.workflow['2'].inputs.image1,
                    nodeInput: state.nodes[1].inputs.image1,
                    logText: elements.comfyRunLog.textContent,
                }));
            })().catch((error) => {
                console.error(error && error.stack ? error.stack : error);
                process.exit(1);
            });
            """
        )
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["nodePosition"], {"x": 420, "y": 260})
        self.assertEqual(payload["workflowPosition"], {"x": 420, "y": 260})
        self.assertEqual(payload["linkCount"], 1)
        self.assertEqual(payload["firstLink"]["fromNode"], "1")
        self.assertEqual(payload["firstLink"]["toNode"], "2")
        self.assertEqual(payload["firstLink"]["toInput"], "image1")
        self.assertEqual(payload["workflowInput"], ["1", 0])
        self.assertEqual(payload["nodeInput"], ["1", 0])
        self.assertIn("已连接", payload["logText"])

    def test_workbench_result_thumbnails_use_backend_view_route(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")

        self.assertIn("function renderResults", workbench_js)
        self.assertIn("API.view(image)", workbench_js)
        self.assertIn("comfy-result-grid", workbench_js)
        self.assertIn("comfy-result-thumb", workbench_js)
        self.assertNotIn("image.url", workbench_js)
        self.assertNotIn("ComfyUI URL", workbench_js)

    def test_css_styles_property_fields_and_result_thumbnails(self):
        css = Path("static/css/comfyui-workbench.css").read_text(encoding="utf-8")

        self.assertIn(".comfy-input-form", css)
        self.assertIn(".comfy-input-field", css)
        self.assertIn(".comfy-input-control", css)
        self.assertIn(".comfy-image-upload", css)
        self.assertIn(".comfy-result-grid", css)
        self.assertIn(".comfy-result-thumb", css)

    def test_property_panel_remains_visible_on_tablet_and_mobile(self):
        css = Path("static/css/comfyui-workbench.css").read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 1180px)", css)
        self.assertIn(".comfy-property-panel", css)
        self.assertNotIn(".comfy-property-panel {\n    display: none;", css)
        self.assertIn("grid-template-areas", css)
        self.assertIn("grid-area: properties", css)

    def test_runtime_actions_and_starter_workflow_are_present(self):
        workbench_js = Path("static/js/comfyui-workbench.js").read_text(encoding="utf-8")
        starter = Path("integrations/comfyui_grsai/workflows/text_image_api.json")

        self.assertIn("async function installRuntime", workbench_js)
        self.assertIn("async function startRuntime", workbench_js)
        self.assertIn("installingRuntime: false", workbench_js)
        self.assertIn("startingRuntime: false", workbench_js)
        self.assertIn("if (State.installingRuntime) return", workbench_js)
        self.assertIn("if (State.startingRuntime) return", workbench_js)
        self.assertIn("State.installingRuntime = true", workbench_js)
        self.assertIn("State.startingRuntime = true", workbench_js)
        self.assertIn("DOM.installBtn.disabled = true", workbench_js)
        self.assertIn("DOM.startBtn.disabled = true", workbench_js)
        self.assertIn("finally", workbench_js)
        self.assertIn("State.installingRuntime = false", workbench_js)
        self.assertIn("State.startingRuntime = false", workbench_js)
        self.assertIn("DOM.installBtn.disabled = false", workbench_js)
        self.assertIn("DOM.startBtn.disabled = false", workbench_js)
        self.assertIn("RUNTIME_ACTION_HEADERS", workbench_js)
        self.assertIn("'X-ComfyUI-Runtime-Action': 'confirm-local-runtime'", workbench_js)
        self.assertIn("requestJson(API.runtimeInstall", workbench_js)
        self.assertIn("requestJson(API.runtimeStart", workbench_js)
        self.assertIn("headers: RUNTIME_ACTION_HEADERS", workbench_js)
        self.assertIn("DOM.installBtn.addEventListener('click', () => installRuntime())", workbench_js)
        self.assertIn("DOM.startBtn.addEventListener('click', () => startRuntime())", workbench_js)
        self.assertIn("启动请求已发送，正在检查连接状态", workbench_js)
        self.assertNotIn("result.baseUrl", workbench_js)

        self.assertTrue(starter.exists())
        workflow = json.loads(starter.read_text(encoding="utf-8"))
        self.assertIn("1", workflow)
        self.assertIn("2", workflow)
        self.assertEqual(workflow["1"]["class_type"], "GrsAINanoBananaTextImage")
        self.assertEqual(workflow["2"]["class_type"], "PreviewImage")
        self.assertEqual(workflow["2"]["inputs"]["images"], ["1", 0])
        self.assertIn("GrsAI", json.dumps(workflow))
        self.assertTrue(Path("integrations/comfyui_grsai/workflows/image_fusion_api.json").exists())
        self.assertTrue(Path("integrations/comfyui_grsai/workflows/batch_generate_api.json").exists())

    def test_runtime_actions_prevent_duplicate_posts_and_hide_upstream_url(self):
        script = textwrap.dedent(
            r"""
            const fs = require('fs');
            const vm = require('vm');
            const source = fs.readFileSync('static/js/comfyui-workbench.js', 'utf8');

            function createElement(id) {
                return {
                    id,
                    textContent: '',
                    innerHTML: '',
                    disabled: false,
                    value: '',
                    files: [],
                    style: {},
                    parentElement: { clientWidth: 960, clientHeight: 640 },
                    classList: {
                        toggle() {},
                        remove() {},
                    },
                    addEventListener() {},
                    setAttribute() {},
                    querySelectorAll() { return []; },
                    querySelector() { return null; },
                };
            }

            const elements = {};
            [
                'comfyWorkbenchRoot',
                'comfyConnectionStatus',
                'comfyImportBtn',
                'comfyImportInput',
                'comfyInstallBtn',
                'comfyStartBtn',
                'comfyRunBtn',
                'comfyCanvas',
                'comfyLinkLayer',
                'comfyEmptyState',
                'comfyPropertyPanel',
                'comfyRunLog',
                'comfyResults',
            ].forEach((id) => {
                elements[id] = createElement(id);
            });

            let installResolve;
            let startResolve;
            const calls = [];
            const sandbox = {
                console,
                setTimeout(callback) {
                    callback();
                    return 1;
                },
                clearTimeout,
                document: {
                    getElementById(id) {
                        return elements[id] || null;
                    },
                },
                fetch(url, options = {}) {
                    calls.push({ url, options });
                    if (url === '/api/comfyui/status') {
                        return Promise.resolve({
                            ok: true,
                            json: () => Promise.resolve({ connection: { connected: true } }),
                        });
                    }
                    if (url === '/api/comfyui/runtime/install') {
                        return new Promise((resolve) => {
                            installResolve = () => resolve({
                                ok: true,
                                json: () => Promise.resolve({ state: 'installing' }),
                            });
                        });
                    }
                    if (url === '/api/comfyui/runtime/start') {
                        return new Promise((resolve) => {
                            startResolve = () => resolve({
                                ok: true,
                                json: () => Promise.resolve({ baseUrl: 'http://127.0.0.1:8188' }),
                            });
                        });
                    }
                    throw new Error(`unexpected fetch ${url}`);
                },
            };
            sandbox.window = {
                setTimeout: sandbox.setTimeout,
                clearTimeout,
            };

            (async () => {
                vm.runInNewContext(source, sandbox, { filename: 'comfyui-workbench.js' });
                sandbox.window.ComfyUIWorkbench.init();
                await Promise.resolve();

                const firstInstall = sandbox.window.ComfyUIWorkbench.installRuntime();
                const secondInstall = sandbox.window.ComfyUIWorkbench.installRuntime();
                await Promise.resolve();
                const installDisabledDuringRequest = elements.comfyInstallBtn.disabled;
                installResolve();
                await firstInstall;
                await secondInstall;

                const firstStart = sandbox.window.ComfyUIWorkbench.startRuntime();
                const secondStart = sandbox.window.ComfyUIWorkbench.startRuntime();
                await Promise.resolve();
                const startDisabledDuringRequest = elements.comfyStartBtn.disabled;
                startResolve();
                await firstStart;
                await secondStart;

                console.log(JSON.stringify({
                    installPosts: calls.filter((call) => call.url === '/api/comfyui/runtime/install').length,
                    startPosts: calls.filter((call) => call.url === '/api/comfyui/runtime/start').length,
                    installHeader: calls.find((call) => call.url === '/api/comfyui/runtime/install').options.headers['X-ComfyUI-Runtime-Action'],
                    startHeader: calls.find((call) => call.url === '/api/comfyui/runtime/start').options.headers['X-ComfyUI-Runtime-Action'],
                    installDisabledDuringRequest,
                    startDisabledDuringRequest,
                    installDisabledAfterRequest: elements.comfyInstallBtn.disabled,
                    startDisabledAfterRequest: elements.comfyStartBtn.disabled,
                    logText: elements.comfyRunLog.textContent,
                }));
            })().catch((error) => {
                console.error(error && error.stack ? error.stack : error);
                process.exit(1);
            });
            """
        )
        result = subprocess.run(
            ["node", "-e", script],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["installPosts"], 1)
        self.assertEqual(payload["startPosts"], 1)
        self.assertEqual(payload["installHeader"], "confirm-local-runtime")
        self.assertEqual(payload["startHeader"], "confirm-local-runtime")
        self.assertTrue(payload["installDisabledDuringRequest"])
        self.assertTrue(payload["startDisabledDuringRequest"])
        self.assertFalse(payload["installDisabledAfterRequest"])
        self.assertFalse(payload["startDisabledAfterRequest"])
        self.assertIn("启动请求已发送，正在检查连接状态", payload["logText"])
        self.assertNotIn("127.0.0.1", payload["logText"])


if __name__ == "__main__":
    unittest.main()

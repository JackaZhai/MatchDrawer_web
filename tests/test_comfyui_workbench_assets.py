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

        self.assertIn('data-page="comfyui-workbench"', html)
        self.assertIn("生图工作台", html)
        self.assertIn('id="page-comfyui-workbench"', html)
        self.assertIn("js/comfyui-workbench.js", html)
        self.assertIn("css/comfyui-workbench.css", html)

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
        workbench_shell = html.split('id="page-comfyui-workbench"', 1)[1].split('id="page-gpt-image"', 1)[0]

        self.assertIn('data-template="text-image"', workbench_shell)
        self.assertIn('data-template="image-fusion"', workbench_shell)
        self.assertIn('data-template="batch-generate"', workbench_shell)
        self.assertIn("<span>Text / Image</span>", workbench_shell)
        self.assertNotIn("GrsAI", workbench_shell)
        self.assertNotIn("grsai-", workbench_shell)

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
        self.assertIn(".comfy-result-grid", css)
        self.assertIn(".comfy-result-thumb", css)

    def test_property_panel_remains_visible_on_tablet_and_mobile(self):
        css = Path("static/css/comfyui-workbench.css").read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 1180px)", css)
        self.assertIn(".comfy-property-panel", css)
        self.assertNotIn(".comfy-property-panel {\n    display: none;", css)
        self.assertIn("grid-template-areas", css)
        self.assertIn("grid-area: properties", css)


if __name__ == "__main__":
    unittest.main()

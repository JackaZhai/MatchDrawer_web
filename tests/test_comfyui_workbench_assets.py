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


if __name__ == "__main__":
    unittest.main()

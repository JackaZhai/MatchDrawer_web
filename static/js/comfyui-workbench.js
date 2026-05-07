(function () {
    'use strict';

    const State = {
        initialized: false,
        workflow: null,
        nodes: [],
        links: [],
        selectedNodeId: null,
        promptId: null,
        pollTimer: null,
    };

    const API = {
        status: '/api/comfyui/status',
        importWorkflow: '/api/comfyui/workflows/import',
        prompt: '/api/comfyui/prompt',
        history: (id) => `/api/comfyui/history/${encodeURIComponent(id)}`,
        uploadImage: '/api/comfyui/upload-image',
        runtimeInstall: '/api/comfyui/runtime/install',
        runtimeStart: '/api/comfyui/runtime/start',
        view: (image) => `/api/comfyui/view?filename=${encodeURIComponent(image.filename)}&subfolder=${encodeURIComponent(image.subfolder || '')}&type=${encodeURIComponent(image.type || 'output')}`,
    };

    const DOM = {};

    function cacheDom() {
        DOM.root = document.getElementById('comfyWorkbenchRoot');
        DOM.status = document.getElementById('comfyConnectionStatus');
        DOM.importBtn = document.getElementById('comfyImportBtn');
        DOM.importInput = document.getElementById('comfyImportInput');
        DOM.installBtn = document.getElementById('comfyInstallBtn');
        DOM.startBtn = document.getElementById('comfyStartBtn');
        DOM.runBtn = document.getElementById('comfyRunBtn');
        DOM.canvas = document.getElementById('comfyCanvas');
        DOM.links = document.getElementById('comfyLinkLayer');
        DOM.empty = document.getElementById('comfyEmptyState');
        DOM.panel = document.getElementById('comfyPropertyPanel');
        DOM.log = document.getElementById('comfyRunLog');
        DOM.results = document.getElementById('comfyResults');
    }

    async function requestJson(url, options = {}) {
        const response = await fetch(url, {
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            ...options,
        });
        if (!response.ok) {
            throw new Error(await response.text());
        }
        return response.json();
    }

    function setLog(message) {
        if (DOM.log) {
            DOM.log.textContent = message;
        }
    }

    async function refreshStatus() {
        try {
            const payload = await requestJson(API.status);
            const connected = payload.connection && payload.connection.connected;
            if (DOM.status) {
                DOM.status.textContent = connected ? '已连接' : '未连接';
                DOM.status.classList.toggle('is-connected', !!connected);
            }
        } catch (error) {
            if (DOM.status) {
                DOM.status.textContent = '连接失败';
                DOM.status.classList.remove('is-connected');
            }
        }
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function nodePosition(node, fallbackIndex = 0) {
        const position = node && node.position ? node.position : {};
        return {
            x: Number(position.x) || 120 + fallbackIndex * 220,
            y: Number(position.y) || 120 + (fallbackIndex % 3) * 110,
        };
    }

    async function importWorkflowFile(file) {
        const text = await file.text();
        const workflow = JSON.parse(text);
        const payload = await requestJson(API.importWorkflow, {
            method: 'POST',
            body: JSON.stringify({ workflow }),
        });

        State.workflow = payload.workflow || workflow;
        State.nodes = Array.isArray(payload.nodes) ? payload.nodes : [];
        State.links = Array.isArray(payload.links) ? payload.links : [];
        State.selectedNodeId = null;
        renderCanvas();
        renderPropertyPanel();
        setLog(`已导入 ${payload.nodeCount || State.nodes.length} 个节点`);
    }

    function renderCanvas() {
        if (!DOM.canvas) return;

        if (DOM.empty) {
            DOM.empty.style.display = State.nodes.length ? 'none' : 'flex';
        }

        DOM.canvas.innerHTML = State.nodes.map((node, index) => {
            const position = nodePosition(node, index);
            const selected = node.id === State.selectedNodeId ? ' is-selected' : '';
            return `
                <button type="button"
                        class="comfy-node-card comfy-node-${escapeHtml(node.kind || 'unknown')}${selected}"
                        data-node-id="${escapeHtml(node.id)}"
                        style="left:${position.x}px;top:${position.y}px">
                    <span class="comfy-node-title">${escapeHtml(node.title || node.classType || node.id)}</span>
                    <span class="comfy-node-meta">#${escapeHtml(node.id)} · ${escapeHtml(node.classType || 'Unknown')}</span>
                </button>
            `;
        }).join('');

        DOM.canvas.querySelectorAll('[data-node-id]').forEach((element) => {
            element.addEventListener('click', () => selectNode(element.getAttribute('data-node-id')));
        });
        renderLinks();
    }

    function renderLinks() {
        if (!DOM.links) return;

        const nodeMap = new Map(State.nodes.map((node, index) => [node.id, { node, index }]));
        DOM.links.innerHTML = State.links.map((link, index) => {
            const source = nodeMap.get(link.fromNode);
            const target = nodeMap.get(link.toNode);
            if (!source || !target) return '';

            const from = nodePosition(source.node, source.index);
            const to = nodePosition(target.node, target.index);
            const x1 = from.x + 176;
            const y1 = from.y + 42;
            const x2 = to.x;
            const y2 = to.y + 42;
            const curve = Math.max(40, Math.abs(x2 - x1) / 2);
            const selected = link.fromNode === State.selectedNodeId || link.toNode === State.selectedNodeId ? ' is-selected' : '';
            return `<path class="comfy-link-path${selected}" data-link-index="${index}" d="M ${x1} ${y1} C ${x1 + curve} ${y1}, ${x2 - curve} ${y2}, ${x2} ${y2}" />`;
        }).join('');
    }

    function selectNode(nodeId) {
        State.selectedNodeId = nodeId;
        renderCanvas();
        renderPropertyPanel();
    }

    function selectedNode() {
        return State.nodes.find((node) => node.id === State.selectedNodeId) || null;
    }

    function renderPropertyPanel() {
        if (!DOM.panel) return;

        const node = selectedNode();
        if (!node) {
            DOM.panel.className = 'comfy-property-empty';
            DOM.panel.innerHTML = '选择一个节点';
            return;
        }

        DOM.panel.className = 'comfy-property-preview';
        DOM.panel.innerHTML = `
            <div class="comfy-property-node-title">${escapeHtml(node.title || node.classType || node.id)}</div>
            <div class="comfy-property-node-meta">#${escapeHtml(node.id)} · ${escapeHtml(node.classType || 'Unknown')} · ${escapeHtml(node.kind || 'unknown')}</div>
            <pre class="comfy-json-preview">${escapeHtml(JSON.stringify(node.inputs || {}, null, 2))}</pre>
        `;
    }

    function bindEvents() {
        if (DOM.importBtn && DOM.importInput) {
            DOM.importBtn.addEventListener('click', () => DOM.importInput.click());
            DOM.importInput.addEventListener('change', (event) => {
                const file = event.target.files && event.target.files[0];
                if (file) {
                    importWorkflowFile(file).catch((error) => {
                        setLog(`导入失败: ${error.message}`);
                    });
                }
                DOM.importInput.value = '';
            });
        }
        if (DOM.installBtn) {
            DOM.installBtn.addEventListener('click', () => setLog('安装 ComfyUI 功能待接入'));
        }
        if (DOM.startBtn) {
            DOM.startBtn.addEventListener('click', () => setLog('启动 ComfyUI 功能待接入'));
        }
        if (DOM.runBtn) {
            DOM.runBtn.addEventListener('click', () => setLog('运行 workflow 功能待接入'));
        }
    }

    function init() {
        cacheDom();
        if (!DOM.root || State.initialized) return;
        State.initialized = true;
        bindEvents();
        refreshStatus();
    }

    window.ComfyUIWorkbench = {
        init,
        refreshStatus,
        _state: State,
        _api: API,
    };
})();

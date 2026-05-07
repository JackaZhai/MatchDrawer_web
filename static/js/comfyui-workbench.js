(function () {
    'use strict';

    const State = {
        initialized: false,
        workflow: null,
        nodes: [],
        links: [],
        viewport: null,
        selectedNodeId: null,
        promptId: null,
        pollTimer: null,
    };

    const NODE_CARD = {
        width: 176,
        height: 76,
        padding: 96,
        minWidth: 720,
        minHeight: 480,
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
        const x = Number(position.x);
        const y = Number(position.y);
        return {
            x: Number.isFinite(x) ? x : 120 + fallbackIndex * 220,
            y: Number.isFinite(y) ? y : 120 + (fallbackIndex % 3) * 110,
        };
    }

    function nodeKindClass(kind) {
        if (kind === 'core') return 'core';
        if (kind === 'unknown') return 'unknown';
        return 'custom';
    }

    function nodeKindLabel(kind) {
        if (kind === 'core') return 'Core Node';
        if (kind === 'unknown') return 'Unknown Node';
        return 'Custom Node';
    }

    function layoutViewport() {
        const shell = DOM.canvas ? DOM.canvas.parentElement : null;
        const shellWidth = shell ? shell.clientWidth : 0;
        const shellHeight = shell ? shell.clientHeight : 0;

        if (!State.nodes.length) {
            return {
                width: Math.max(shellWidth, NODE_CARD.minWidth),
                height: Math.max(shellHeight, NODE_CARD.minHeight),
                offsetX: 0,
                offsetY: 0,
            };
        }

        const bounds = State.nodes.reduce((result, node, index) => {
            const position = nodePosition(node, index);
            return {
                minX: Math.min(result.minX, position.x),
                minY: Math.min(result.minY, position.y),
                maxX: Math.max(result.maxX, position.x + NODE_CARD.width),
                maxY: Math.max(result.maxY, position.y + NODE_CARD.height),
            };
        }, {
            minX: Infinity,
            minY: Infinity,
            maxX: -Infinity,
            maxY: -Infinity,
        });

        return {
            width: Math.max(shellWidth, NODE_CARD.minWidth, bounds.maxX - bounds.minX + NODE_CARD.padding * 2),
            height: Math.max(shellHeight, NODE_CARD.minHeight, bounds.maxY - bounds.minY + NODE_CARD.padding * 2),
            offsetX: NODE_CARD.padding - bounds.minX,
            offsetY: NODE_CARD.padding - bounds.minY,
        };
    }

    function normalizeNodePosition(node, index, viewport) {
        const position = nodePosition(node, index);
        return {
            x: position.x + viewport.offsetX,
            y: position.y + viewport.offsetY,
        };
    }

    function setCanvasDimensions(viewport) {
        if (DOM.canvas) {
            DOM.canvas.style.width = `${viewport.width}px`;
            DOM.canvas.style.height = `${viewport.height}px`;
        }
        if (DOM.links) {
            DOM.links.setAttribute('width', String(viewport.width));
            DOM.links.setAttribute('height', String(viewport.height));
            DOM.links.setAttribute('viewBox', `0 0 ${viewport.width} ${viewport.height}`);
            DOM.links.style.width = `${viewport.width}px`;
            DOM.links.style.height = `${viewport.height}px`;
        }
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

        const viewport = layoutViewport();
        State.viewport = viewport;
        setCanvasDimensions(viewport);

        if (DOM.empty) {
            DOM.empty.style.display = State.nodes.length ? 'none' : 'flex';
        }

        DOM.canvas.innerHTML = State.nodes.map((node, index) => {
            const position = normalizeNodePosition(node, index, viewport);
            const selected = node.id === State.selectedNodeId ? ' is-selected' : '';
            const kindClass = nodeKindClass(node.kind);
            return `
                <button type="button"
                        class="comfy-node-card comfy-node-${kindClass}${selected}"
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
        renderLinks(viewport);
    }

    function renderLinks(viewport = State.viewport || layoutViewport()) {
        if (!DOM.links) return;

        const nodeMap = new Map(State.nodes.map((node, index) => [node.id, { node, index }]));
        DOM.links.innerHTML = State.links.map((link, index) => {
            const source = nodeMap.get(link.fromNode);
            const target = nodeMap.get(link.toNode);
            if (!source || !target) return '';

            const from = normalizeNodePosition(source.node, source.index, viewport);
            const to = normalizeNodePosition(target.node, target.index, viewport);
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
            <div class="comfy-property-node-meta">#${escapeHtml(node.id)} · ${escapeHtml(node.classType || 'Unknown')} · ${escapeHtml(nodeKindLabel(node.kind))}</div>
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

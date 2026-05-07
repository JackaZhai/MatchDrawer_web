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
        running: false,
    };

    const KNOWN_GRSAI_INPUTS = [
        { name: 'prompt', label: 'Prompt', type: 'textarea' },
        { name: 'negative_prompt', label: 'Negative prompt', type: 'textarea' },
        { name: 'model', label: 'Model', type: 'text' },
        { name: 'aspectRatio', label: 'Aspect ratio', type: 'text' },
        { name: 'imageSize', label: 'Image size', type: 'text' },
        { name: 'seed', label: 'Seed', type: 'number' },
        { name: 'steps', label: 'Steps', type: 'number' },
        { name: 'cfg', label: 'CFG', type: 'number' },
        { name: 'batch_size', label: 'Batch size', type: 'number' },
    ];

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
        State.promptId = null;
        renderResults([]);
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

    function inputControlMarkup(definition, value) {
        const escapedName = escapeHtml(definition.name);
        const escapedLabel = escapeHtml(definition.label);
        const escapedValue = escapeHtml(value);

        if (definition.type === 'textarea') {
            return `
                <label class="comfy-input-field">
                    <span>${escapedLabel}</span>
                    <textarea class="comfy-input-control"
                              rows="4"
                              data-comfy-input-name="${escapedName}">${escapedValue}</textarea>
                </label>
            `;
        }

        return `
            <label class="comfy-input-field">
                <span>${escapedLabel}</span>
                <input class="comfy-input-control"
                       type="${definition.type === 'number' ? 'number' : 'text'}"
                       data-comfy-input-name="${escapedName}"
                       value="${escapedValue}">
            </label>
        `;
    }

    function renderKnownGrsaiInputs(node) {
        const inputs = node && node.inputs && typeof node.inputs === 'object' ? node.inputs : {};
        const fields = KNOWN_GRSAI_INPUTS
            .filter((definition) => Object.prototype.hasOwnProperty.call(inputs, definition.name))
            .filter((definition) => {
                const value = inputs[definition.name];
                return !Array.isArray(value);
            })
            .map((definition) => inputControlMarkup(definition, inputs[definition.name]));

        if (!fields.length) {
            return '<div class="comfy-input-empty">无可编辑输入</div>';
        }

        return `<form class="comfy-input-form">${fields.join('')}</form>`;
    }

    function parseInputValue(name, value) {
        if (['seed', 'steps', 'batch_size'].includes(name)) {
            const parsed = Number.parseInt(value, 10);
            return Number.isFinite(parsed) ? parsed : 0;
        }
        if (name === 'cfg') {
            const parsed = Number.parseFloat(value);
            return Number.isFinite(parsed) ? parsed : 0;
        }
        return value;
    }

    function updateSelectedNodeInput(name, value) {
        const node = selectedNode();
        if (!node || !name) return;

        const parsedValue = parseInputValue(name, value);
        node.inputs = node.inputs && typeof node.inputs === 'object' ? node.inputs : {};
        node.inputs[name] = parsedValue;

        if (State.workflow && State.workflow[node.id]) {
            State.workflow[node.id].inputs = State.workflow[node.id].inputs && typeof State.workflow[node.id].inputs === 'object'
                ? State.workflow[node.id].inputs
                : {};
            State.workflow[node.id].inputs[name] = parsedValue;
        }
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
            ${renderKnownGrsaiInputs(node)}
            <pre class="comfy-json-preview">${escapeHtml(JSON.stringify(node.inputs || {}, null, 2))}</pre>
        `;

        DOM.panel.querySelectorAll('[data-comfy-input-name]').forEach((element) => {
            element.addEventListener('input', () => {
                updateSelectedNodeInput(element.getAttribute('data-comfy-input-name'), element.value);
                const preview = DOM.panel.querySelector('.comfy-json-preview');
                const currentNode = selectedNode();
                if (preview && currentNode) {
                    preview.textContent = JSON.stringify(currentNode.inputs || {}, null, 2);
                }
            });
        });
    }

    function setRunning(isRunning) {
        State.running = isRunning;
        if (DOM.runBtn && isRunning) {
            DOM.runBtn.disabled = true;
        } else if (DOM.runBtn) {
            DOM.runBtn.disabled = false;
        }
    }

    function extractHistoryRecord(payload, promptId) {
        if (!payload || typeof payload !== 'object') return null;
        if (payload[promptId]) return payload[promptId];
        if (payload.history && payload.history[promptId]) return payload.history[promptId];
        if (payload.outputs || payload.status) return payload;
        return null;
    }

    function historySucceeded(record) {
        if (!record) return false;
        if (record.outputs && Object.keys(record.outputs).length) return true;
        if (record.status && record.status.completed === true) return true;
        if (record.status && record.status.status_str === 'success') return true;
        return false;
    }

    function collectResultImages(record) {
        const outputs = record && record.outputs && typeof record.outputs === 'object' ? record.outputs : {};
        return Object.values(outputs).flatMap((output) => {
            if (!output || !Array.isArray(output.images)) return [];
            return output.images.filter((image) => image && image.filename);
        });
    }

    function renderResults(images) {
        if (!DOM.results) return;
        const safeImages = Array.isArray(images) ? images.filter((image) => image && image.filename) : [];
        if (!safeImages.length) {
            DOM.results.innerHTML = '<div class="comfy-results-empty">暂无结果</div>';
            return;
        }

        DOM.results.innerHTML = `
            <div class="comfy-result-grid">
                ${safeImages.map((image) => {
                    const src = API.view(image);
                    const title = image.filename || 'result';
                    return `
                        <a class="comfy-result-thumb" href="${escapeHtml(src)}" target="_blank" rel="noopener">
                            <img src="${escapeHtml(src)}" alt="${escapeHtml(title)}" loading="lazy">
                        </a>
                    `;
                }).join('')}
            </div>
        `;
    }

    async function installRuntime() {
        setLog('开始安装 ComfyUI，本步骤会下载 ComfyUI 和 ComfyUI-GrsAI');
        try {
            const result = await requestJson(API.runtimeInstall, { method: 'POST', body: '{}' });
            setLog(`安装状态: ${result.state || '完成'}`);
            await refreshStatus();
        } catch (error) {
            setLog(`安装失败: ${error.message}`);
        }
    }

    async function startRuntime() {
        setLog('正在启动 ComfyUI');
        try {
            const result = await requestJson(API.runtimeStart, { method: 'POST', body: '{}' });
            setLog(`启动请求已发送: ${result.baseUrl || ''}`);
            window.setTimeout(refreshStatus, 2500);
        } catch (error) {
            setLog(`启动失败: ${error.message}`);
        }
    }

    function pollHistory(promptId) {
        if (!promptId) {
            setLog('缺少任务 ID，无法查询历史');
            setRunning(false);
            return;
        }

        if (State.pollTimer) {
            window.clearTimeout(State.pollTimer);
            State.pollTimer = null;
        }

        requestJson(API.history(promptId))
            .then((payload) => {
                // Primary path: normalized backend history from /api/comfyui/history/<prompt_id>.
                if (payload && payload.promptId && typeof payload.status === 'string') {
                    if (payload.status === 'succeeded') {
                        renderResults(payload.results || []);
                        setLog(`生成完成，返回 ${(payload.results || []).length} 张图片`);
                        setRunning(false);
                        return;
                    }

                    const normalizedStatus = payload.status || 'running';
                    setLog(`生成中: ${normalizedStatus}`);
                    State.pollTimer = window.setTimeout(() => pollHistory(promptId), 1800);
                    return;
                }

                const record = extractHistoryRecord(payload, promptId);
                if (historySucceeded(record)) {
                    const images = collectResultImages(record);
                    renderResults(images);
                    setLog(images.length ? `生成完成，返回 ${images.length} 张图片` : '生成完成，未返回图片');
                    setRunning(false);
                    return;
                }

                setLog(`生成中: ${promptId}`);
                State.pollTimer = window.setTimeout(() => pollHistory(promptId), 1800);
            })
            .catch((error) => {
                setLog(`查询失败: ${error.message}`);
                setRunning(false);
            });
    }

    async function runWorkflow() {
        if (!State.workflow) {
            setLog('请先导入 workflow');
            return;
        }

        if (State.pollTimer) {
            window.clearTimeout(State.pollTimer);
            State.pollTimer = null;
        }

        setRunning(true);
        renderResults([]);
        setLog('正在提交 workflow');

        try {
            const payload = await requestJson(API.prompt, {
                method: 'POST',
                body: JSON.stringify({
                    workflow: State.workflow,
                    clientId: 'matchdrawer-web',
                }),
            });
            const promptId = payload.prompt_id || payload.promptId;
            if (!promptId) {
                throw new Error('后端未返回 prompt_id');
            }
            State.promptId = promptId;
            setLog(`已提交任务: ${promptId}`);
            pollHistory(promptId);
        } catch (error) {
            setLog(`运行失败: ${error.message}`);
            setRunning(false);
        }
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
            DOM.installBtn.addEventListener('click', () => installRuntime());
        }
        if (DOM.startBtn) {
            DOM.startBtn.addEventListener('click', () => startRuntime());
        }
        if (DOM.runBtn) {
            DOM.runBtn.addEventListener('click', () => {
                runWorkflow();
            });
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
        installRuntime,
        startRuntime,
        runWorkflow,
        pollHistory,
        _state: State,
        _api: API,
    };
})();

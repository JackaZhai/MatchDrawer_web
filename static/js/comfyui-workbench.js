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
        installingRuntime: false,
        startingRuntime: false,
        pendingConnection: null,
        drag: null,
        imageSource: null,
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
        height: 104,
        padding: 96,
        minWidth: 720,
        minHeight: 480,
    };

    const IMAGE_SOURCE_DEFAULTS = {
        provider: 'grsai',
        imageProvider: 'grsai',
        model: 'nano-banana-pro',
        imageModel: 'nano-banana-pro',
        imageSize: '1K',
    };
    const COMFY_SOURCE_KEY = 'comfyui_workbench_image_source_v1';

    const LINK_INPUT_PORTS = {
        GrsAINanoBananaTextImage: ['image1', 'image2'],
        PreviewImage: ['images'],
        SaveImage: ['images'],
    };

    const API = {
        status: '/api/comfyui/status',
        importWorkflow: '/api/comfyui/workflows/import',
        starterWorkflow: (name) => `/api/comfyui/workflows/starter/${encodeURIComponent(name)}`,
        prompt: '/api/comfyui/prompt',
        history: (id) => `/api/comfyui/history/${encodeURIComponent(id)}`,
        uploadImage: '/api/comfyui/upload-image',
        runtimeInstall: '/api/comfyui/runtime/install',
        runtimeStart: '/api/comfyui/runtime/start',
        view: (image) => `/api/comfyui/view?filename=${encodeURIComponent(image.filename)}&subfolder=${encodeURIComponent(image.subfolder || '')}&type=${encodeURIComponent(image.type || 'output')}`,
    };

    const DOM = {};
    const RUNTIME_ACTION_HEADERS = {
        'X-ComfyUI-Runtime-Action': 'confirm-local-runtime',
    };

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
        DOM.imageSourceSummary = document.getElementById('comfyImageSourceSummary');
        DOM.sourceProvider = document.getElementById('comfyImageProviderSelect');
        DOM.sourceModel = document.getElementById('comfyImageModelInput');
        DOM.sourceSize = document.getElementById('comfyImageSizeSelect');
    }

    function normalizeImageSource(source) {
        const raw = source || {};
        const provider = String(raw.provider || raw.imageProvider || 'grsai').trim() || IMAGE_SOURCE_DEFAULTS.provider;
        const imageModel = String(raw.imageModel || raw.model || '').trim() || String(raw.imageModelHint || '').trim() || IMAGE_SOURCE_DEFAULTS.imageModel;
        const sizeRaw = String(raw.imageSize || '').trim().toUpperCase() || '';
        const imageSize = ['1K', '2K', '4K'].includes(sizeRaw) ? sizeRaw : IMAGE_SOURCE_DEFAULTS.imageSize;

        return {
            provider,
            imageProvider: provider,
            model: imageModel,
            imageModel,
            imageSize,
        };
    }

    function loadWorkbenchImageSource() {
        if (typeof localStorage === 'undefined') {
            return Object.assign({}, IMAGE_SOURCE_DEFAULTS);
        }
        try {
            const raw = localStorage.getItem(COMFY_SOURCE_KEY);
            if (raw) {
                return normalizeImageSource(JSON.parse(raw));
            }
        } catch (error) {
            console.warn('读取生图工作台模型配置失败:', error);
        }
        return Object.assign({}, IMAGE_SOURCE_DEFAULTS);
    }

    function saveWorkbenchImageSource(source) {
        if (typeof localStorage === 'undefined') return;
        const normalized = normalizeImageSource(source || State.imageSource || IMAGE_SOURCE_DEFAULTS);
        localStorage.setItem(COMFY_SOURCE_KEY, JSON.stringify(normalized));
    }

    function syncImageSourceControls(source) {
        const normalized = normalizeImageSource(source || State.imageSource || IMAGE_SOURCE_DEFAULTS);
        if (DOM.sourceProvider) {
            const hasProviderOption = Array.from(DOM.sourceProvider.options || [])
                .some((option) => option.value === normalized.provider);
            if (!hasProviderOption) {
                const option = document.createElement('option');
                option.value = normalized.provider;
                option.textContent = normalized.provider;
                DOM.sourceProvider.appendChild(option);
            }
            DOM.sourceProvider.value = normalized.provider;
        }
        if (DOM.sourceModel) DOM.sourceModel.value = normalized.imageModel;
        if (DOM.sourceSize) DOM.sourceSize.value = normalized.imageSize;
    }

    function readWorkbenchImageSourceFromControls() {
        return normalizeImageSource({
            provider: DOM.sourceProvider ? DOM.sourceProvider.value : (State.imageSource && State.imageSource.provider),
            imageModel: DOM.sourceModel ? DOM.sourceModel.value : (State.imageSource && State.imageSource.imageModel),
            imageSize: DOM.sourceSize ? DOM.sourceSize.value : (State.imageSource && State.imageSource.imageSize),
        });
    }

    function renderImageSourceSummary(source = null) {
        if (!DOM.imageSourceSummary) return;
        const normalized = normalizeImageSource(source || State.imageSource || IMAGE_SOURCE_DEFAULTS);
        DOM.imageSourceSummary.textContent = `当前工作台模型：${normalized.provider} / ${normalized.imageModel} / ${normalized.imageSize}`;
    }

    function applySourceToGrsaiNode(node, source) {
        if (!node || node.classType !== 'GrsAINanoBananaTextImage') return false;
        const workflowInputs = ensureWorkflowInputs(node.id);
        if (!workflowInputs) return false;

        const normalizedSource = normalizeImageSource(source);
        const providerKeyExists = Object.prototype.hasOwnProperty.call(workflowInputs, 'provider');
        const changed = (
            workflowInputs.model !== normalizedSource.imageModel
            || workflowInputs.imageSize !== normalizedSource.imageSize
            || (providerKeyExists && workflowInputs.provider !== normalizedSource.provider)
        );

        workflowInputs.model = normalizedSource.imageModel;
        workflowInputs.imageSize = normalizedSource.imageSize;
        if (Object.prototype.hasOwnProperty.call(workflowInputs, 'provider')) {
            workflowInputs.provider = normalizedSource.provider;
        }

        if (!node.inputs || typeof node.inputs !== 'object') {
            node.inputs = {};
        }
        node.inputs.model = normalizedSource.imageModel;
        node.inputs.imageSize = normalizedSource.imageSize;
        if (Object.prototype.hasOwnProperty.call(node.inputs, 'provider')) {
            node.inputs.provider = normalizedSource.provider;
        }

        return changed;
    }

    function applyImageSourceToWorkflow(source = null) {
        const normalized = normalizeImageSource(source || readWorkbenchImageSourceFromControls());
        let changed = false;
        State.imageSource = normalized;
        syncImageSourceControls(normalized);
        saveWorkbenchImageSource(normalized);

        if (!State.workflow || !Array.isArray(State.nodes)) {
            renderImageSourceSummary(normalized);
            return { source: normalized, changed: false };
        }

        State.nodes.forEach((node) => {
            changed = applySourceToGrsaiNode(node, normalized) || changed;
        });

        renderImageSourceSummary(normalized);
        if (changed) {
            if (DOM.panel) {
                renderPropertyPanel();
            }
        }

        return {
            source: normalized,
            changed,
        };
    }

    async function requestJson(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        };
        const response = await fetch(url, {
            credentials: 'same-origin',
            ...options,
            headers,
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

    function uniqueValues(values) {
        return Array.from(new Set(values.filter((value) => value !== null && value !== undefined && value !== '')));
    }

    function workflowNode(nodeId) {
        return State.workflow && State.workflow[nodeId] && typeof State.workflow[nodeId] === 'object'
            ? State.workflow[nodeId]
            : null;
    }

    function ensureWorkflowInputs(nodeId) {
        const node = workflowNode(nodeId);
        if (!node) return null;
        node.inputs = node.inputs && typeof node.inputs === 'object' ? node.inputs : {};
        return node.inputs;
    }

    function ensureWorkflowMeta(nodeId) {
        const node = workflowNode(nodeId);
        if (!node) return null;
        node._meta = node._meta && typeof node._meta === 'object' ? node._meta : {};
        return node._meta;
    }

    function inputPortNames(node) {
        const inputs = node && node.inputs && typeof node.inputs === 'object' ? node.inputs : {};
        const linkedInputs = Object.entries(inputs)
            .filter((entry) => Array.isArray(entry[1]))
            .map((entry) => entry[0]);
        const candidates = LINK_INPUT_PORTS[node && node.classType] || [];
        return uniqueValues([...linkedInputs, ...candidates]);
    }

    function outputPortIndexes(node) {
        const nodeId = node && node.id;
        const indexes = State.links
            .filter((link) => link.fromNode === nodeId)
            .map((link) => Number.isFinite(Number(link.fromOutput)) ? Number(link.fromOutput) : 0);
        return uniqueValues([0, ...indexes]).sort((a, b) => a - b);
    }

    function nodeHeight(node) {
        const portRows = Math.max(inputPortNames(node).length, outputPortIndexes(node).length, 1);
        return Math.max(NODE_CARD.height, 58 + portRows * 24);
    }

    function portY(index) {
        return 42 + index * 24;
    }

    function inputPortY(node, inputName) {
        const index = Math.max(0, inputPortNames(node).indexOf(inputName));
        return portY(index);
    }

    function outputPortY(node, outputIndex = 0) {
        const index = Math.max(0, outputPortIndexes(node).indexOf(Number(outputIndex) || 0));
        return portY(index);
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
                maxY: Math.max(result.maxY, position.y + nodeHeight(node)),
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

    async function normalizeWorkflow(workflow, sourceLabel = 'workflow') {
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
        applyImageSourceToWorkflow();
        renderCanvas();
        renderPropertyPanel();
        setLog(`已载入 ${sourceLabel}：${payload.nodeCount || State.nodes.length} 个节点`);
        return payload;
    }

    async function importWorkflowFile(file) {
        const text = await file.text();
        const workflow = JSON.parse(text);
        await normalizeWorkflow(workflow, file.name || 'workflow');
    }

    async function loadTemplateWorkflow(name) {
        try {
            setLog('正在加载内置 workflow');
            const payload = await requestJson(API.starterWorkflow(name));
            await normalizeWorkflow(payload.workflow, payload.name || name);
        } catch (error) {
            setLog(`模板加载失败: ${error.message}`);
        }
    }

    function inputPortMarkup(node) {
        return inputPortNames(node).map((inputName, index) => `
            <button type="button"
                    class="comfy-port comfy-input-port"
                    data-port-type="input"
                    data-port-node-id="${escapeHtml(node.id)}"
                    data-input-name="${escapeHtml(inputName)}"
                    style="top:${portY(index)}px"
                    title="输入 ${escapeHtml(inputName)}">
                <span>${escapeHtml(inputName)}</span>
            </button>
        `).join('');
    }

    function outputPortMarkup(node) {
        return outputPortIndexes(node).map((outputIndex, index) => `
            <button type="button"
                    class="comfy-port comfy-output-port"
                    data-port-type="output"
                    data-port-node-id="${escapeHtml(node.id)}"
                    data-output-index="${escapeHtml(outputIndex)}"
                    style="top:${portY(index)}px"
                    title="输出 ${escapeHtml(outputIndex)}">
                <span>${escapeHtml(outputIndex)}</span>
            </button>
        `).join('');
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
            const connecting = State.pendingConnection && State.pendingConnection.nodeId === node.id ? ' is-connecting' : '';
            return `
                <div role="button"
                     tabindex="0"
                     class="comfy-node-card comfy-node-${kindClass}${selected}${connecting}"
                     data-node-id="${escapeHtml(node.id)}"
                     style="left:${position.x}px;top:${position.y}px;height:${nodeHeight(node)}px">
                    ${inputPortMarkup(node)}
                    <div class="comfy-node-body">
                        <span class="comfy-node-title">${escapeHtml(node.title || node.classType || node.id)}</span>
                        <span class="comfy-node-meta">#${escapeHtml(node.id)} · ${escapeHtml(node.classType || 'Unknown')}</span>
                    </div>
                    ${outputPortMarkup(node)}
                </div>
            `;
        }).join('');

        DOM.canvas.querySelectorAll('[data-node-id]').forEach((element) => {
            element.addEventListener('click', () => selectNode(element.getAttribute('data-node-id')));
            element.addEventListener('pointerdown', beginNodeDrag);
        });
        DOM.canvas.querySelectorAll('[data-port-type]').forEach((element) => {
            element.addEventListener('pointerdown', (event) => event.stopPropagation());
            element.addEventListener('click', handlePortClick);
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
            const x1 = from.x + NODE_CARD.width;
            const y1 = from.y + outputPortY(source.node, link.fromOutput);
            const x2 = to.x;
            const y2 = to.y + inputPortY(target.node, link.toInput);
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

    function findNode(nodeId) {
        return State.nodes.find((node) => node.id === nodeId) || null;
    }

    function findNodeIndex(nodeId) {
        return State.nodes.findIndex((node) => node.id === nodeId);
    }

    function syncNodePositionToWorkflow(nodeId, position) {
        const meta = ensureWorkflowMeta(nodeId);
        if (meta) {
            meta.position = {
                x: position.x,
                y: position.y,
            };
        }
    }

    function moveNode(nodeId, x, y, options = {}) {
        const node = findNode(nodeId);
        if (!node) return null;

        const position = {
            x: Math.round(Number(x) || 0),
            y: Math.round(Number(y) || 0),
        };
        node.position = position;
        syncNodePositionToWorkflow(nodeId, position);

        if (options.render !== false) {
            renderCanvas();
            renderPropertyPanel();
        } else {
            renderLinks();
        }
        return position;
    }

    function syncNodeInputToWorkflow(nodeId, inputName, value) {
        const inputs = ensureWorkflowInputs(nodeId);
        if (inputs) {
            inputs[inputName] = Array.isArray(value) ? [...value] : value;
        }
    }

    function connectNodes(connection) {
        if (!connection || !connection.fromNode || !connection.toNode || !connection.toInput) {
            return null;
        }
        if (connection.fromNode === connection.toNode) {
            setLog('不能连接到同一个节点');
            State.pendingConnection = null;
            renderCanvas();
            return null;
        }

        const source = findNode(connection.fromNode);
        const target = findNode(connection.toNode);
        if (!source || !target) return null;

        const fromOutput = Number.isFinite(Number(connection.fromOutput)) ? Number(connection.fromOutput) : 0;
        const linkValue = [connection.fromNode, fromOutput];
        target.inputs = target.inputs && typeof target.inputs === 'object' ? target.inputs : {};
        target.inputs[connection.toInput] = linkValue;
        syncNodeInputToWorkflow(connection.toNode, connection.toInput, linkValue);

        State.links = State.links
            .filter((link) => !(link.toNode === connection.toNode && link.toInput === connection.toInput));
        const link = {
            fromNode: connection.fromNode,
            fromOutput,
            toNode: connection.toNode,
            toInput: connection.toInput,
        };
        State.links.push(link);
        State.pendingConnection = null;
        renderCanvas();
        renderPropertyPanel();
        setLog(`已连接 #${connection.fromNode} → #${connection.toNode}.${connection.toInput}`);
        return link;
    }

    function startConnection(nodeId, outputIndex = 0) {
        State.pendingConnection = {
            nodeId,
            outputIndex: Number.isFinite(Number(outputIndex)) ? Number(outputIndex) : 0,
        };
        setLog(`选择目标输入端口连接 #${nodeId}`);
        renderCanvas();
    }

    function handlePortClick(event) {
        event.preventDefault();
        event.stopPropagation();

        const port = event.currentTarget;
        const portType = port.getAttribute('data-port-type');
        const nodeId = port.getAttribute('data-port-node-id');
        if (portType === 'output') {
            startConnection(nodeId, port.getAttribute('data-output-index') || 0);
            return;
        }

        if (portType === 'input') {
            const inputName = port.getAttribute('data-input-name');
            if (!State.pendingConnection) {
                setLog('先点击一个输出端口，再点击输入端口');
                return;
            }
            connectNodes({
                fromNode: State.pendingConnection.nodeId,
                fromOutput: State.pendingConnection.outputIndex,
                toNode: nodeId,
                toInput: inputName,
            });
        }
    }

    function updateDraggedNodeElement() {
        const drag = State.drag;
        if (!drag || !drag.element) return;
        const node = findNode(drag.nodeId);
        const index = findNodeIndex(drag.nodeId);
        if (!node || index < 0) return;
        const viewport = State.viewport || layoutViewport();
        const position = normalizeNodePosition(node, index, viewport);
        drag.element.style.left = `${position.x}px`;
        drag.element.style.top = `${position.y}px`;
    }

    function handleNodeDrag(event) {
        const drag = State.drag;
        if (!drag) return;

        const dx = event.clientX - drag.startClientX;
        const dy = event.clientY - drag.startClientY;
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
            drag.moved = true;
        }
        moveNode(drag.nodeId, drag.startX + dx, drag.startY + dy, { render: false });
        updateDraggedNodeElement();
        event.preventDefault();
    }

    function endNodeDrag(event) {
        const drag = State.drag;
        if (!drag) return;

        if (typeof document.removeEventListener === 'function') {
            document.removeEventListener('pointermove', handleNodeDrag);
            document.removeEventListener('pointerup', endNodeDrag);
        }
        State.drag = null;
        if (drag.element && typeof drag.element.releasePointerCapture === 'function') {
            drag.element.releasePointerCapture(drag.pointerId);
        }
        if (drag.moved) {
            renderCanvas();
        } else {
            selectNode(drag.nodeId);
        }
        event.preventDefault();
    }

    function beginNodeDrag(event) {
        if (event.button !== undefined && event.button !== 0) return;
        const target = event.target;
        if (target && typeof target.closest === 'function' && target.closest('[data-port-type]')) {
            return;
        }

        const element = event.currentTarget;
        const nodeId = element.getAttribute('data-node-id');
        const node = findNode(nodeId);
        if (!node) return;

        const position = nodePosition(node);
        State.drag = {
            nodeId,
            element,
            pointerId: event.pointerId,
            startClientX: event.clientX,
            startClientY: event.clientY,
            startX: position.x,
            startY: position.y,
            moved: false,
        };
        if (typeof element.setPointerCapture === 'function') {
            element.setPointerCapture(event.pointerId);
        }
        if (typeof document.addEventListener === 'function') {
            document.addEventListener('pointermove', handleNodeDrag);
            document.addEventListener('pointerup', endNodeDrag);
        }
        event.preventDefault();
    }

    function isLoadImageNode(node) {
        const inputs = node && node.inputs && typeof node.inputs === 'object' ? node.inputs : {};
        return !!node && (node.classType === 'LoadImage' || Object.prototype.hasOwnProperty.call(inputs, 'image'));
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
            return '';
        }

        return `<form class="comfy-input-form">${fields.join('')}</form>`;
    }

    function renderLoadImageInputs(node) {
        if (!isLoadImageNode(node)) return '';
        const inputs = node && node.inputs && typeof node.inputs === 'object' ? node.inputs : {};
        const currentImage = inputs.image || '';
        return `
            <div class="comfy-image-upload">
                <div class="comfy-image-upload-label">参考图</div>
                <div class="comfy-current-image">${currentImage ? `当前：${escapeHtml(currentImage)}` : '尚未选择图片'}</div>
                <label class="comfy-upload-button">
                    <input type="file" accept="image/*" data-comfy-image-upload>
                    <span>上传图片</span>
                </label>
            </div>
        `;
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

    function readFileAsDataUrl(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(reader.error || new Error('图片读取失败'));
            reader.readAsDataURL(file);
        });
    }

    async function uploadImageForSelectedNode(file) {
        if (!file) return;
        const node = selectedNode();
        if (!node) return;

        setLog('正在上传参考图');
        const image = await readFileAsDataUrl(file);
        const result = await requestJson(API.uploadImage, {
            method: 'POST',
            body: JSON.stringify({
                image,
                filename: file.name || 'input.png',
            }),
        });
        const uploadedName = result.name || result.filename;
        if (!uploadedName) {
            throw new Error('后端未返回上传文件名');
        }

        updateSelectedNodeInput('image', uploadedName);
        renderPropertyPanel();
        setLog(`已上传参考图: ${uploadedName}`);
    }

    function renderPropertyPanel() {
        if (!DOM.panel) return;

        const node = selectedNode();
        if (!node) {
            DOM.panel.className = 'comfy-property-empty';
            DOM.panel.innerHTML = '选择一个节点';
            return;
        }

        const uploadEditor = renderLoadImageInputs(node);
        const inputEditor = renderKnownGrsaiInputs(node);
        const editorMarkup = uploadEditor || inputEditor
            ? `${uploadEditor}${inputEditor}`
            : '<div class="comfy-input-empty">无可编辑输入</div>';

        DOM.panel.className = 'comfy-property-preview';
        DOM.panel.innerHTML = `
            <div class="comfy-property-node-title">${escapeHtml(node.title || node.classType || node.id)}</div>
            <div class="comfy-property-node-meta">#${escapeHtml(node.id)} · ${escapeHtml(node.classType || 'Unknown')} · ${escapeHtml(nodeKindLabel(node.kind))}</div>
            ${editorMarkup}
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

        const imageUpload = DOM.panel.querySelector('[data-comfy-image-upload]');
        if (imageUpload) {
            imageUpload.addEventListener('change', (event) => {
                const file = event.target.files && event.target.files[0];
                if (file) {
                    uploadImageForSelectedNode(file).catch((error) => {
                        setLog(`上传失败: ${error.message}`);
                    });
                }
                imageUpload.value = '';
            });
        }
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
        if (State.installingRuntime) return;

        State.installingRuntime = true;
        if (DOM.installBtn) {
            DOM.installBtn.disabled = true;
        }
        setLog('开始安装 ComfyUI，本步骤会下载 ComfyUI 和 ComfyUI-GrsAI');
        try {
            const result = await requestJson(API.runtimeInstall, {
                method: 'POST',
                headers: RUNTIME_ACTION_HEADERS,
                body: '{}',
            });
            setLog(`安装状态: ${result.state || '完成'}`);
            await refreshStatus();
        } catch (error) {
            setLog(`安装失败: ${error.message}`);
        } finally {
            State.installingRuntime = false;
            if (DOM.installBtn) {
                DOM.installBtn.disabled = false;
            }
        }
    }

    async function startRuntime() {
        if (State.startingRuntime) return;

        State.startingRuntime = true;
        if (DOM.startBtn) {
            DOM.startBtn.disabled = true;
        }
        setLog('正在启动 ComfyUI');
        try {
            await requestJson(API.runtimeStart, {
                method: 'POST',
                headers: RUNTIME_ACTION_HEADERS,
                body: '{}',
            });
            setLog('启动请求已发送，正在检查连接状态');
            window.setTimeout(refreshStatus, 2500);
        } catch (error) {
            setLog(`启动失败: ${error.message}`);
        } finally {
            State.startingRuntime = false;
            if (DOM.startBtn) {
                DOM.startBtn.disabled = false;
            }
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
        applyImageSourceToWorkflow();
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
        [DOM.sourceProvider, DOM.sourceModel, DOM.sourceSize].forEach((element) => {
            if (!element) return;
            const eventName = element === DOM.sourceModel ? 'input' : 'change';
            element.addEventListener(eventName, () => {
                applyImageSourceToWorkflow(readWorkbenchImageSourceFromControls());
            });
        });
        if (DOM.root) {
            DOM.root.querySelectorAll('[data-template]').forEach((button) => {
                button.addEventListener('click', () => loadTemplateWorkflow(button.getAttribute('data-template')));
            });
        }
    }

    function init() {
        cacheDom();
        if (!DOM.root || State.initialized) return;
        State.initialized = true;
        State.imageSource = loadWorkbenchImageSource();
        syncImageSourceControls(State.imageSource);
        bindEvents();
        renderImageSourceSummary(State.imageSource);
        refreshStatus();
    }

    window.ComfyUIWorkbench = {
        init,
        refreshStatus,
        installRuntime,
        startRuntime,
        loadTemplateWorkflow,
        uploadImageForSelectedNode,
        setWorkbenchImageSource: applyImageSourceToWorkflow,
        loadWorkbenchImageSource,
        moveNode,
        connectNodes,
        runWorkflow,
        pollHistory,
        _state: State,
        _api: API,
    };
})();

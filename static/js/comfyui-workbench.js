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

    function bindEvents() {
        if (DOM.importBtn && DOM.importInput) {
            DOM.importBtn.addEventListener('click', () => DOM.importInput.click());
            DOM.importInput.addEventListener('change', () => {
                setLog('Workflow 导入功能待接入');
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

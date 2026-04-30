/**
 * GPT Image Playground - 画图工作台
 * 参考 GPT_Image_Playground 设计，集成到 MatchDrawer
 */

(function () {
    'use strict';

    // ===== 常量 =====
    const STORAGE_KEY = 'gpt_image_tasks_v1';
    const SETTINGS_KEY = 'gpt_image_settings_v1';
    const MAX_TASKS = 200;
    const API_MAX_IMAGES = 16;
    const POLL_INTERVAL_MS = 3000;

    // 默认参数
    const DEFAULT_PARAMS = {
        model: 'gpt-image-1',
        size: '1024x1024',
        quality: 'high',
        output_format: 'png',
        output_compression: null,
        moderation: 'auto',
        n: 1,
    };

    const SIZE_OPTIONS = [
        { value: '1024x1024', label: '1024 x 1024', ratio: '1:1' },
        { value: '1024x1536', label: '1024 x 1536', ratio: '2:3' },
        { value: '1536x1024', label: '1536 x 1024', ratio: '3:2' },
        { value: 'auto', label: '自动', ratio: 'auto' },
    ];

    const QUALITY_OPTIONS = [
        { value: 'auto', label: '自动' },
        { value: 'low', label: '低' },
        { value: 'medium', label: '中' },
        { value: 'high', label: '高' },
    ];

    const FORMAT_OPTIONS = [
        { value: 'png', label: 'PNG' },
        { value: 'jpeg', label: 'JPEG' },
        { value: 'webp', label: 'WebP' },
    ];

    const MODEL_OPTIONS = [
        { value: 'gpt-image-1', label: 'GPT Image 1' },
        { value: 'dall-e-3', label: 'DALL-E 3' },
        { value: 'gpt-image-1.5', label: 'GPT Image 1.5' },
    ];

    // ===== 状态 =====
    const State = {
        tasks: [],
        inputImages: [],
        prompt: '',
        params: { ...DEFAULT_PARAMS },
        settings: loadSettings(),
        isGenerating: false,
        activeTaskId: null,
        pollTimer: null,
        dragCounter: 0,
        imageCache: new Map(),
    };

    // ===== 存储 =====
    function loadSettings() {
        try {
            const raw = localStorage.getItem(SETTINGS_KEY);
            if (raw) {
                const parsed = JSON.parse(raw);
                return {
                    apiProtocol: parsed.apiProtocol || 'images',
                    requestMode: parsed.requestMode || 'direct',
                    baseUrl: parsed.baseUrl || '',
                    apiKey: parsed.apiKey || '',
                };
            }
        } catch { }
        return {
            apiProtocol: 'images',
            requestMode: 'direct',
            baseUrl: '',
            apiKey: '',
        };
    }

    function saveSettings() {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(State.settings));
    }

    function loadTasks() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) {
                    // 清理过期任务（30天）
                    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
                    State.tasks = parsed.filter(t => t.createdAt > cutoff);
                    return;
                }
            }
        } catch { }
        State.tasks = [];
    }

    function saveTasks() {
        // 限制最大任务数
        if (State.tasks.length > MAX_TASKS) {
            State.tasks = State.tasks.slice(0, MAX_TASKS);
        }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(State.tasks));
    }

    function addTask(task) {
        State.tasks.unshift(task);
        saveTasks();
        renderGallery();
    }

    function updateTask(taskId, updates) {
        const idx = State.tasks.findIndex(t => t.id === taskId);
        if (idx >= 0) {
            State.tasks[idx] = { ...State.tasks[idx], ...updates, updatedAt: Date.now() };
            saveTasks();
            renderGallery();
        }
    }

    function removeTask(taskId) {
        State.tasks = State.tasks.filter(t => t.id !== taskId);
        saveTasks();
        renderGallery();
    }

    // ===== 工具函数 =====
    function generateId() {
        return 'task_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
    }

    function formatTime(ts) {
        if (!ts) return '';
        const d = new Date(ts);
        return d.toLocaleString('zh-CN', {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /** 仅转义引号，用于 HTML 属性值（不破坏 URL 中的 &） */
    function escapeAttr(str) {
        if (!str) return '';
        return str.replace(/"/g, '&quot;');
    }

    async function fileToDataUrl(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    async function blobToDataUrl(blob) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.readAsDataURL(blob);
        });
    }

    // ===== API 调用 =====
    function getApiHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        // 优先使用后端管理的 Key
        const apiKey = window.apiService && window.apiService.apiKey ? window.apiService.apiKey : State.settings.apiKey;
        if (apiKey) {
            headers['Authorization'] = `Bearer ${apiKey}`;
        }
        return headers;
    }

    function getApiBaseUrl() {
        // 优先使用后端配置的主机
        if (window.apiService && window.apiService.apiHost) {
            return window.apiService.apiHost.replace(/\/+$/, '');
        }
        const custom = (State.settings.baseUrl || '').trim();
        if (custom) {
            return custom.replace(/\/+$/, '');
        }
        return '';
    }

    async function callImagesGenerations(payload) {
        const baseUrl = getApiBaseUrl();
        if (!baseUrl) {
            throw new Error('未配置 API 地址，请先在 API 设置中添加密钥');
        }

        const url = `${baseUrl}/v1/images/generations`;
        const response = await fetch(url, {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const text = await response.text().catch(() => '');
            let msg = `HTTP ${response.status}`;
            try {
                const err = JSON.parse(text);
                msg = err.error?.message || err.message || msg;
            } catch { }
            throw new Error(msg);
        }

        return await response.json();
    }

    async function callResponsesApi(payload) {
        const baseUrl = getApiBaseUrl();
        if (!baseUrl) {
            throw new Error('未配置 API 地址，请先在 API 设置中添加密钥');
        }

        const url = `${baseUrl}/v1/responses`;
        const response = await fetch(url, {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const text = await response.text().catch(() => '');
            let msg = `HTTP ${response.status}`;
            try {
                const err = JSON.parse(text);
                msg = err.error?.message || err.message || msg;
            } catch { }
            throw new Error(msg);
        }

        // 处理 SSE 流式响应
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('text/event-stream')) {
            return { _stream: true, response };
        }

        return await response.json();
    }

    async function parseStreamResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let resultText = '';
        let imageUrls = [];

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || !trimmed.startsWith('data:')) continue;
                const data = trimmed.slice(5).trim();
                if (data === '[DONE]') continue;
                try {
                    const parsed = JSON.parse(data);
                    // 提取文本
                    const delta = parsed.output?.[0]?.content?.[0]?.text ||
                        parsed.choices?.[0]?.delta?.content || '';
                    if (delta) resultText += delta;
                    // 提取图片
                    if (parsed.output?.[0]?.content) {
                        for (const c of parsed.output[0].content) {
                            if (c.type === 'image_url' && c.image_url?.url) {
                                imageUrls.push(c.image_url.url);
                            }
                        }
                    }
                } catch { }
            }
        }

        return { text: resultText, imageUrls };
    }

    // ===== 提交任务 =====
    async function submitGeneration() {
        if (State.isGenerating) return;

        const prompt = State.prompt.trim();
        const hasImages = State.inputImages.length > 0;
        if (!prompt && !hasImages) {
            showToast('请输入提示词或上传参考图', 'warning');
            return;
        }

        const apiKey = window.apiService && window.apiService.apiKey ? window.apiService.apiKey : State.settings.apiKey;
        if (!apiKey) {
            showToast('未配置 API 密钥，请先在 API 设置中添加', 'error');
            if (typeof showPage === 'function') showPage('api-keys');
            return;
        }

        State.isGenerating = true;
        updateSubmitButton();

        const taskId = generateId();
        const task = {
            id: taskId,
            prompt: prompt,
            inputImages: State.inputImages.map(img => ({ ...img })),
            params: { ...State.params },
            status: 'pending',
            createdAt: Date.now(),
            updatedAt: Date.now(),
            resultImages: [],
            error: null,
            protocol: State.settings.apiProtocol,
        };

        addTask(task);
        State.activeTaskId = taskId;

        try {
            if (State.settings.apiProtocol === 'responses') {
                await submitResponses(task);
            } else {
                await submitImagesGenerations(task);
            }
        } catch (error) {
            console.error('生成失败:', error);
            updateTask(taskId, {
                status: 'failed',
                error: error.message || '生成失败',
                updatedAt: Date.now(),
            });
            showToast(`生成失败: ${error.message}`, 'error');
        } finally {
            State.isGenerating = false;
            State.activeTaskId = null;
            updateSubmitButton();
        }
    }

    async function submitImagesGenerations(task) {
        const payload = {
            model: task.params.model,
            prompt: task.prompt,
            n: Math.min(Math.max(task.params.n || 1, 1), 4),
            size: task.params.size === 'auto' ? '1024x1024' : task.params.size,
            quality: task.params.quality,
            output_format: task.params.output_format,
        };

        if (task.params.output_compression != null && task.params.output_format !== 'png') {
            payload.output_compression = task.params.output_compression;
        }

        // 注意：Images API (images/generations) 不支持直接传入参考图
        // 参考图编辑需要使用 images/edits 端点和 multipart/form-data 格式
        // 当前在 Images API 模式下忽略参考图，仅在 Responses API 模式下使用参考图

        updateTask(task.id, { status: 'running' });

        const result = await callImagesGenerations(payload);

        const images = [];
        if (result.data && Array.isArray(result.data)) {
            for (const item of result.data) {
                if (item.url) images.push(item.url);
                if (item.b64_json) images.push(`data:image/png;base64,${item.b64_json}`);
            }
        } else if (result.images && Array.isArray(result.images)) {
            images.push(...result.images);
        }

        updateTask(task.id, {
            status: images.length > 0 ? 'completed' : 'failed',
            resultImages: images,
            error: images.length > 0 ? null : '未返回图片',
            updatedAt: Date.now(),
        });

        if (images.length > 0) {
            showToast(`成功生成 ${images.length} 张图片`, 'success');
        }
    }

    async function submitResponses(task) {
        const content = [];

        // 添加参考图
        for (const img of task.inputImages) {
            if (img.dataUrl) {
                content.push({ type: 'input_image', image_url: img.dataUrl });
            }
        }

        // 添加提示词
        if (task.prompt) {
            content.push({ type: 'text', text: task.prompt });
        }

        const input = content.length > 0 ? [{ role: 'user', content }] : [];

        const payload = {
            model: task.params.model,
            input: input,
            tools: [{ type: 'image_generation' }],
        };

        updateTask(task.id, { status: 'running' });

        const result = await callResponsesApi(payload);

        if (result._stream) {
            const parsed = await parseStreamResponse(result.response);
            const images = parsed.imageUrls || [];
            updateTask(task.id, {
                status: images.length > 0 ? 'completed' : 'failed',
                resultImages: images,
                error: images.length > 0 ? null : '流式响应未返回图片',
                updatedAt: Date.now(),
            });
            if (images.length > 0) showToast(`成功生成 ${images.length} 张图片`, 'success');
        } else {
            const images = [];
            if (result.output) {
                for (const out of result.output) {
                    if (out.content) {
                        for (const c of out.content) {
                            if (c.type === 'image_url' && c.image_url?.url) {
                                images.push(c.image_url.url);
                            }
                        }
                    }
                }
            }
            updateTask(task.id, {
                status: images.length > 0 ? 'completed' : 'failed',
                resultImages: images,
                error: images.length > 0 ? null : '未返回图片',
                updatedAt: Date.now(),
            });
            if (images.length > 0) showToast(`成功生成 ${images.length} 张图片`, 'success');
        }
    }

    // ===== 参考图管理 =====
    async function addInputImage(file) {
        if (State.inputImages.length >= API_MAX_IMAGES) {
            showToast(`参考图数量已达上限（${API_MAX_IMAGES} 张）`, 'warning');
            return;
        }
        try {
            const dataUrl = await fileToDataUrl(file);
            State.inputImages.push({
                id: generateId(),
                dataUrl: dataUrl,
                name: file.name,
                size: file.size,
                type: file.type,
            });
            renderInputImages();
        } catch (err) {
            showToast(`添加图片失败: ${err.message}`, 'error');
        }
    }

    function addInputImageFromUrl(url) {
        if (State.inputImages.length >= API_MAX_IMAGES) {
            showToast(`参考图数量已达上限（${API_MAX_IMAGES} 张）`, 'warning');
            return;
        }
        State.inputImages.push({
            id: generateId(),
            dataUrl: url,
            name: 'URL 图片',
            size: 0,
            type: 'url',
        });
        renderInputImages();
    }

    function removeInputImage(index) {
        State.inputImages.splice(index, 1);
        renderInputImages();
    }

    function clearInputImages() {
        State.inputImages = [];
        renderInputImages();
    }

    // ===== DOM 渲染 =====
    function renderInputImages() {
        const container = document.getElementById('gptInputImagesList');
        if (!container) return;

        if (State.inputImages.length === 0) {
            container.innerHTML = '';
            return;
        }

        let html = '<div class="gpt-input-images-grid">';
        State.inputImages.forEach((img, idx) => {
            const isUrl = img.type === 'url' || /^https?:\/\//i.test(img.dataUrl);
            html += `
                <div class="gpt-input-image-item">
                    <img src="${escapeAttr(img.dataUrl)}" alt="" loading="lazy">
                    <span class="gpt-input-image-badge">${isUrl ? 'URL' : '本地'}</span>
                    <button class="gpt-input-image-remove" data-idx="${idx}" title="移除">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        });
        html += `
            <button class="gpt-input-image-clear" id="gptClearInputImages" title="清空全部">
                <i class="fas fa-trash-alt"></i>
            </button>
        `;
        html += '</div>';

        container.innerHTML = html;

        // 绑定事件
        container.querySelectorAll('.gpt-input-image-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                removeInputImage(parseInt(btn.dataset.idx));
            });
        });

        const clearBtn = container.querySelector('#gptClearInputImages');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                if (confirm('确定要清空全部参考图吗？')) {
                    clearInputImages();
                }
            });
        }
    }

    function renderGallery() {
        const container = document.getElementById('gptGalleryGrid');
        if (!container) return;

        const tasks = State.tasks;
        if (tasks.length === 0) {
            container.innerHTML = `
                <div class="gpt-gallery-empty">
                    <i class="fas fa-image"></i>
                    <p>还没有生成记录</p>
                    <p class="gpt-gallery-empty-hint">在下方输入提示词，点击生成图像开始</p>
                </div>
            `;
            return;
        }

        let html = '<div class="gpt-gallery-grid">';
        tasks.forEach(task => {
            const statusClass = task.status === 'completed' ? 'completed' :
                task.status === 'running' || task.status === 'pending' ? 'running' : 'failed';
            const statusLabel = task.status === 'completed' ? '完成' :
                task.status === 'running' ? '生成中' :
                    task.status === 'pending' ? '排队中' : '失败';
            const hasImage = task.resultImages && task.resultImages.length > 0;
            const previewImg = hasImage ? task.resultImages[0] : '';

            html += `
                <div class="gpt-task-card" data-task-id="${escapeAttr(task.id)}">
                    <div class="gpt-task-card-image">
                        ${hasImage ? `<img src="${escapeAttr(previewImg)}" alt="" loading="lazy" onclick="GPTImage.openLightbox('${escapeAttr(task.id)}', 0)">` :
                    task.status === 'running' || task.status === 'pending' ?
                        `<div class="gpt-task-card-loading"><div class="gpt-spinner"></div></div>` :
                        `<div class="gpt-task-card-error"><i class="fas fa-exclamation-circle"></i></div>`
                }
                    </div>
                    <div class="gpt-task-card-body">
                        <div class="gpt-task-card-prompt">${escapeHtml(task.prompt || '(无提示词)').slice(0, 80)}${(task.prompt || '').length > 80 ? '...' : ''}</div>
                        <div class="gpt-task-card-meta">
                            <span class="gpt-task-card-status ${statusClass}">${statusLabel}</span>
                            <span class="gpt-task-card-time">${formatTime(task.createdAt)}</span>
                        </div>
                        <div class="gpt-task-card-params">
                            <span>${escapeHtml(task.params?.model || 'gpt-image-1')}</span>
                            <span>${escapeHtml(task.params?.size || 'auto')}</span>
                            <span>${escapeHtml(task.params?.quality || 'auto')}</span>
                        </div>
                    </div>
                    <div class="gpt-task-card-actions">
                        ${hasImage ? `
                            <button class="gpt-task-card-action" onclick="GPTImage.downloadImage('${escapeAttr(task.resultImages[0])}')" title="下载">
                                <i class="fas fa-download"></i>
                            </button>
                        ` : ''}
                        <button class="gpt-task-card-action" onclick="GPTImage.reuseTask('${escapeAttr(task.id)}')" title="复用配置">
                            <i class="fas fa-redo"></i>
                        </button>
                        <button class="gpt-task-card-action gpt-task-card-action-danger" onclick="GPTImage.deleteTask('${escapeAttr(task.id)}')" title="删除">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    }

    function updateSubmitButton() {
        const btn = document.getElementById('gptSubmitBtn');
        if (!btn) return;
        if (State.isGenerating) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 生成中...';
        } else {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-magic"></i> 生成图像';
        }
    }

    // ===== 交互功能 =====
    let _activeLightbox = null;
    let _activeEscHandler = null;
    function openLightbox(taskId, imageIndex) {
        const task = State.tasks.find(t => t.id === taskId);
        if (!task || !task.resultImages || !task.resultImages[imageIndex]) return;

        // 关闭已打开的 lightbox
        if (_activeLightbox) {
            _activeLightbox.remove();
            _activeLightbox = null;
        }
        if (_activeEscHandler) {
            document.removeEventListener('keydown', _activeEscHandler);
            _activeEscHandler = null;
        }

        const url = task.resultImages[imageIndex];
        const modal = document.createElement('div');
        modal.className = 'gpt-lightbox';
        modal.innerHTML = `
            <div class="gpt-lightbox-backdrop"></div>
            <div class="gpt-lightbox-content">
                <img src="${escapeAttr(url)}" alt="">
                <button class="gpt-lightbox-close" title="关闭 (Esc)"><i class="fas fa-times"></i></button>
                <div class="gpt-lightbox-toolbar">
                    <button onclick="GPTImage.downloadImage('${escapeAttr(url)}')"><i class="fas fa-download"></i> 下载</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        _activeLightbox = modal;

        const closeModal = () => {
            modal.remove();
            _activeLightbox = null;
            if (_activeEscHandler) {
                document.removeEventListener('keydown', _activeEscHandler);
                _activeEscHandler = null;
            }
        };

        modal.querySelector('.gpt-lightbox-backdrop').addEventListener('click', closeModal);
        modal.querySelector('.gpt-lightbox-close').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        // ESC 键关闭
        _activeEscHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal();
            }
        };
        document.addEventListener('keydown', _activeEscHandler);
    }

    function getImageExt(url, mimeType) {
        if (mimeType) {
            if (mimeType === 'image/jpeg') return 'jpg';
            if (mimeType === 'image/webp') return 'webp';
            if (mimeType === 'image/png') return 'png';
        }
        const match = url.match(/^data:image\/(\w+);/);
        if (match) return match[1] === 'jpeg' ? 'jpg' : match[1];
        return 'png';
    }

    async function downloadImage(url) {
        try {
            // 如果是 data URL 或同源 URL，直接下载
            const isDataUrl = /^data:/i.test(url);
            if (isDataUrl) {
                const ext = getImageExt(url);
                const a = document.createElement('a');
                a.href = url;
                a.download = `gpt-image-${Date.now()}.${ext}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                showToast('下载已开始', 'success');
                return;
            }

            // 跨域图片：尝试 fetch 后下载
            const response = await fetch(url, { mode: 'cors' });
            if (!response.ok) throw new Error('Fetch failed');
            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);
            const ext = getImageExt(url, blob.type);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = `gpt-image-${Date.now()}.${ext}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(blobUrl);
            showToast('下载已开始', 'success');
        } catch (err) {
            // 降级：新标签页打开
            window.open(url, '_blank');
            showToast('已在浏览器中打开图片', 'info');
        }
    }

    function reuseTask(taskId) {
        const task = State.tasks.find(t => t.id === taskId);
        if (!task) return;

        State.prompt = task.prompt || '';
        State.params = { ...DEFAULT_PARAMS, ...task.params };

        const promptEl = document.getElementById('gptPromptInput');
        if (promptEl) promptEl.value = State.prompt;

        // 更新参数 UI
        updateParamUIs();
        showToast('已加载任务配置', 'info');
    }

    function deleteTask(taskId) {
        if (!confirm('确定要删除这条记录吗？')) return;
        removeTask(taskId);
        showToast('已删除', 'info');
    }

    function updateParamUIs() {
        const modelEl = document.getElementById('gptModelSelect');
        const sizeEl = document.getElementById('gptSizeSelect');
        const qualityEl = document.getElementById('gptQualitySelect');
        const formatEl = document.getElementById('gptFormatSelect');
        const nEl = document.getElementById('gptNInput');

        if (modelEl) modelEl.value = State.params.model;
        if (sizeEl) sizeEl.value = State.params.size;
        if (qualityEl) qualityEl.value = State.params.quality;
        if (formatEl) formatEl.value = State.params.output_format;
        if (nEl) nEl.value = State.params.n;
    }

    // ===== Toast =====
    function showToast(message, type = 'info') {
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
            return;
        }
        // 降级实现
        const toast = document.createElement('div');
        toast.className = `gpt-toast gpt-toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('gpt-toast-hide');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // ===== 拖拽处理 =====
    function setupDragDrop() {
        const container = document.getElementById('gptImagePlayground');
        if (!container) return;

        const handleDragEnter = (e) => {
            e.preventDefault();
            e.stopPropagation();
            State.dragCounter++;
            if (e.dataTransfer?.types.includes('Files')) {
                container.classList.add('gpt-drag-over');
            }
        };

        const handleDragLeave = (e) => {
            e.preventDefault();
            e.stopPropagation();
            State.dragCounter--;
            if (State.dragCounter === 0) {
                container.classList.remove('gpt-drag-over');
            }
        };

        const handleDrop = (e) => {
            e.preventDefault();
            e.stopPropagation();
            State.dragCounter = 0;
            container.classList.remove('gpt-drag-over');
            const files = e.dataTransfer?.files;
            if (files) {
                for (const file of files) {
                    if (file.type.startsWith('image/')) {
                        addInputImage(file);
                    }
                }
            }
        };

        document.addEventListener('dragenter', handleDragEnter);
        document.addEventListener('dragover', (e) => e.preventDefault());
        document.addEventListener('dragleave', handleDragLeave);
        document.addEventListener('drop', handleDrop);
    }

    // ===== 粘贴处理 =====
    function setupPaste() {
        document.addEventListener('paste', (e) => {
            // 只在 GPT 画图页面激活时处理粘贴
            if (typeof AppState !== 'undefined' && AppState.currentPage !== 'gpt-image') return;
            const items = e.clipboardData?.items;
            if (!items) return;
            const imageFiles = [];
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    const file = item.getAsFile();
                    if (file) imageFiles.push(file);
                }
            }
            if (imageFiles.length > 0) {
                e.preventDefault();
                for (const file of imageFiles) {
                    addInputImage(file);
                }
            }
        });
    }

    // ===== 设置面板 =====
    function toggleSettings() {
        const panel = document.getElementById('gptSettingsPanel');
        if (!panel) return;
        const isActive = panel.classList.toggle('active');

        // 点击外部关闭
        if (isActive) {
            const outsideClickHandler = (e) => {
                if (!panel.contains(e.target)) {
                    panel.classList.remove('active');
                    document.removeEventListener('click', outsideClickHandler);
                }
            };
            // 延迟绑定，避免立即触发
            setTimeout(() => {
                document.addEventListener('click', outsideClickHandler);
            }, 10);
        }
    }

    function saveGptSettings() {
        const baseUrlEl = document.getElementById('gptSettingsBaseUrl');
        const apiKeyEl = document.getElementById('gptSettingsApiKey');
        const protocolEl = document.getElementById('gptSettingsProtocol');

        if (baseUrlEl) State.settings.baseUrl = baseUrlEl.value.trim();
        if (apiKeyEl) State.settings.apiKey = apiKeyEl.value.trim();
        if (protocolEl) State.settings.apiProtocol = protocolEl.value;

        saveSettings();
        toggleSettings();
        showToast('设置已保存', 'success');
    }

    function loadGptSettingsUI() {
        const baseUrlEl = document.getElementById('gptSettingsBaseUrl');
        const apiKeyEl = document.getElementById('gptSettingsApiKey');
        const protocolEl = document.getElementById('gptSettingsProtocol');

        if (baseUrlEl) baseUrlEl.value = State.settings.baseUrl;
        if (apiKeyEl) apiKeyEl.value = State.settings.apiKey;
        if (protocolEl) protocolEl.value = State.settings.apiProtocol;
    }

    // ===== 导出功能 =====
    async function exportTasks() {
        try {
            const data = {
                version: 1,
                exportedAt: Date.now(),
                tasks: State.tasks,
            };
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `gpt-image-export-${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('导出成功', 'success');
        } catch (err) {
            showToast('导出失败', 'error');
        }
    }

    function importTasks(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                if (data.tasks && Array.isArray(data.tasks)) {
                    State.tasks = data.tasks;
                    saveTasks();
                    renderGallery();
                    showToast(`成功导入 ${data.tasks.length} 条记录`, 'success');
                } else {
                    throw new Error('无效的数据格式');
                }
            } catch (err) {
                showToast(`导入失败: ${err.message}`, 'error');
            }
        };
        reader.readAsText(file);
    }

    // ===== 初始化 =====
    let _initialized = false;
    function init() {
        loadTasks();
        renderGallery();
        renderInputImages();
        if (!_initialized) {
            setupDragDrop();
            setupPaste();
        }
        updateParamUIs();

        if (_initialized) return;
        _initialized = true;

        // 绑定事件
        const promptEl = document.getElementById('gptPromptInput');
        if (promptEl) {
            promptEl.addEventListener('input', (e) => {
                State.prompt = e.target.value;
            });
            promptEl.addEventListener('keydown', (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    e.preventDefault();
                    submitGeneration();
                }
            });
        }

        const submitBtn = document.getElementById('gptSubmitBtn');
        if (submitBtn) {
            submitBtn.addEventListener('click', submitGeneration);
        }

        const fileInput = document.getElementById('gptFileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                for (const file of e.target.files) {
                    if (file.type.startsWith('image/')) {
                        addInputImage(file);
                    }
                }
                fileInput.value = '';
            });
        }

        const attachBtn = document.getElementById('gptAttachBtn');
        if (attachBtn && fileInput) {
            attachBtn.addEventListener('click', () => fileInput.click());
        }

        const urlBtn = document.getElementById('gptUrlBtn');
        if (urlBtn) {
            urlBtn.addEventListener('click', () => {
                const url = prompt('请输入图片 URL:');
                if (url && url.trim()) {
                    addInputImageFromUrl(url.trim());
                }
            });
        }

        const settingsBtn = document.getElementById('gptSettingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                loadGptSettingsUI();
                toggleSettings();
            });
        }

        const settingsSaveBtn = document.getElementById('gptSettingsSaveBtn');
        if (settingsSaveBtn) {
            settingsSaveBtn.addEventListener('click', saveGptSettings);
        }

        const settingsCloseBtn = document.getElementById('gptSettingsCloseBtn');
        if (settingsCloseBtn) {
            settingsCloseBtn.addEventListener('click', toggleSettings);
        }

        const exportBtn = document.getElementById('gptExportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', exportTasks);
        }

        const importBtn = document.getElementById('gptImportBtn');
        const importInput = document.getElementById('gptImportInput');
        if (importBtn && importInput) {
            importBtn.addEventListener('click', () => importInput.click());
            importInput.addEventListener('change', (e) => {
                if (e.target.files[0]) {
                    importTasks(e.target.files[0]);
                }
                importInput.value = '';
            });
        }

        // 参数绑定
        const modelSelect = document.getElementById('gptModelSelect');
        if (modelSelect) {
            modelSelect.addEventListener('change', (e) => {
                State.params.model = e.target.value;
            });
        }

        const sizeSelect = document.getElementById('gptSizeSelect');
        if (sizeSelect) {
            sizeSelect.addEventListener('change', (e) => {
                State.params.size = e.target.value;
            });
        }

        const qualitySelect = document.getElementById('gptQualitySelect');
        if (qualitySelect) {
            qualitySelect.addEventListener('change', (e) => {
                State.params.quality = e.target.value;
            });
        }

        const formatSelect = document.getElementById('gptFormatSelect');
        if (formatSelect) {
            formatSelect.addEventListener('change', (e) => {
                State.params.output_format = e.target.value;
            });
        }

        const nInput = document.getElementById('gptNInput');
        if (nInput) {
            nInput.addEventListener('change', (e) => {
                const val = parseInt(e.target.value);
                State.params.n = isNaN(val) ? 1 : Math.min(Math.max(val, 1), 4);
                nInput.value = State.params.n;
            });
        }
    }

    // ===== 公开 API =====
    window.GPTImage = {
        init,
        openLightbox,
        downloadImage,
        reuseTask,
        deleteTask,
        submitGeneration,
        exportTasks,
        importTasks,
    };

})();

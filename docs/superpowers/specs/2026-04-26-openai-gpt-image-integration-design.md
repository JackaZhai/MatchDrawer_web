# OpenAI GPT Image Integration Design

**Goal**

把 OpenAI 官方 `gpt-image` 图像 API 接入现有 MatchDrawer Web，使用户可以在现有 `图像生成` 页面中选择 `openai` 作为图像提供商，并使用保存在 `API 设置` 中的 OpenAI key 完成文生图与参考图编辑。

基于 2026-04-27 重新核对的 OpenAI 官方文档，本次“先接入官方 gpt-image API”明确以 Images API 为目标，首版支持 `gpt-image-1.5`、`gpt-image-1`、`gpt-image-1-mini`。`gpt-image-2` 当前更适合通过 Responses API 的 `image_generation` 工具接入，不纳入这次最小闭环实现。

**Scope**

- 保持现有页面结构、`/api/draw` 提交入口和结果展示流程不变。
- 在通用 `图像生成` 页面中补全 `openai` 图像 provider 的真实后端分支。
- 首批支持 OpenAI 图像模型：`gpt-image-1.5`、`gpt-image-1`、`gpt-image-1-mini`。
- 支持两种输入模式：
  - 仅文本提示词：调用 OpenAI Images API generation endpoint。
  - 文本提示词 + 参考图：调用 OpenAI Images API edit endpoint。
- 继续保留现有 `PaperBanana` 工作流和其它 provider 行为，不在本次改动中重写。

**Non-Goals**

- 不重做页面布局或交互。
- 不把 `PaperBanana` 迁移到 OpenAI Responses API。
- 不引入新的任务队列系统或数据库表。
- 不在本次改动中新增遮罩编辑、局部涂抹编辑或多轮会话式图像编辑。

**Current State**

- 前端统一通过 `/api/draw` 提交图像任务。
- 后端 [src/services/ai_service.py](/Users/jackzhai/Desktop/SCIdrawer_web/src/services/ai_service.py) 的 `generate_image()` 当前把通用生成和 `PaperBanana` 都收敛到本地 `PaperBanana` 提交链路。
- 前端已经存在 `openai` provider、参考图选择器和多 provider 模型目录，但 `openai` 图像生成没有一条明确的官方 OpenAI 分支。
- 通用页中的参考图目前会转为 data URL 并随提交参数一并发送，适合直接转化为 OpenAI 编辑输入。

**Chosen Approach**

采用“保持现有 UI 和 `/api/draw` 不变，在后端按 `imageProvider === "openai"` 分流”的方案。

这样可以在最小改动范围内完成真实接入：

- 前端操作路径不变，用户学习成本最低。
- `openai` 走官方 Images API，避免继续把 `gpt-image-*` 仅当作兼容模型名处理。
- 非 `openai` provider 和 `PaperBanana` 工作流不受影响，便于回归验证。

**Alternatives Considered**

1. 所有 provider 继续共用 `PaperBanana`/OpenAI-compatible 路径
   - 优点：后端改动最少。
   - 缺点：官方 OpenAI 图像编辑能力、返回格式和后续扩展点会被弱化，不利于长期维护。

2. 新增独立 `/api/openai/images` 接口
   - 优点：职责清晰。
   - 缺点：前端需要新增一套调用路径，与现有生成入口重复，首版收益不高。

3. 直接切到 OpenAI Responses API
   - 优点：后续多轮编辑能力更强。
   - 缺点：超出本次“先跑通官方 `gpt-image`”的范围，且会显著放大实现与测试成本。

**Design**

1. Request routing

- 保持 [src/routes/api_routes.py](/Users/jackzhai/Desktop/SCIdrawer_web/src/routes/api_routes.py) 的 `/api/draw` 不变。
- 在 [src/services/ai_service.py](/Users/jackzhai/Desktop/SCIdrawer_web/src/services/ai_service.py) 中为 `generate_image()` 增加显式分支：
  - 当页面模式是通用生成，且 `image_provider` 为 `openai` 时，走新的 OpenAI 图像生成服务分支。
  - 其它情况继续走现有 `PaperBanana` 提交流程。
- 第一版不改变 `/api/result` 和 `/api/cancel` 的路由签名；OpenAI 分支返回结果时要适配成现有前端可消费的统一结构。

2. OpenAI image service behavior

- 新增一个专门的 OpenAI 图像请求辅助层，职责只包括：
  - 读取当前用户的 OpenAI key/base URL。
  - 根据是否包含参考图决定调用 Images Generations 或 Images Edits。
  - 将 OpenAI 返回的 base64 图像整理成前端预览与下载所需的统一 payload。
- 文本生成时：
  - 调用 OpenAI `v1/images/generations`。
  - 使用模型 `gpt-image-1.5`、`gpt-image-1` 或 `gpt-image-1-mini`。
- 参考图编辑时：
  - 调用 OpenAI `v1/images/edits`。
  - 将前端传来的 data URL 解码为文件内容，以 multipart 方式上传。
  - 第一版只允许 `gpt-image-1.5`、`gpt-image-1`、`gpt-image-1-mini` 这些当前 Images API 明确列出的模型。
- 首版映射规则：
  - `gpt-image-1.5`、`gpt-image-1`、`gpt-image-1-mini` 使用当前已知稳定尺寸档位。
  - 具体尺寸映射在实现阶段以当日官方文档参数为准，先封装在后端服务层，避免前端写死。
- 输出统一使用 base64 图像结果，避免依赖 GPT image 不支持的 URL 返回格式。

3. Frontend adjustments

- 在 [static/js/app.js](/Users/jackzhai/Desktop/SCIdrawer_web/static/js/app.js) 的 provider/model catalog 中，把 `openai` 图像模型补全为：
  - `gpt-image-1.5`
  - `gpt-image-1`
  - `gpt-image-1-mini`
- `grsai` 目录仍可保留当前低价测试模型，但不再把官方 OpenAI 接入依赖到 `grsai` 列表上。
- 通用 `图像生成` 页面继续复用当前参考图上传和 data URL 存储逻辑。
- 前端不新增新的操作控件；第一版继续复用现有 `生成图像`、`下载`、`清空` 流程。

4. Provider configuration

- 更新 [src/services/provider_config_service.py](/Users/jackzhai/Desktop/SCIdrawer_web/src/services/provider_config_service.py) 中 `openai` 的默认图像模型为 `gpt-image-1.5`。
- 保持现有 key 存储与 base URL 逻辑：
  - 默认 base URL 仍为 `https://api.openai.com/v1`
  - 如果用户自定义 OpenAI-compatible base URL，则继续使用用户保存值
- `deepseek`、`openrouter`、`anthropic` 的默认图像模型本次不扩大调整范围，只保证 `openai` 分支真实可用。

5. Unified result shape

- OpenAI 图像分支返回给前端的数据需要尽量贴近当前 `handleImageGenerationComplete()` 的消费方式。
- 响应至少包含：
  - 生成后的图像数据
  - 可用于下载的 MIME 信息或文件名提示
  - 任务成功状态
  - 如果可获得则附带 revised prompt / usage 信息，作为可选字段
- 如果 OpenAI 图像分支采用同步请求，则后端可以在一次 `/api/draw` 调用中直接返回已完成结果，并由前端走现有成功完成逻辑，而不是强制进入长轮询。

6. Error handling

- 缺少 OpenAI key 时，返回明确的 provider-specific 错误，提示用户到 `API 设置` 添加 `openai` key。
- 如果参考图 data URL 解码失败，返回输入校验错误，而不是透传上游异常。
- 上游 OpenAI 错误需要保留核心状态码与错误消息，便于前端提示。
- 当用户选择 `openai` 但误填了不支持的模型名时，应在后端先拦截并返回验证错误。

**Testing**

- 新增后端测试，覆盖：
  - `image_provider == "openai"` 时 `generate_image()` 走 OpenAI 分支。
  - 无参考图时构造 generation 请求。
  - 有参考图时构造 edit 请求。
  - `openai` 默认模型回退为 `gpt-image-1.5`。
  - 缺少 OpenAI key 时返回可读错误。
  - 非 `openai` provider 仍走原有 `PaperBanana` 路径。
- 更新前端/静态目录测试，覆盖：
  - `openai` provider 的模型目录包含 `gpt-image-1.5`、`gpt-image-1`、`gpt-image-1-mini`
  - 现有 `grsai` 模型目录回归不丢失

**Implementation Notes**

- 这一轮优先保证“官方 OpenAI `gpt-image` 可用”，不把同步生成也强行包装成后台任务。
- 如果同步响应与现有轮询流程冲突，优先在前端为即时完成结果增加兼容，而不是把 OpenAI 分支硬塞进本地 job runner。
- 参考图当前已经以 data URL 存在前端状态中，因此不需要先引入文件上传后端存储。
- OpenAI 官方文档当前分成两条能力路径：
  - Images API：适合这次最小闭环接入，当前明确列出 `gpt-image-1.5`、`gpt-image-1`、`gpt-image-1-mini`。
  - Responses API image generation tool：支持 `gpt-image-2` 等更现代的图像工作流，但会引入另一套调用面。
- 这次实现优先选择更小的 Images API 集成面，后续如果需要 `gpt-image-2`，再单独做 Responses API 接入。

**References**

- OpenAI GPT Image 1.5 model page: [developers.openai.com/api/docs/models/gpt-image-1.5](https://developers.openai.com/api/docs/models/gpt-image-1.5)
- OpenAI GPT Image 1 model page: [developers.openai.com/api/docs/models/gpt-image-1](https://developers.openai.com/api/docs/models/gpt-image-1)
- OpenAI GPT Image 1 Mini model page: [developers.openai.com/api/docs/models/gpt-image-1-mini](https://developers.openai.com/api/docs/models/gpt-image-1-mini)
- OpenAI image generation guide: [developers.openai.com/api/docs/guides/image-generation](https://developers.openai.com/api/docs/guides/image-generation)
- OpenAI images API reference: [developers.openai.com/api/reference/resources/images](https://developers.openai.com/api/reference/resources/images)
- OpenAI image generation tool guide: [developers.openai.com/api/docs/guides/tools-image-generation](https://developers.openai.com/api/docs/guides/tools-image-generation)

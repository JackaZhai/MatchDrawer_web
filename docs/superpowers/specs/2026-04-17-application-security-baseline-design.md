# Application Security Baseline Design

**Goal**

为 MatchDrawer 建立上线可用的应用层安全基线，修复当前最直接的高风险问题：默认自动登录、缺少 CSRF、防敏感配置外泄、前端保存敏感信息、弱会话配置、上传与输入校验不足、错误响应泄露内部实现细节。

**Scope**

- 登录、登出、会话管理与登录态校验
- 全站 CSRF 防护
- 前端去敏：不再下发或展示上游接口地址、活动 Base URL、提供商信息
- 前端不再保存任何 API key 或上游连接配置
- API key 存储与使用的应用层约束
- 上传与输入校验增强
- 错误响应与日志边界收紧
- 生产环境启动保护与基础安全响应头

**Non-Goals**

- 不改部署架构，不引入 WAF、反向代理鉴权、SSO、2FA
- 不改业务上的多提供商内部支持能力
- 不在这一轮引入审计中心、操作审批、细粒度 RBAC
- 不处理部署层 HTTPS、Systemd、Nginx、备份与主机加固

**Current Risks**

- `AuthService.is_authenticated()` 和 `require_auth()` 会自动创建默认会话，导致登录保护形同虚设
- `/api/profile` 和首页模板会把 `apiHost` / `activeBaseUrl` 下发给前端
- 前端把 `apiKey` / `chatApiKey` / `apiHost` 写入 `localStorage`
- 所有写接口当前没有 CSRF 防护
- `/logout` 使用 `GET`，可被跨站触发
- 登录页直接预填默认用户名和密码
- 上传校验只检查数量和大小估算，没有验证真实图片内容
- 错误处理会把内部异常细节透传给前端
- 若 `APP_SECRET_KEY` 保持默认值，数据库密钥加密与会话安全都退化

**Design**

## 1. Authentication And Session

- 保留“确保默认用户存在”能力，但只在数据层创建用户，不再自动生成会话
- `AuthService.is_authenticated()` 仅检查：
  - `session["authenticated"] is True`
  - `session["user_id"]` 存在
  - `session["username"]` 存在
- `AuthService.require_auth()` 在未登录时抛出 `AuthenticationError`
- 登录成功时执行：
  - `session.clear()`
  - 写入 `authenticated / user_id / username`
  - 写入登录时间戳
  - `session.permanent = True`
- 登出改为 `POST /logout`，并受 CSRF 校验
- `manual` 页面也纳入登录保护，避免把内部使用说明暴露给匿名访问者
- 登录页不再预填默认账号密码，只保留配置说明

## 2. Session Cookie And App Config

- 在 Flask app 初始化中增加：
  - `SESSION_COOKIE_HTTPONLY = True`
  - `SESSION_COOKIE_SAMESITE = "Lax"`
  - `SESSION_COOKIE_SECURE = True` when production
  - `PERMANENT_SESSION_LIFETIME = 12 hours`
- 增加环境判断：
  - `FLASK_ENV=production` 或显式 `APP_ENV=production` 时，若 `APP_SECRET_KEY` 仍为 `change-me`，应用拒绝启动
  - 开发模式允许默认值，但在日志中打印明显警告

## 3. CSRF Protection

- 新增轻量级 CSRF 服务，基于 session 保存随机 token
- 页面渲染时下发 CSRF token：
  - 登录页表单隐藏字段
  - 主页面通过 `<meta name="csrf-token">` 或 `window.AppConfig.csrfToken`
- 所有状态变更请求必须带 token：
  - `/login`
  - `/logout`
  - `/api/keys`
  - `/api/keys/active`
  - `/api/draw`
  - `/api/result`
  - `/api/cancel`
  - `/api/provider-configs`
- 只读 GET 接口默认不要求 CSRF
- 前端统一在 `fetch` 请求头里附加 `X-CSRF-Token`

## 4. Frontend De-Sensitization

- 首页模板不再下发 `api_host`
- `/api/profile` 不再返回：
  - `apiHost`
  - `activeBaseUrl`
- `/api/keys` 不再返回：
  - `provider`
  - `baseUrl`
- API 设置页从“供应商 + Base URL + API Key”改为“名称 + API Key”最小表单
- 现有多提供商能力保留在服务端内部配置，不对普通前端用户公开
- 首页与设置页不再显示任何上游接口地址
- 模型选择继续使用产品层模型目录，不向前端暴露 provider-route 细节

## 5. Frontend Sensitive Storage Removal

- 前端移除对以下 `localStorage` 项的读写：
  - `apiKey`
  - `chatApiKey`
  - `apiHost`
- 前端 API 服务统一只调用本地 `/api/*`
- 上游调用由服务端完成，前端不再构造第三方请求头
- 保留非敏感 UI 状态存储：主题、语言、页面展示状态、非敏感模型偏好

## 6. API Key Handling

- API key 继续只存数据库加密值，不回传明文
- `serialize_keys()` 仅返回：
  - `id`
  - `name`
  - `mask`
  - `isActive`
  - `createdAt`
- 服务端默认将所有上游路由视为内部实现，不进入前端响应
- 现有 provider/base_url 字段保留在数据库层，作为内部实现细节继续使用
- 当前轮不删除数据库字段，避免破坏兼容性

## 7. Upload And Input Validation

- 参考图校验升级为真实内容校验：
  - 限制最大张数与大小
  - 只接受常见位图 MIME：`image/png`, `image/jpeg`, `image/webp`
  - base64 必须能成功解码
  - 使用 Pillow 验证图片头和像素尺寸
  - 拒绝 SVG、空数据、伪造 MIME
- 增加文本输入约束：
  - prompt/caption 最大长度
  - API key 最小长度与字符规范
  - `draw_id` / `job_id` 仅允许预期字符集
- 对 provider/model 相关字段改成内部兜底，不信任前端自由拼装

## 8. Error Handling And Logging

- `handle_api_errors` 向前端只返回通用错误消息，不再返回 traceback
- `ApiError.to_dict()` 默认不包含 `details`，仅在 `debug=True` 时输出
- 服务端保留完整日志：
  - 时间
  - endpoint
  - user_id
  - error class
  - 安全相关拒绝原因
- 上游 API 失败时，对前端统一收敛为：
  - “请求失败”
  - “服务暂时不可用”
  - “认证失效”
- 不把上游 host、provider、headers、原始响应体直接暴露给前端

## 9. Security Headers

- 在 `after_request` 中统一附加基础响应头：
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Cache-Control: no-store` for authenticated HTML and sensitive API responses
- 本轮不启用 Content-Security-Policy
- 原因：当前模板与脚本结构仍包含较多内联依赖，强行启用 CSP 容易造成生产回归
- CSP 留到后续独立安全迭代处理

**File Design**

- `app.py`
  - 注入生产模式配置、cookie 配置、安全响应头、启动期 secret 校验
- `src/services/auth.py`
  - 移除自动登录，改为真实 session 校验与 session 轮换
- `src/routes/auth_routes.py`
  - 登录表单加 CSRF，登出改为 `POST`
- `src/routes/decorators.py`
  - 增加 CSRF 装饰器，错误输出收敛
- `src/routes/api_routes.py`
  - 去掉 profile/keys 的敏感字段输出
  - 所有写接口接入 CSRF
  - `manual` 增加登录保护
- `src/utils/validation.py`
  - 强化参考图、文本、ID、API key 校验
- `src/utils/errors.py`
  - 错误结构去敏
- `src/utils/encryption.py`
  - 保持现有 Fernet 方案，但依赖更严格的 secret 策略
- `static/js/api-service.js`
  - 不再保存敏感信息到 `localStorage`
  - 统一本地 API 调用 + CSRF header
- `static/js/app.js`
  - 去掉 host/baseUrl/provider 的展示与依赖
  - API 设置页改为最小输入
- `templates/index.html`
  - 下发 CSRF token，移除 host 暴露
- `templates/login.html`
  - 登录表单增加 CSRF，移除默认账号密码预填
- `tests/`
  - 增加未登录、CSRF、前端去敏、上传校验、生产 secret 校验等测试

**Testing**

- 未登录访问 `/` -> 重定向 `/login`
- 未登录访问 `/manual` -> 重定向 `/login`
- 未登录访问 `/api/profile` -> `401`
- 登录表单缺少 CSRF -> 拒绝
- 已登录状态下 API 写请求缺少 CSRF -> `403`
- `/api/profile` 不包含 `apiHost` / `activeBaseUrl`
- `/api/keys` 不包含 `provider` / `baseUrl`
- 登录页不包含默认 `admin` / `banana123` 预填
- 非法图片、超限图片、伪造图片数据被拒绝
- 生产模式下默认 `APP_SECRET_KEY` 启动失败
- 现有品牌与基础功能 smoke tests 继续通过

**Rollout Notes**

- 这是应用层基线，不覆盖部署层 HTTPS、反向代理、主机与备份加固
- 这一轮优先解决“匿名可访问、可伪造请求、可前端读取敏感配置”的问题
- 对现有前端交互会有小幅变动：
  - 登录后才可访问页面
  - 退出登录将改为 POST
  - API 设置页不再展示 provider/base URL

# Auth Management Design

**Goal**

在现有 MatchDrawer 登录能力基础上，补齐一套可长期使用的本地账号系统，覆盖以下四项：

- 开放注册
- 用户自行修改密码
- 记住登录
- 管理员多用户管理

实现后，系统应支持“普通用户注册并使用站点”和“管理员在后台管理用户”这两条路径，同时保持当前前端 RSA 加密登录和后端 bearer token 鉴权模型不被推翻。

**Scope**

- 扩展当前单用户登录为多用户登录。
- 增加用户角色与状态控制。
- 增加注册、改密、刷新登录、退出登录相关接口。
- 增加“记住登录”长期凭证机制。
- 在现有设置页加入管理员用户管理界面。
- 为普通用户增加个人账号安全操作入口。
- 增加必要的数据库迁移与测试覆盖。

**Non-Goals**

- 不做邮箱验证码、短信验证码或第三方 OAuth 登录。
- 不做找回密码、邮件重置链接、双因素认证。
- 不做多租户组织模型。
- 不做复杂设备会话面板或登录审计大屏。
- 不把当前 bearer token 架构改回纯服务端 session-only 模式。

**Current State**

- 当前项目是 Flask + SQLite + Vanilla JS 架构。
- 已有登录页与前端 RSA 公钥加密登录流程。
- 已有短期 bearer token 校验逻辑与 `/api/auth/validate`。
- 当前首页通过前端拦截进入，缺 token 时跳转到 `/login`。
- 当前用户模型只有用户名和密码，不具备角色、状态、最后登录时间等管理字段。
- 当前没有开放注册、改密、remember token、管理员后台。

**Chosen Approach**

采用“双令牌模型”：

- `access token`：短期 token，前端保存在 `localStorage`
- `remember token`：长期 token，仅在用户勾选“记住登录”时签发，通过 `HttpOnly` Cookie 保存

配合多用户表和 remember token 持久化表，实现以下目标：

- 普通登录：只依赖短期 access token
- 记住登录：access token 过期后，前端调用刷新接口，后端依赖 remember cookie 重新签发 access token
- 管理员后台：基于 `role=admin` 控制访问
- 用户禁用/改密/删除：可主动使长期 remember token 失效

这是对现有架构改动最小且边界最清楚的方案。

**Alternatives Considered**

1. 只使用长寿命 JWT，不保存 remember token
   - 优点：实现更快。
   - 缺点：无法精细撤销长期登录，不利于管理员禁用用户和密码变更后的强制退出。

2. 完全回退到服务端 session + cookie
   - 优点：后端集中控制登录态。
   - 缺点：与当前已接入的前端 bearer token 方案不一致，需要返工现有认证流。

3. 直接引入外部身份服务
   - 优点：功能全。
   - 缺点：远超本项目当前规模和部署方式，不符合本地 SQLite 项目的复杂度边界。

**Design**

1. User model

扩展 `users` 表字段：

- `id`
- `username`
- `salt`
- `password_hash`
- `role`：`admin` 或 `user`
- `status`：`active` 或 `disabled`
- `created_at`
- `last_login_at`

行为规则：

- 种子账户 `admin` 为默认管理员。
- 开放注册创建的新用户默认 `role=user`、`status=active`。
- 被禁用用户不能登录、不能刷新 token、不能继续访问受保护接口。

2. Remember token model

新增 `remember_tokens` 表：

- `id`
- `user_id`
- `token_hash`
- `expires_at`
- `created_at`
- `last_used_at`
- `user_agent`

存储规则：

- 只存储 remember token 的哈希值，不明文落库。
- remember token 由后端随机生成，并通过 `HttpOnly` cookie 下发。
- 每次刷新 access token 时更新 `last_used_at`。
- remember token 有固定过期时间，默认 30 天。

3. Authentication model

- 登录成功后总是签发短期 `access token`。
- 当用户勾选“记住登录”时，同时创建 remember token 记录并设置 cookie。
- 前端进入站点时：
  - 若本地已有 access token，则先走 `/api/auth/validate`
  - 若 access token 缺失或已过期，则调用 `/api/auth/refresh`
  - refresh 成功时写入新的 access token
  - refresh 失败时清除本地状态并回到未登录页

安全规则：

- `access token` 继续使用当前签名机制。
- remember token 仅通过 cookie 传输，不暴露给前端 JS。
- 修改密码、管理员重置密码、禁用用户、删除用户时，应失效该用户全部 remember token。

4. Registration flow

前端：

- 在登录页提供“登录 / 注册”切换。
- 注册时校验：
  - 用户名 3-32 位，仅允许字母、数字、下划线、点、中横线
  - 密码 6-64 位
  - 确认密码必须一致
- 用户名和密码仍通过 RSA 公钥加密上传。

后端：

- 新增注册接口。
- 拒绝重复用户名。
- 创建用户后不自动授予管理员权限。
- 注册成功后可直接返回登录成功结果与 token，减少额外一步登录操作。

5. Change password flow

普通用户：

- 在设置页提供“修改密码”表单。
- 必须输入旧密码、新密码、确认密码。
- 后端校验旧密码正确后再写入新密码。

安全行为：

- 改密成功后，当前 access token 失效策略采用“当前请求成功返回，后续要求重新刷新/重新登录”。
- 该用户所有 remember token 立即删除。
- 旧密码必须立即失效。

6. Admin user management

管理员入口放在现有设置页中，仅管理员可见。

第一版操作集：

- 查看用户列表
- 创建用户
- 重置用户密码
- 启用/禁用用户
- 删除用户
- 提升为管理员
- 降级为普通用户

权限保护：

- 普通用户不得访问任何管理员接口。
- 管理员不能禁用自己当前账户。
- 管理员不能删除自己当前账户。
- 不能将最后一个 `active admin` 禁用、删除或降级。
- 被禁用用户即使持有未过期 token，也必须在后续请求中被拒绝。

7. API design

认证接口：

- `POST /api/auth/register`
  - 输入：加密后的 `username`、`password`、`confirmPassword`
  - 输出：注册结果；成功时可直接附带 access token

- `POST /api/auth/login`
  - 输入：加密后的 `username`、`password`、`remember`
  - 输出：登录结果、access token、用户信息
  - 若 `remember=true`，同时设置 remember cookie

- `GET /api/auth/validate`
  - 校验当前 access token

- `POST /api/auth/refresh`
  - 仅依赖 remember cookie
  - 返回新的 access token

- `POST /api/auth/change-password`
  - 普通用户修改自身密码

- `POST /api/auth/logout`
  - 清除 access token 对应前端状态的响应信号
  - 清除 remember cookie
  - 删除当前 remember token 记录

管理员接口：

- `GET /api/admin/users`
- `POST /api/admin/users`
- `PATCH /api/admin/users/<user_id>`
- `POST /api/admin/users/<user_id>/reset-password`
- `DELETE /api/admin/users/<user_id>`

管理员接口返回字段应避免泄露密码哈希、salt、remember token 原文等敏感信息。

8. Frontend changes

登录页 [templates/login.html](/Users/jackzhai/Desktop/SCIdrawer_web/templates/login.html)：

- 增加登录/注册切换
- 增加“记住登录”勾选框
- 注册表单复用当前 RSA 加密流程

主页面 [templates/index.html](/Users/jackzhai/Desktop/SCIdrawer_web/templates/index.html)：

- 保持当前进站拦截逻辑
- 初始化阶段从“validate 失败直接回登录”调整为“先尝试 refresh，再决定是否回登录”

设置页 [templates/index.html](/Users/jackzhai/Desktop/SCIdrawer_web/templates/index.html) 与 [static/js/app.js](/Users/jackzhai/Desktop/SCIdrawer_web/static/js/app.js)：

- 新增“账号安全”分组：
  - 当前用户名
  - 角色展示
  - 修改密码表单
- 新增“用户管理”分组，仅管理员可见：
  - 用户列表表格
  - 新建用户表单
  - 行内启用/禁用/升降级/删除/重置密码操作

9. Migration and compatibility

- 对现有 `users` 表做保守迁移：
  - 若缺少 `role`、`status`、`last_login_at` 字段，则补齐
  - 现有 `admin` 用户自动回填为 `role=admin`、`status=active`
- 新增 `remember_tokens` 表
- 保留当前短期 token 逻辑接口名，减少前端回归范围

10. Error handling

需要明确返回的用户态错误：

- 用户名已存在
- 用户名或密码格式不合法
- 旧密码错误
- 用户已被禁用
- 登录已过期
- 无可用 remember 登录状态
- 权限不足
- 不能删除最后一个管理员
- 不能禁用最后一个管理员
- 不能降级最后一个管理员

前端处理规则：

- `401`：先尝试 refresh；refresh 失败则退出登录
- `403`：保留当前登录态，并提示权限不足
- 管理员危险操作使用明确确认框

**Testing**

后端测试至少覆盖：

- 注册成功
- 重复用户名注册失败
- 非法用户名或密码注册失败
- 登录成功
- 勾选 remember 登录时成功写入 remember cookie
- access token 过期后 refresh 成功
- remember token 过期后 refresh 失败
- 普通用户改密成功且旧密码失效
- 改密后旧 remember token 失效
- 普通用户访问管理员接口返回 `403`
- 管理员创建用户成功
- 管理员禁用用户后该用户访问受保护接口失败
- 禁止删除最后一个管理员
- 禁止禁用最后一个管理员
- 禁止降级最后一个管理员

前端/页面测试至少覆盖：

- 登录页显示登录/注册与 remember 选项
- 设置页普通用户可见改密区，不可见用户管理区
- 设置页管理员可见用户管理区

**Implementation Notes**

- 本次优先做“先跑通，后完善”的最小闭环：
  - 先支持本地用户名密码、多用户、remember、管理员基础管理
  - 不额外叠加找回密码、设备列表、验证码等复杂功能
- remember cookie 建议使用：
  - `HttpOnly`
  - `SameSite=Lax`
  - `Secure` 在生产 HTTPS 环境开启；本地开发根据环境自适应
- 用户列表第一页不需要分页，按当前项目规模直接全量返回即可；若后续用户量变大，再补分页和搜索。

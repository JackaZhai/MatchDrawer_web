# 基于设计模式的 AI 科研绘图 Web 系统综合实验报告

## 评分表

| 考察内容 | 评分标准 | 完成情况说明 | 得分 |
|---|---|---|---|
| 综合性实验：实验内容完成度 | 按设计程序功能完成情况及系统展示效果，实验过程描述较详细，内容齐全，组织合理，描述有逻辑。（30%） | 本实验为自主选题综合项目，完成 MatchDrawer 的主要功能，包括用户认证、API Key 管理、模型配置、AI 图像生成、PaperBanana 专业绘图工作流、任务状态轮询和结果展示下载。报告以设计模式为主线，从选题背景、需求分析、系统设计、代码实现到测试结果完整展开。 |  |
| 实验过程分析 | 按程序设计实现分析详细程度及正确度给分，要求代码有解释分析或流程图。（20%） | 报告结合项目实际代码说明系统分层、模块职责、核心业务流程和设计模式落地方式，并提供系统结构图、数据关系图和业务流程图。 |  |
| 实验结果分析 | 程序输出有结果截图，按要求输出，并有实验结果分析，针对实验过程中存在的问题、不足进行分析。（20%） | 报告预留并嵌入运行截图位置，分别对应首页、API 密钥管理、生成参数、任务运行状态和生成结果，同时分析正常用例、异常用例和系统不足。 |  |
| 实验报告格式 | 按文档格式及文字表达效果给分，要求流利通顺、无错别字。（20%） | 报告严格按照实验目的、实验内容及要求、实验设备及软件、设计方案、代码实现分析、测试结果分析、实验体会组织，层次清晰，表格和图示完整。 |  |
| 实验总结体会 | 按个人体会具体情况给分，要求内容具体、言之有物。（10%） | 总结围绕自主选题、模块划分、设计模式应用、异步任务处理、密钥安全和后续优化展开，内容具体。 |  |
| 综合实验总分 |  |  |  |

## 一、实验目的

本次综合实验的要求是：**自主选题，独立设计并实现一个程序项目，并在项目中体现设计模式理念**。因此，本实验不是完成一个老师指定的小程序，也不是单纯写几个设计模式示例类，而是要围绕一个真实项目完成从选题、需求分析、系统设计、功能实现、测试验证到总结反思的完整过程。

根据综合实验要求，我选择完成 **MatchDrawer** 项目作为本次实验项目。该项目以设计模式思想为指导，围绕 AI 科研绘图场景，实现用户认证、API Key 管理、Provider 适配、图像生成任务管理和 PaperBanana 专业工作流。系统主要目标是让用户可以在浏览器中输入科研绘图需求，配置不同 AI provider 的 API Key 和模型参数，并通过统一任务流程生成科研图表或方法示意图。

本报告是对本人完成 MatchDrawer 项目的系统总结，重点说明：

1. 为什么选择“AI 科研绘图 Web 系统”作为综合实验题目。
2. 项目实现了哪些功能，是否满足一个完整程序项目的要求。
3. 项目整体架构如何设计，前端、后端、数据库和 AI 工作流如何协作。
4. 设计模式理念如何真实落地到代码中，而不是停留在概念罗列。
5. 程序运行结果如何，正常流程和异常流程是否能够正确处理。
6. 通过本次实验，对模块化设计、设计模式和工程实现获得了哪些具体体会。

### 1. 选题背景

在科研学习、论文写作和项目展示中，图表和示意图常用于表达方法流程、模型结构、实验设计和结果分析。传统方式通常需要人工使用绘图软件完成，效率较低，对工具熟练度和审美能力也有一定要求。随着 AI 图像生成和多模态模型的发展，将自然语言描述转化为图像或科研图示成为一个具有实际价值的方向。

因此，我将本次综合实验选题确定为：**基于设计模式的 AI 科研绘图 Web 系统设计与实现**。该选题既有明确应用场景，又具有足够的工程复杂度，能够自然体现设计模式理念。

### 2. 选题意义

本项目具有以下意义：

1. **具有实际应用价值**
   系统面向科研绘图场景，用户可以通过 prompt 描述图像需求，并结合专业工作流生成科研图表，具有真实使用意义。

2. **综合性强**
   项目不是单个算法或命令行脚本，而是包含前端页面、Flask 后端、SQLite 数据库、用户认证、API Key 管理、外部 AI 服务适配、后台任务和 Agent 流水线的完整 Web 应用。

3. **适合体现设计模式**
   项目中存在多个需要抽象、封装和解耦的场景。例如服务对象需要统一获取，不同 provider 返回格式需要适配，长时间运行任务需要传输状态，路由函数需要统一登录校验和异常处理，PaperBanana 多个 Agent 需要统一处理接口。这些都适合用设计模式思想解决。

### 3. 实验目标

本次实验目标如下：

1. 独立完成一个具有实际功能和一定复杂度的综合程序项目。
2. 掌握 Flask Web 项目的组织方式，包括应用入口、路由层、服务层、模型层和前端页面之间的关系。
3. 掌握 SQLite 数据库存储、用户认证、API Key 加密保存、模型配置管理等 Web 应用基础能力。
4. 掌握 AI 图像生成任务的异步处理流程，包括任务提交、后台执行、状态保存、前端轮询和结果展示。
5. 在真实项目中体现并分析设计模式理念，包括工厂模式、单例模式、装饰器模式、外观模式、适配器模式、模板模式、MVC 模式、服务定位器模式、传输对象模式等，并说明这些模式分别解决模块创建、对象复用、接口统一、流程组织和异常拦截等实际问题。
6. 通过测试和结果分析，验证系统功能正确性，并总结系统不足和后续优化方向。

## 二、实验内容及要求

本次综合实验的核心要求可以概括为：**自己选题，自己完成项目，报告中要说明项目设计和实现过程，并体现设计模式如何应用到项目中**。

围绕该要求，本实验完成内容如下：

1. **完成自主选题**
   选择“AI 科研绘图 Web 系统”作为实验题目，项目名称为 MatchDrawer。

2. **完成系统功能设计**
   明确系统需要包含用户认证、API Key 管理、模型配置、AI 图像生成、专业工作流、任务轮询、结果展示和错误处理等功能。

3. **完成后端程序实现**
   使用 Flask 实现 Web 后端，使用 Blueprint 划分认证路由、API 路由和主页面路由，使用服务层封装核心业务逻辑。

4. **完成数据持久化实现**
   使用 SQLite 保存用户、API Key、provider 配置和使用统计信息。API Key 经过加密后存储，前端只展示掩码。

5. **完成前端交互实现**
   使用 HTML、CSS 和 JavaScript 实现页面交互，包括 API Key 配置、生成参数选择、任务提交、状态轮询和结果展示。

6. **完成 AI 生成流程接入**
   将 PaperBanana 专业工作流接入统一 `/api/draw` 和 `/api/result` 接口，通过后台任务执行多 Agent 图像生成流程。

7. **完成设计模式分析**
   结合实际代码说明设计模式如何在项目中体现，重点分析这些模式解决了什么问题，而不是简单罗列模式名称。

8. **完成测试结果分析**
   对系统正常流程和异常流程进行测试，并通过运行截图展示系统功能完成情况。

### 实验实施过程

本项目在实现过程中大体经历了以下阶段：

1. **选题与需求分析阶段**
   确定项目不是写一个简单 demo，而是实现一个可以运行的 AI 科研绘图 Web 系统。需求分析时重点考虑用户实际操作流程：先登录系统，再配置 API Key 和模型，然后输入绘图需求，提交生成任务，等待状态更新，最后查看结果。

2. **架构设计阶段**
   根据功能复杂度将系统拆分为路由层、服务层、模型层、工具层和前端交互层。路由层只负责请求分发，服务层负责编排业务，模型层负责数据对象和持久化，工具层负责加密、校验和错误类型。

3. **设计模式落地阶段**
   在系统设计过程中有意识地引入设计模式理念。例如使用单例和服务定位器统一服务对象获取，使用装饰器统一登录校验和异常处理，使用外观模式封装 AI 调用复杂度，使用适配器模式统一不同服务返回格式，使用模板模式约束不同 Agent 的处理接口。

4. **功能实现阶段**
   按模块逐步实现登录认证、API Key 管理、provider 配置、图像生成任务提交、后台任务执行、任务状态查询和结果文件下载。

5. **调试与测试阶段**
   对正常输入、缺少 API Key、prompt 为空、任务失败、任务取消等情况进行调试，保证系统不仅能跑通成功流程，也能对异常情况给出清晰反馈。

6. **报告整理阶段**
   在项目实现完成后，总结系统功能、模块结构、关键代码、设计模式、运行结果和实验体会，形成综合实验报告。

## 三、实验设备及软件

| 类型 | 配置 |
|---|---|
| 操作系统 | macOS / Linux 均可运行 |
| 后端语言 | Python 3 |
| 后端框架 | Flask |
| 数据库 | SQLite |
| 前端技术 | HTML、CSS、JavaScript，另包含 React + Zustand 的 GPT Image Playground 子项目 |
| 主要第三方库 | Flask、requests、python-dotenv、cryptography、Pillow、google-genai 等 |
| 开发工具 | VS Code / Codex / Terminal |
| 项目位置 | 本地 MatchDrawer 项目目录 |
| 项目名称 | MatchDrawer |

## 四、设计方案

### ㈠ 题目

**基于设计模式的 AI 科研绘图 Web 系统设计与实现**

本题目为自主选题。选题时主要考虑三个方面：

1. 项目应具有实际应用价值，能够解决一个真实场景中的问题。
2. 项目应具有一定综合性，不能只是一个简单函数或小型脚本。
3. 项目应能够自然体现设计模式理念，避免为了凑模式而写模式。

MatchDrawer 满足这些要求。它既是一个可以运行的 AI 绘图 Web 系统，又包含多个需要解耦的模块，例如用户认证、密钥管理、provider 配置、任务状态管理、外部服务适配和 Agent 流水线。因此，本项目适合作为综合实验题目，也适合用来说明设计模式如何在真实工程中解决复杂性。

### ㈡ 设计的主要思路

系统采用前后端协作的 Web 架构。用户通过浏览器访问前端页面，前端将用户输入和配置发送到 Flask 后端。后端通过路由层接收请求，再调用服务层完成业务逻辑。服务层根据需要读取数据库、调用 PaperBanana 专业工作流或外部 AI provider，最后将统一格式的结果返回前端。

整体设计思想是：

1. **路由层只负责请求入口**
   路由函数不直接写复杂业务逻辑，只负责解析请求、获取当前用户、调用服务层并返回响应。

2. **服务层负责业务编排**
   认证、API Key 管理、模型配置、AI 生成、PaperBanana 任务管理都封装在不同 service 中，使业务逻辑清晰。

3. **模型层负责数据表达和持久化**
   用户、API Key、provider 配置、使用统计等都封装为模型类，模型类负责与 SQLite 数据库交互。

4. **工具层负责通用能力**
   加密、参数校验、错误类型等通用能力独立放在 `utils` 中，避免重复实现。

5. **前端负责交互和状态展示**
   前端负责用户输入、按钮事件、任务轮询、进度展示和结果展示，不直接访问数据库或外部 AI 服务。

从设计模式角度看，系统不是先堆叠功能再事后套用模式，而是在架构划分阶段就围绕“降低耦合、统一入口、隔离变化、复用通用逻辑”进行设计。主要对应关系如下：

| 架构位置 | 使用的设计模式理念 | 解决的设计问题 |
|---|---|---|
| Flask 应用入口 | 工厂模式 | 统一创建应用对象、加载配置并注册蓝图，避免初始化逻辑分散 |
| 路由层 | MVC / 前端控制器模式 | 统一接收请求，路由只做参数解析和业务分发，不直接处理复杂业务 |
| 服务层 | 外观模式 | 用 `AIService`、`ApiKeyService` 等服务封装复杂子系统，对路由层暴露简单接口 |
| 服务获取 | 单例模式 / 服务定位器模式 | 统一复用配置、数据库、认证和 AI 服务对象，减少重复创建和状态不一致 |
| Provider 选择 | 工厂模式思想 / 策略模式思想 | 根据 provider、模型能力和协议选择不同调用路径，隔离外部服务变化 |
| API Key 与数据库访问 | DAO 思想 | 集中管理数据查询、保存、加密和掩码展示，避免 SQL 与业务逻辑混杂 |
| 登录和异常处理 | 装饰器模式 / 拦截过滤器模式 | 将登录校验、错误捕获等横切逻辑从业务函数中抽离 |
| PaperBanana 工作流 | 模板模式 / 组合模式思想 | 用统一 Agent 接口组织检索、规划、生图、审图等步骤，复杂流程由多个模块组合完成 |
| 任务状态返回 | 传输对象模式 / 适配器模式 | 用统一任务状态对象和统一 JSON payload 屏蔽后台实现细节 |

项目主要模块划分如下：

| 模块 | 主要文件或目录 | 职责说明 |
|---|---|---|
| 应用入口 | `app.py` | 创建 Flask 应用，加载配置，注册认证、API 和主页面蓝图 |
| 路由层 | `src/routes` | 定义页面路由和 API 路由，完成请求解析、登录校验和响应返回 |
| 服务层 | `src/services` | 封装认证、API Key、provider 配置、AI 调用、PaperBanana 任务等业务逻辑 |
| 模型层 | `src/models` | 定义用户、API Key、provider 配置和使用统计等数据模型 |
| 工具层 | `src/utils` | 提供参数校验、错误类型、密钥加密等通用能力 |
| 前端页面 | `templates`、`static` | 提供页面结构、样式、事件绑定、API 调用和任务轮询 |
| PaperBanana 集成 | `integrations/PaperBanana` | 提供科研图表生成多 Agent 工作流 |
| GPT Image Playground 子项目 | `GPT_Image_Playground-main` | 提供更复杂的图像生成前端工作台和 Zustand 状态管理 |

系统总体结构如下：

```mermaid
flowchart LR
    U["用户浏览器"] --> UI["前端页面 templates/static"]
    UI --> R["Flask Routes 路由层"]
    R --> S["Services 服务层"]
    S --> M["Models 模型层"]
    M --> DB["SQLite 数据库"]
    S --> PB["PaperBanana 专业工作流"]
    PB --> AG["Retriever / Planner / Stylist / Visualizer / Critic Agents"]
    S --> EXT["外部 AI Provider API"]
```

### 数据设计

系统主要数据对象如下：

| 数据对象 | 对应模型 | 关键字段 | 作用 |
|---|---|---|---|
| 用户信息 | `User` | `id`、`username`、`salt`、`password_hash` | 保存登录用户和密码哈希 |
| API 密钥 | `ApiKey` | `id`、`user_id`、`provider`、`base_url`、`value`、`is_active` | 保存不同 provider 的 API Key 和激活状态 |
| 模型配置 | `ProviderConfig` | `user_id`、`provider`、`text_model`、`image_model` | 保存每个 provider 默认文本模型和图像模型 |
| 使用统计 | `UsageStats` | `user_id`、`total_calls`、`last_used_at` | 记录用户调用次数和最后使用时间 |
| 后台任务状态 | `PaperBananaJob` | `job_id`、`status`、`progress`、`stage`、`error` | 在图像生成过程中传递任务状态 |

数据关系如下：

```mermaid
erDiagram
    User ||--o{ ApiKey : owns
    User ||--o{ ProviderConfig : configures
    User ||--|| UsageStats : records
    User {
        int id
        string username
        bytes salt
        string password_hash
    }
    ApiKey {
        string id
        int user_id
        string provider
        string base_url
        string value
        bool is_active
    }
    ProviderConfig {
        int user_id
        string provider
        string text_model
        string image_model
    }
    UsageStats {
        int user_id
        int total_calls
        string last_used_at
    }
```

### 主要业务流程

图像生成是系统最核心的业务流程。它采用“提交任务 + 后台执行 + 前端轮询 + 结果下载”的形式，避免长时间同步等待。

```mermaid
sequenceDiagram
    participant User as 用户
    participant UI as 前端页面
    participant API as Flask API
    participant AI as AIService
    participant PB as PaperBananaService
    participant Agent as PaperBanana Agents

    User->>UI: 输入 prompt 和生成参数
    UI->>API: POST /api/draw
    API->>AI: generate_image(user_id, data)
    AI->>PB: submit_diagram(...)
    PB-->>API: 返回 job_id
    API-->>UI: 返回任务 ID
    PB->>Agent: 后台执行多 Agent 生成流程
    Agent-->>PB: 返回生成结果
    loop 前端轮询
        UI->>API: POST /api/result
        API->>AI: get_image_result(...)
        AI->>PB: get_result_payload(job_id)
        PB-->>API: 返回 running/succeeded/failed
        API-->>UI: 返回状态和结果
    end
    UI->>API: GET /api/paperbanana/file/<job_id>
    API-->>UI: 返回输出图片
```

### ㈢ 主要功能

1. **用户认证功能**
   系统提供默认用户初始化、登录、退出和登录状态维护。认证逻辑封装在 `AuthService` 中，路由层通过装饰器进行登录校验。

2. **API Key 管理功能**
   用户可以为不同 provider 添加 API Key、base URL 和名称。密钥经过加密后保存到 SQLite，前端展示时只显示掩码，避免明文泄露。

3. **Provider 模型配置功能**
   系统支持为不同 provider 保存默认文本模型和图像模型，例如 `grsai`、`openai`、`deepseek`、`openrouter`、`anthropic`、`google` 等。

4. **AI 图像生成入口**
   前端通过 `/api/draw` 提交图像生成请求，后端完成参数校验、模型选择和任务提交。

5. **PaperBanana 专业工作流**
   PaperBanana 使用多个 Agent 完成科研图表生成，包括 RetrieverAgent、PlannerAgent、StylistAgent、VisualizerAgent、CriticAgent 和 PolishAgent 等。

6. **任务状态管理功能**
   后台任务会记录 `queued`、`initializing`、`loading_agents`、`processing`、`saving`、`completed`、`failed` 等阶段，前端可以实时查看任务进度。

7. **结果展示与下载功能**
   任务成功后，系统将生成图片保存为文件，并通过 `/api/paperbanana/file/<job_id>` 返回给前端展示或下载。

8. **异常处理功能**
   系统能处理未登录、缺少 API Key、prompt 为空、任务 ID 无效、生成失败等异常情况，并返回明确错误信息。

功能完成情况如下：

| 设计目标 | 对应功能 | 实现方式 | 完成情况 |
|---|---|---|---|
| Web 系统可访问 | 首页、登录页、主页面 | Flask 模板渲染和静态资源加载 | 已完成 |
| 用户身份管理 | 登录、退出、默认用户 | `AuthService` + session | 已完成 |
| API Key 安全保存 | 添加、删除、激活、掩码展示 | `ApiKeyService` + `EncryptionService` | 已完成 |
| provider 模型配置 | 文本模型、图像模型默认值 | `ProviderConfigService` | 已完成 |
| 图像任务提交 | `/api/draw` | `AIService.generate_image()` | 已完成 |
| 后台异步执行 | 后台线程和状态文件 | `PaperBananaService` | 已完成 |
| 任务轮询查询 | `/api/result` | 统一状态 payload | 已完成 |
| 结果文件返回 | `/api/paperbanana/file/<job_id>` | `send_file` 返回图片 | 已完成 |
| 设计模式应用 | 多个模块体现不同模式 | 单例、装饰器、外观、适配器、模板等 | 已完成 |

## 五、代码实现分析

本次综合实验要求项目中体现设计模式理念。我的理解是，设计模式不是写完项目后再在报告里补几个名称，而是在设计和实现过程中真正帮助我们解决问题。例如：

1. 服务对象需要统一创建和复用，所以使用单例模式和服务定位器模式。
2. 多个路由都需要登录校验和异常处理，所以使用装饰器模式和拦截过滤器模式。
3. 路由层不应该了解所有 AI provider 和 PaperBanana 内部细节，所以用 `AIService` 作为外观接口。
4. 不同外部服务返回格式不同，所以需要适配成统一前端 payload。
5. 多个 Agent 都需要统一处理入口，所以使用抽象基类和模板模式思想。

### 1. 设计模式应用总览

| 设计模式 | 项目体现 | 解决的问题 | 如何做到 |
|---|---|---|---|
| 工厂模式 | `create_app()` 创建 Flask 应用 | 集中管理应用初始化过程 | 将配置加载、Flask 实例创建、Blueprint 注册和默认用户初始化放在一个应用工厂函数中 |
| MVC 模式 | `models`、`routes`、`templates/static` 分层 | 分离数据、控制逻辑和界面展示 | 模型负责数据，路由负责请求控制，模板和静态文件负责页面 |
| 单例模式 | `get_config()`、`get_ai_service()`、`get_db_manager()` 等 | 避免重复创建全局服务对象 | 使用模块级变量保存实例，第一次调用时创建，后续直接返回 |
| 服务定位器模式 | `get_xxx_service()` | 简化服务对象获取方式 | 路由和服务不直接 new 对象，而是通过统一函数获取服务 |
| 装饰器模式 | `@api_login_required`、`@handle_api_errors` | 给路由函数增强登录校验和异常处理 | 使用 Python 装饰器包装原函数，在执行前后添加逻辑 |
| 拦截过滤器模式 | 登录校验和 API 错误处理 | 统一处理横切逻辑 | 请求进入业务函数前先经过装饰器检查 |
| 外观模式 | `AIService` | 屏蔽 AI 调用和任务编排复杂度 | 路由层只调用 `generate_image()`、`get_image_result()` 等统一方法 |
| 适配器模式 | PaperBanana / Anthropic 等结果转统一结构 | 屏蔽不同接口返回格式差异 | 后端将不同来源结果转换成前端可消费的统一 JSON |
| 模板模式 | `BaseAgent.process()` | 统一 Agent 处理接口 | 父类定义抽象方法，子类分别实现检索、规划、审查等逻辑 |
| 组合模式思想 | `PaperVizProcessor` 组合多个 Agent | 将复杂生成流程拆成多个步骤 | Processor 按模式组合 Retriever、Planner、Stylist、Visualizer、Critic |
| 策略模式思想 | 根据 provider / protocol 选择调用路径 | 支持多 provider 和多协议 | 服务层根据 provider、模型能力和协议选择不同分支 |
| 数据访问对象模式思想 | `DatabaseManager` | 集中管理数据库连接和查询 | 封装 `execute_query`、`fetch_one`、`fetch_all` 等方法 |
| 传输对象模式 | `PaperBananaJob` 和 JSON payload | 在模块之间传递结构化状态 | 用 dataclass 和字典统一传递任务状态与结果 |
| 前端控制器模式 | Flask Blueprint 和路由函数 | 集中接收并分发前端请求 | 所有浏览器请求先进入 Flask 路由，再调用相应服务 |

### 2. 应用工厂模式

项目在 `app.py` 中定义 `create_app()` 方法，用于创建 Flask 应用、设置配置项、注册 Blueprint 和初始化默认用户。

```python
def create_app() -> Flask:
    config = get_config()
    app = Flask(__name__)
    app.secret_key = config.app_secret_key
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(main_bp)
    User.ensure_default_user()
    return app
```

这个设计体现了工厂模式思想。外部调用者只需要调用 `create_app()`，不需要关心 Flask 对象如何创建、配置如何加载、路由如何注册。这样做的好处是应用初始化逻辑集中，后续测试或部署时也更容易复用。

### 3. MVC 模式

项目整体采用 MVC 思想组织代码：

| MVC 角色 | 项目对应部分 | 说明 |
|---|---|---|
| Model | `src/models` | 定义 `User`、`ApiKey`、`ProviderConfig`、`UsageStats` 等数据模型 |
| View | `templates`、`static` | 负责页面结构、样式和前端交互 |
| Controller | `src/routes` | 接收 HTTP 请求，调用服务层并返回 JSON 或页面 |

例如 `/api/draw` 路由并不直接执行复杂图像生成逻辑，而是调用 `AIService.generate_image()`。这说明 Controller 只负责请求控制，真正业务逻辑由 service 完成。这种分层让代码更清晰，也方便后续维护。

### 4. 单例模式与服务定位器模式

项目中很多服务采用模块级懒加载单例，例如 `AIService`：

```python
_ai_service: Optional[AIService] = None

def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
```

类似方法还包括：

1. `get_config()`
2. `get_db_manager()`
3. `get_auth_service()`
4. `get_api_key_service()`
5. `get_provider_config_service()`
6. `get_paper_banana_service()`
7. `get_validation_service()`

这些方法体现了两个设计模式：

1. **单例模式**
   保证服务对象不会在项目中被反复创建，避免重复初始化数据库、配置和服务依赖。

2. **服务定位器模式**
   调用方通过 `get_xxx_service()` 获取服务，而不需要知道服务对象如何创建、依赖什么参数。

这种设计尤其适合当前 Flask 项目，因为路由函数分散在多个文件中，如果每个路由都自己创建服务对象，会造成重复代码和状态不一致。

### 5. 装饰器模式与拦截过滤器模式

项目在 `src/routes/decorators.py` 中定义了登录校验和错误处理装饰器：

```python
@api_bp.post("/draw")
@api_login_required
@handle_api_errors
def draw() -> Any:
    ...
```

其中：

1. `api_login_required` 用于判断 API 请求是否已登录。
2. `login_required` 用于页面请求登录校验。
3. `handle_api_errors` 用于统一捕获 API 错误并返回 JSON。

这体现了装饰器模式：在不修改原路由函数内部逻辑的情况下，为函数增加额外能力。它也体现了拦截过滤器模式：请求真正进入业务逻辑之前，先经过登录校验和异常处理。

这样做的优点是：

1. 避免每个路由重复写登录判断。
2. 避免每个路由重复写 try-except。
3. 让路由函数更专注于自己的业务。
4. 统一 API 错误返回格式，便于前端处理。

### 6. 外观模式

`AIService` 是后端 AI 相关业务的统一入口。路由层只需要调用：

1. `generate_image()`
2. `get_image_result()`
3. `cancel_image_result()`
4. `chat_completion()`

路由层不需要知道底层是调用 grsai、OpenAI-compatible provider、Anthropic，还是调用 PaperBanana 本地工作流。

```text
Routes -> AIService -> ApiKeyService / ProviderConfigService / PaperBananaService / UsageStats
```

这体现了外观模式。`AIService` 为复杂子系统提供了一个统一接口，降低了路由层的复杂度。后续如果底层 provider 调用方式改变，只需要修改 service 内部，路由层基本不用变化。

### 7. 适配器模式

项目中存在多个外部接口和内部工作流，它们返回的数据格式并不相同。例如：

1. Anthropic 的消息接口和 OpenAI Chat Completions 格式不同。
2. PaperBanana 本地生成的是任务状态、base64 图片和本地文件路径。
3. 前端希望读取统一的 JSON 字段来展示结果。

因此，后端需要把不同来源的数据转换成统一结构。例如 PaperBanana 成功后返回：

```json
{
  "id": "job_id",
  "status": "succeeded",
  "progress": 100,
  "stage": "completed",
  "model": "paperbanana",
  "results": [
    {
      "url": "/api/paperbanana/file/job_id",
      "content": "PaperBanana generated"
    }
  ]
}
```

这就是适配器模式的作用：**让前端面对统一接口，而不是直接面对每一种外部服务的差异**。如果没有适配器思想，前端就需要为每个 provider 写不同展示逻辑，系统会变得难以维护。

### 8. 模板模式

PaperBanana 子模块中定义了 `BaseAgent` 抽象类：

```python
class BaseAgent(ABC):
    @abstractmethod
    async def process(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        pass
```

不同 Agent 都继承 `BaseAgent`，并实现自己的 `process()` 方法，例如：

1. `RetrieverAgent` 负责检索参考样例。
2. `PlannerAgent` 负责生成图像描述规划。
3. `StylistAgent` 负责风格化。
4. `VisualizerAgent` 负责生成图像。
5. `CriticAgent` 负责审查和改进建议。
6. `PolishAgent` 负责进一步润色。

这体现了模板模式和多态思想：父类规定统一处理接口，子类实现不同处理步骤。这样 `PaperVizProcessor` 可以统一调用各个 Agent 的 `process()`，而不需要关心每个 Agent 内部如何实现。

### 9. 组合模式思想

PaperBanana 的完整生成过程不是由单个对象完成，而是由多个 Agent 组合完成。`PaperVizProcessor` 负责将这些 Agent 按不同实验模式组合起来：

```text
RetrieverAgent -> PlannerAgent -> StylistAgent -> VisualizerAgent -> CriticAgent -> Evaluation
```

这种设计体现了组合模式思想。每个 Agent 是一个相对独立的功能模块，复杂任务通过组合多个模块完成。这样做的优点是：

1. 每个 Agent 职责清晰。
2. 工作流可以按模式灵活组合。
3. 某个 Agent 的实现变化不会直接影响其他 Agent。
4. 后续可以增加新的 Agent 或新的工作流模式。

### 10. 策略模式思想

系统支持多个 provider 和多种调用协议。不同 provider 的调用方式、headers、base URL 和返回格式可能不同，因此服务层需要根据 provider 和模型选择不同处理路径。

例如：

1. `anthropic` 使用 Anthropic Messages API。
2. OpenAI-compatible provider 使用 `/chat/completions`。
3. PaperBanana 图像生成走本地多 Agent 工作流。
4. GPT Image Playground 子项目可以根据 `apiProtocol` 在 `images`、`responses`、`auto` 之间选择。

当前项目主要通过条件分支实现这种选择，还没有完全拆成独立策略类，但它体现了策略模式的核心思想：**把不同算法或调用路径封装为可选择的行为**。后续如果 provider 继续增加，可以进一步重构为标准策略模式。

### 11. 数据访问对象模式思想

项目使用 `DatabaseManager` 统一管理数据库连接和查询：

```python
class DatabaseManager:
    def execute_query(...)
    def execute_insert(...)
    def fetch_one(...)
    def fetch_all(...)
```

模型类中也封装了保存和查询方法，例如 `User.get_by_username()`、`ApiKey.get_by_user_id()`、`ProviderConfig.get_by_user_provider()` 等。

这种设计具有 DAO 和 Active Record 的混合特点：

1. `DatabaseManager` 提供统一数据库访问能力。
2. 模型类负责把数据库记录转换为业务对象。
3. 路由层和前端不直接接触 SQL。

这样能减少数据库操作散落在各处的问题，使数据访问逻辑更加集中。

### 12. 传输对象模式

后台任务状态通过 `PaperBananaJob` dataclass 表达：

```python
@dataclass(frozen=True)
class PaperBananaJob:
    job_id: str
    status: str
    progress: int
    stage: str = "queued"
    stage_message: Optional[str] = None
    output_image_path: Optional[str] = None
    error: Optional[str] = None
```

这个对象用于在后台任务执行、状态文件保存、结果读取和 API 返回之间传递状态数据。它体现了传输对象模式：将多个相关字段封装为一个结构化对象，便于不同层之间传递。

如果没有这种结构，任务状态可能会散落成多个无约束的变量，容易造成字段遗漏或格式不一致。

### 13. 前端控制器模式

Flask Blueprint 和路由函数承担前端控制器角色。浏览器请求不会直接访问服务类或数据库，而是先进入路由层，再由路由层分发到不同服务：

```text
/api/keys -> ApiKeyService
/api/provider-configs -> ProviderConfigService
/api/draw -> AIService
/api/result -> AIService
/api/paperbanana/file/<job_id> -> PaperBananaService
```

这种结构符合前端控制器模式思想：前端请求集中进入后端控制器，由控制器统一进行认证、参数解析和业务分发。它让系统请求入口更加清晰，也便于统一加权限校验和错误处理。

### 14. 核心业务流程实现分析

图像生成流程是本项目最核心的业务。它采用异步任务式设计，主要步骤如下：

1. **前端收集参数**
   用户输入 prompt，选择 provider、文本模型、图像模型、图片比例、图片尺寸和工作流模式。

2. **提交生成请求**
   前端调用 `/api/draw`，后端路由进入 `AIService.generate_image()`。

3. **服务层校验和补全参数**
   `AIService` 对 provider、model、prompt、工作流参数进行校验，并读取用户保存的默认模型配置。

4. **创建后台任务**
   `PaperBananaService.submit_diagram()` 创建 job id，写入初始状态，并启动后台线程。

5. **执行 PaperBanana 工作流**
   后台线程按实验模式调用不同 Agent，逐步生成图像描述、风格化描述、图片结果和评估结果。

6. **保存结果和状态**
   成功后将图片保存为 `output.jpg`，并将任务状态更新为 `succeeded`；失败时写入 `failed` 和错误信息。

7. **前端轮询结果**
   前端定时调用 `/api/result`，根据状态更新页面进度。如果任务成功，则读取 `results` 中的图片 URL 展示结果。

这个流程体现了多个设计模式的协作：路由层体现前端控制器模式，`AIService` 体现外观模式，`PaperBananaJob` 体现传输对象模式，多 Agent 处理体现模板和组合思想，状态查询结果体现适配器模式。

### 15. 关键代码具体实现

为了体现“设计模式理念不是停留在文字说明中，而是落实到具体代码结构中”，本节从前端提交、后端路由、服务层调度、后台任务、结果返回和密钥管理六个角度分析项目的关键实现。

#### 15.1 前端参数收集与控制器调用

前端核心入口位于 `static/js/app.js` 的 `generateImage(mode = 'generic')` 函数。该函数相当于前端页面层的控制器，负责读取用户输入、判断当前是普通图像生成模式还是 PaperBanana 专业工作流模式，并把页面控件中的参数整理成统一请求对象。

关键实现如下：

```javascript
const prompt = context.promptInput.value;
const textProvider = isPaperMode && DOM.generationTextProviderSelect
    ? DOM.generationTextProviderSelect.value
    : '';
const imageProvider = isPaperMode
    ? (DOM.paperImageProviderSelect ? DOM.paperImageProviderSelect.value : 'grsai')
    : (DOM.generationImageProviderSelect ? DOM.generationImageProviderSelect.value : 'grsai');
const imageModel = isPaperMode
    ? (DOM.paperImageModelSelect ? DOM.paperImageModelSelect.value : 'nano-banana-pro')
    : (DOM.generationImageModelSelect ? DOM.generationImageModelSelect.value : 'nano-banana-pro');
```

这段代码的作用是把页面中分散的输入控件转换为统一业务参数。普通生成模式和 PaperBanana 模式在页面控件上不同，但提交给后端时仍然整理成 `provider`、`textProvider`、`imageProvider`、`textModel`、`imageModel`、`imageSize`、`expMode` 等字段。这体现了前端控制器模式和适配器思想：页面可以不同，但提交协议保持一致。

当前端提交任务后，并不是直接等待后端长时间阻塞返回，而是调用 `window.APIService.generateImage()`，同时传入 `onProgress` 和 `onComplete` 回调：

```javascript
const result = await window.APIService.generateImage(prompt, {
    provider,
    textProvider,
    imageProvider,
    textModel,
    imageModel,
    expMode: workflowExpMode,
    retrievalSetting: workflowRetrieval,
    imageSize,
    cancellation: generationController,
    onProgress: (progress, message, payload) => {
        updatePaperTaskId(payload.id);
        updatePaperStage(payload?.stage, payload?.stageMessage || message, payload?.status || 'running');
    },
    onComplete: (resultData) => {
        handleImageGenerationComplete(resultData, context.mode);
    }
});
```

这里的 `onProgress` 负责把后台任务状态同步到界面，包括任务 ID、进度条、阶段名称和工作流图节点；`onComplete` 负责在任务成功后渲染结果图片。这种写法把“提交任务”和“展示状态”解耦，避免了把所有逻辑堆在一个大函数中。

#### 15.2 前端 APIService 的提交与轮询实现

`static/js/api-service.js` 中的 `APIService` 对后端接口进行了封装，它是前端访问后端的统一外观。前端页面不直接 `fetch('/api/draw')`，而是通过 `APIService.generateImage()` 间接调用。

提交任务时，`generateImageStream()` 将参数组装为 JSON，并请求 `/api/draw`：

```javascript
const body = {
    model,
    provider,
    textProvider,
    imageProvider,
    textModel,
    imageModel,
    expMode,
    retrievalSetting,
    criticEnabled,
    evalEnabled,
    maxCriticRounds,
    prompt,
    aspectRatio,
    imageSize,
    urls
};
body.webHook = '-1';
const response = await this.makeRequest('/api/draw', 'POST', body);
```

后端返回任务 ID 后，`generateImage()` 进入轮询流程。它每 5 秒调用一次 `/api/result`，最多轮询 240 次，即最多等待约 20 分钟：

```javascript
const maxAttempts = 240;
const pollInterval = 5000;

while (attempts < maxAttempts) {
    await new Promise(resolve => setTimeout(resolve, pollInterval));
    attempts++;
    const pollResult = await this.getImageResult(taskId);
    result = pollResult.data;

    if (onProgress) {
        const progressValue = result.progress || Math.min(10 + attempts * 2, 90);
        onProgress(progressValue, result.stageMessage, result);
    }

    if (result.status === 'succeeded') {
        if (onComplete) onComplete(result);
        return { success: true, taskId, result };
    }
}
```

这段实现体现了异步任务设计。图像生成属于耗时操作，如果使用同步请求，浏览器可能长时间等待甚至超时；通过“提交任务 ID + 轮询状态”的方式，系统可以实时展示进度，也可以在任务失败或超时时给出明确反馈。

#### 15.3 后端路由层的前端控制器实现

后端接口集中在 `src/routes/api_routes.py`。例如图像生成和结果查询接口如下：

```python
@api_bp.post("/draw")
@api_login_required
@handle_api_errors
def draw() -> Any:
    auth_service = get_auth_service()
    ai_service = get_ai_service()

    user_id = auth_service.get_current_user_id()
    data = request.get_json(force=True, silent=True) or {}

    result = ai_service.generate_image(user_id, data)
    return jsonify(result)

@api_bp.post("/result")
@api_login_required
@handle_api_errors
def result() -> Any:
    auth_service = get_auth_service()
    ai_service = get_ai_service()
    user_id = auth_service.get_current_user_id()
    draw_id = (request.get_json(force=True, silent=True) or {}).get("id", "").strip()

    result = ai_service.get_image_result(user_id, draw_id)
    return jsonify(result)
```

路由层没有直接操作数据库，也没有直接调用外部模型，而是只做三件事：获取当前用户、读取请求参数、调用服务层。这是 MVC 中 Controller 的典型职责。`@api_login_required` 和 `@handle_api_errors` 负责在业务执行前后统一处理认证与错误，因此路由函数本身保持简洁。

#### 15.4 AIService 的外观封装与工厂选择

`src/services/ai_service.py` 中的 `AIService.generate_image()` 是后端图像生成的统一入口。它先解析前端传入的 provider、模型、工作流参数，再根据用户配置补全默认模型。

关键实现如下：

```python
provider = (data.get("provider") or "grsai").strip() or "grsai"
text_provider = (data.get("textProvider") or data.get("text_provider") or provider).strip() or provider
image_provider = (data.get("imageProvider") or data.get("image_provider") or provider).strip() or provider

text_provider = self.api_key_service.normalize_provider(text_provider)
image_provider = self.api_key_service.normalize_provider(image_provider)
provider = image_provider or text_provider or self.api_key_service.normalize_provider(provider)
```

这部分体现了工厂模式思想：系统不是把 provider 写死，而是先标准化 provider，再根据 provider 找到对应的 Key、Base URL 和模型配置。之后 `AIService` 读取用户保存的 provider 默认配置：

```python
svc = get_provider_config_service()
text_defaults = svc.get_defaults(int(user_id) if user_id else 1, text_provider)
image_defaults = svc.get_defaults(int(user_id) if user_id else 1, image_provider)

text_model = text_model or text_defaults.get("textModel") or ""
image_model = image_model or image_defaults.get("imageModel") or ""
```

如果前端没有指定模型，后端会使用默认配置或 preset 映射补全模型名。这样做的好处是前端可以保持简单，后端负责兜底和兼容旧参数。

最后，`AIService` 并不直接执行 PaperBanana 工作流，而是调用 `PaperBananaService.submit_diagram()`：

```python
service = get_paper_banana_service()
job_id = service.submit_diagram(
    user_id=user_id,
    provider=provider,
    text_provider=text_provider,
    image_provider=image_provider,
    text_model=text_model,
    image_model=image_model,
    method_content=prompt,
    caption=caption,
    image_size=image_size,
    exp_mode=exp_mode,
    retrieval_setting=retrieval_setting,
    critic_enabled=critic_enabled,
    eval_enabled=eval_enabled,
)

return {"code": 0, "data": {"id": job_id}}
```

从调用关系看，`AIService` 对路由层提供的是一个简单的“生成图片”接口，但内部实际完成了 provider 选择、模型补全、参数校验、任务创建和使用统计记录。这正是外观模式在项目中的具体体现。

#### 15.5 PaperBananaService 的后台任务实现

`src/services/paper_banana_service.py` 是本项目最能体现异步任务和传输对象模式的部分。系统使用 `PaperBananaJob` 统一描述任务状态：

```python
@dataclass(frozen=True)
class PaperBananaJob:
    job_id: str
    status: str
    progress: int
    stage: str = "queued"
    stage_message: Optional[str] = None
    output_image_path: Optional[str] = None
    error: Optional[str] = None
```

任务状态不是用多个零散变量表达，而是封装成一个结构化对象，在“写入状态文件、读取状态文件、生成 API payload”之间传递。`_write_status()` 会把它落盘为 `status.json`：

```python
payload = {
    "jobId": job.job_id,
    "status": job.status,
    "progress": job.progress,
    "stage": job.stage,
    "stageMessage": job.stage_message,
    "outputImagePath": job.output_image_path,
    "error": job.error,
}
self._status_file(job.job_id).write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
```

提交任务时，`submit_diagram()` 先生成 `uuid`，写入 queued 状态，再启动后台线程：

```python
job_id = uuid.uuid4().hex
self._write_status(
    PaperBananaJob(
        job_id=job_id,
        status="running",
        progress=1,
        stage="queued",
    )
)

thread = threading.Thread(
    target=self._run_job_safe,
    args=(job_id, user_id, provider, text_provider, image_provider, text_model, image_model, ...),
    daemon=True,
)
thread.start()
return job_id
```

这里的关键点是：HTTP 请求只负责创建任务并立即返回任务 ID，真正耗时的生成过程放入后台线程执行。这样前端不会被长任务阻塞。

后台线程由 `_run_job_safe()` 包裹，它捕获所有异常，并把失败信息写入任务状态：

```python
try:
    self._run_job(...)
except Exception as exc:
    self._write_status(
        PaperBananaJob(
            job_id=job_id,
            status="failed",
            progress=100,
            stage="failed",
            error=str(exc),
        )
    )
```

这使得后台任务即使失败，也不会让前端一直停留在“运行中”。前端轮询 `/api/result` 时能够拿到 `failed` 状态和错误原因，用户可以看到明确反馈。

任务成功后，服务层会把 base64 图片解码为本地文件，并将任务状态更新为 succeeded：

```python
img_bytes = base64.b64decode(b64_jpg)
out_path = job_dir / "output.jpg"
out_path.write_bytes(img_bytes)

self._write_status(
    PaperBananaJob(
        job_id=job_id,
        status="succeeded",
        progress=100,
        stage="completed",
        output_image_path=str(out_path),
    )
)
```

这部分实现体现了完整的任务生命周期：创建任务、运行任务、记录进度、保存结果、返回成功状态。

#### 15.6 结果查询与统一返回格式

前端轮询调用的 `/api/result` 最终会进入 `PaperBananaService.get_result_payload()`。该方法把内部任务状态转换为前端可理解的统一 JSON：

```python
if job.status == "succeeded":
    return {
        "id": job_id,
        "status": "succeeded",
        "progress": 100,
        "stage": job.stage or "completed",
        "stageMessage": job.stage_message or "图像生成完成",
        "model": "paperbanana",
        "results": [
            {
                "url": f"/api/paperbanana/file/{job_id}",
                "content": "PaperBanana generated",
            }
        ],
    }
```

这里体现了适配器模式：PaperBanana 内部保存的是 `status.json` 和 `output.jpg`，但前端并不需要知道这些内部文件路径，只需要读取统一的 `status`、`progress`、`stageMessage` 和 `results` 字段。

图片文件返回由 `src/routes/api_routes.py` 中的文件接口完成：

```python
@api_bp.get("/paperbanana/file/<job_id>")
@api_login_required
@handle_api_errors
def paperbanana_file(job_id: str):
    service = get_paper_banana_service()
    output_path = service.get_output_file(job_id)
    return send_file(str(output_path), mimetype="image/jpeg", conditional=True, max_age=0)
```

该接口把后端生成的本地文件转换为浏览器可访问的图片响应，前端结果展示只需要使用 `results[0].url` 即可。

#### 15.7 API Key 加密存储与掩码展示

API Key 管理位于 `src/services/api_key_service.py` 和 `src/utils/encryption.py`。添加 Key 时，系统会先清洗用户输入，防止用户把 `Bearer ` 前缀、中文备注或非 ASCII 字符误填入密钥：

```python
value = self._sanitize_api_key_value(value)
if not value:
    raise ValidationError("Api key 不能为空")
```

随后创建新的 key 记录，并把该 provider 的 active key 指向新记录：

```python
new_item = {
    "id": uuid.uuid4().hex,
    "provider": provider,
    "name": (name or "").strip(),
    "base_url": base_url,
    "value": value,
    "source": "custom",
}
keys.append(new_item)
active_by_provider[provider] = new_item["id"]
self.save_key_store(keys, active_by_provider, user_id)
```

真正保存数据库时，密钥不会明文入库，而是调用 `EncryptionService.encrypt()`：

```python
key = ApiKey(
    id=item.get("id"),
    user_id=user_id,
    provider=provider,
    name=item.get("name") or "",
    base_url=item.get("base_url") or "",
    value=self.encryption.encrypt(item.get("value", "")),
    source=item.get("source", "custom"),
    is_active=(item.get("id") == active_by_provider.get(provider)),
)
key.save()
```

前端展示密钥列表时，后端不会返回明文，而是通过 `mask_key()` 生成掩码：

```python
@staticmethod
def mask_key(value: str) -> str:
    if len(value) <= 8:
        return f"***{value[-2:]}"
    return f"{value[:4]}...{value[-4:]}"
```

因此实验截图中显示的是 `sk-d...7890` 这种形式，而不是完整密钥。这说明系统不仅实现了功能，也考虑了敏感信息保护。

#### 15.8 代码实现与设计模式对应关系

综合上面的代码，可以看到设计模式和具体实现之间的关系如下：

| 具体代码位置 | 实现内容 | 对应设计模式或思想 |
|---|---|---|
| `static/js/app.js` | 收集页面参数、触发生成、更新 UI 状态 | 前端控制器、回调解耦思想 |
| `static/js/api-service.js` | 封装 `/api/draw`、`/api/result`、轮询任务 | 外观模式、适配器思想 |
| `src/routes/api_routes.py` | 统一接收 HTTP 请求并分发到服务层 | 前端控制器模式、MVC |
| `src/routes/decorators.py` | 登录校验和异常处理装饰器 | 装饰器模式、拦截过滤器模式 |
| `src/services/ai_service.py` | 统一封装 provider、模型、任务创建逻辑 | 外观模式、工厂模式思想 |
| `src/services/paper_banana_service.py` | 后台任务、状态文件、结果 payload | 传输对象模式、适配器模式 |
| `src/services/api_key_service.py` | Key 清洗、加密保存、active key 管理 | DAO 思想、服务定位器思想 |
| `src/utils/encryption.py` | Fernet 加密、解密和掩码显示 | 单例模式、安全封装 |

由此可见，项目的设计模式并不是单独写几个示例类，而是贯穿在真实业务流程中：前端通过控制器收集参数，后端通过路由分发请求，服务层封装复杂业务，后台任务通过传输对象记录状态，结果接口通过适配器统一返回格式，密钥服务则通过加密和 DAO 思想保证数据安全。

### 16. 安全性与异常处理分析

项目在安全性和异常处理方面也做了设计：

1. **API Key 加密保存**
   `EncryptionService` 使用 Fernet 对 API Key 加密，数据库不直接保存明文。前端展示时使用掩码，例如只显示前后部分字符。

2. **登录校验**
   页面和 API 请求通过装饰器校验登录状态，避免未授权访问核心功能。

3. **统一错误返回**
   `handle_api_errors` 将后端异常转换为统一 JSON，前端可以稳定展示错误信息。

4. **参数校验**
   `ValidationService` 对 prompt、draw id、messages、参考图片数量和大小进行校验，避免无效输入进入核心流程。

5. **任务失败处理**
   `_run_job_safe()` 捕获后台任务异常，并写入 failed 状态。前端轮询时可以看到失败原因，而不是一直等待。

6. **任务取消设计**
   系统通过 `cancelled.flag` 文件记录取消请求，后台流程中多次检查取消状态，支持长任务中途终止。

这些设计说明项目不仅关注成功流程，也考虑了异常情况和用户反馈。

## 六、测试结果分析

### 1. 测试环境与方法

本次测试采用手工功能测试和接口流程验证相结合的方式。测试前先启动 Flask 后端服务，再通过浏览器访问系统页面，依次检查登录、API Key 配置、模型配置、图像生成、任务轮询、结果下载和异常提示。

测试重点包括：

1. 页面是否能正常访问。
2. API Key 是否能够保存、加密和掩码展示。
3. provider 模型配置是否能够保存和读取。
4. 图像生成任务是否能够提交并返回 job id。
5. 后台任务状态是否能够被前端轮询。
6. 生成成功后结果图片是否能够展示。
7. 异常输入是否能够得到明确错误提示。

除功能正确性外，本次测试还专门关注设计模式是否真正发挥作用：API Key 切换用于验证 provider 选择和服务定位是否有效；任务状态轮询用于验证传输对象和适配器返回结构是否稳定；异常提示用于验证装饰器和拦截过滤器是否统一处理错误；PaperBanana 工作流用于验证模板模式和组合模式思想是否能够组织多 Agent 流程。

### 2. 功能测试表

| 测试项 | 测试方法 | 预期结果 | 实际结果 |
|---|---|---|---|
| 应用启动 | 启动 Flask 应用并访问首页 | 服务正常启动，首页可访问 | 正常 |
| 默认用户初始化 | 首次访问系统 | 自动创建默认用户 | 正常 |
| 登录功能 | 输入用户名和密码登录 | 登录成功后进入主页面 | 正常 |
| API Key 添加 | 添加 provider key | 数据库存储密钥，前端显示掩码 | 正常 |
| API Key 激活 | 切换 active key | 同 provider 只保留一个 active key | 正常 |
| 模型配置 | 修改 provider 默认模型 | 保存后生成流程可读取配置 | 正常 |
| 图像任务提交 | 输入 prompt 并点击生成 | 返回任务 ID | 正常 |
| 任务状态轮询 | 前端定时请求 `/api/result` | 返回 running/succeeded/failed 状态 | 正常 |
| 结果文件下载 | 访问 `/api/paperbanana/file/<job_id>` | 返回生成图片 | 正常 |
| 异常处理 | 缺少 key 或 prompt 为空 | 返回明确错误信息 | 正常 |

从设计模式验证角度看，以上测试并不是只证明按钮能点击，而是验证系统结构是否合理：API Key 添加和激活证明 `ApiKeyService` 与服务定位器能够统一管理 provider 凭据；模型配置证明后端外观服务能够读取并组合多个子服务；任务提交和轮询证明传输对象和适配器 payload 能够在前后端之间稳定传递；异常处理证明装饰器和拦截过滤器能把不同异常转换成统一响应。

### 3. 运行截图与结果说明

以下截图均来自本地运行环境。为避免泄露个人真实凭据，API Key 截图使用实验演示 Key；结果截图使用本地测试任务输出，重点验证“任务提交、状态记录、结果文件返回、前端展示”这一完整链路。

系统启动后可以正常进入主页面，页面提供图像生成、API 密钥管理、模型配置和专业工作流等入口，说明后端页面渲染和前端静态资源加载正常。

![图1 系统首页或主控制台截图](images/figure-1-homepage.png)

在 API 密钥管理页面中，用户可以选择 provider，填写 base URL 和 API Key。密钥保存后不会在前端明文展示，而是通过掩码方式显示，体现了系统对敏感信息的保护。

![图2 API 密钥管理页面截图](images/figure-2-api-keys.png)

在图像生成页面中，用户可以输入 prompt，并选择 provider、文本模型、图像模型、图片比例和图片尺寸等参数。前端会将这些参数统一提交给 `/api/draw` 接口。

![图3 图像生成参数填写截图](images/figure-3-generation-form.png)

任务提交后，系统返回任务 ID，前端通过轮询 `/api/result` 查询任务状态。运行过程中可以看到任务 ID、进行中标签以及 queued、initializing、loading_agents、processing、saving 等阶段节点，说明后台任务状态管理正常。截图中同时出现模型能力提示，说明当前工作流配置与模型能力不匹配时，系统能够给出可见的错误或风险提示。

![图4 任务运行中状态截图](images/figure-4-task-running.png)

任务成功后，前端能够展示生成图片，并通过 `/api/paperbanana/file/<job_id>` 下载输出结果。图中结果文件由本地测试任务产生，内容展示了系统内部的设计模式链路；该结果说明从前端提交、后端执行、状态查询到文件返回的完整流程已经跑通。

![图5 图像生成结果截图](images/figure-5-generation-result.png)

### 4. 正常用例分析

正常流程中，用户先进入系统页面，配置 API Key 和 provider 模型，然后输入 prompt 提交图像生成任务。后端返回任务 ID 后，前端进入轮询状态，持续显示后台进度。任务成功后，页面展示生成图片。

正常用例验证结果说明：

1. 前端能够正确收集和提交用户参数，说明前端控制器逻辑能够将页面输入转换为统一请求。
2. Flask 路由能够正确接收请求并调用服务层，说明 MVC 分层和前端控制器模式有效。
3. `AIService` 能够完成参数处理和任务提交，说明外观模式降低了路由层对 AI 子系统的依赖。
4. `PaperBananaService` 能够创建任务、执行后台流程并写入状态，说明传输对象和模板化工作流能够组织长任务。
5. 前端能够根据统一结果 payload 展示任务进度和生成图片，说明适配器模式统一了不同来源结果的展示方式。

这一流程证明项目主要功能已经实现，系统具备完整闭环。

### 5. 异常用例分析

| 异常情况 | 系统处理方式 | 分析 |
|---|---|---|
| prompt 为空 | `ValidationService` 抛出校验错误 | 避免无效任务进入后台 |
| 未配置 API Key | `ApiKeyService` 返回缺少密钥错误 | 用户可以根据提示补充配置 |
| 任务 ID 为空 | `validate_draw_id()` 拦截 | 防止读取不存在任务 |
| 后台任务失败 | 写入 failed 状态和错误信息 | 前端可以展示失败原因 |
| 用户取消任务 | 写入 `cancelled.flag` | 支持长任务中途终止 |
| 上游服务异常 | 统一转换为 API 错误 | 前端能展示可读错误 |

异常用例说明系统具备基本健壮性，也说明设计模式对异常处理有直接帮助。prompt 为空和任务 ID 为空由校验服务集中拦截，未配置 API Key 由服务层统一返回错误，后台任务失败由任务状态对象保存失败原因，上游服务异常则通过装饰器转换为统一 API 响应。虽然目前还没有引入完整任务队列和集中日志系统，但对综合实验项目而言，错误处理已经比较完整。

### 6. 测试结果总结

通过测试可以看出，系统核心功能已经完成，同时设计模式主线也得到了验证。前端能够向后端提交生成请求，后端能够创建后台任务并执行 PaperBanana 工作流，前端能够通过轮询获取任务状态并展示结果。API Key 管理和模型配置功能也能正常支撑不同 provider 的调用，说明工厂模式思想、服务定位器、外观模式、适配器模式和传输对象模式在实际流程中能够协同工作。

从评分标准角度看：

1. **实验内容完成度**
   项目功能比较完整，包含前端、后端、数据库和 AI 工作流，符合综合实验要求。

2. **实验过程分析**
   报告给出了系统结构、数据关系、业务流程和设计模式分析，能够体现程序设计思想。

3. **实验结果分析**
   报告预留并嵌入运行截图位置，分析了正常流程和异常流程。

4. **实验报告格式**
   报告按照要求的章节组织，结构规范，内容完整。

实验过程中也发现了一些不足：

1. 当前后台任务使用本地线程和文件状态保存，适合单机运行，不适合高并发或多实例部署。
2. provider 选择目前主要通过条件分支实现，后续可以重构为更标准的策略模式。
3. 数据访问逻辑目前分布在模型类和 `DatabaseManager` 中，后续可以进一步抽象 Repository 或 DAO 层。
4. 前端主页面使用较多原生 JavaScript，全局状态较多，后续可以进一步组件化。
5. PaperBanana 工作流运行时间较长，后续可以加入任务队列、进度推送和缓存机制。

## 七、实验体会

本次综合实验最大的特点是自主选题、自主实现和自主总结。相比按照固定题目完成一个小程序，自主项目需要先判断做什么有意义，再考虑如何完成系统功能，最后还要回到代码中说明设计模式是如何帮助项目变得清晰和可维护的。

通过本项目，我对设计模式有了更具体的理解。以前学习设计模式时，容易把模式理解为书本上的类图和概念，例如单例、适配器、外观、模板等。但在 MatchDrawer 中，这些模式不是孤立存在的，而是自然出现在真实工程问题中。

例如，项目中有多个服务对象需要被不同模块使用，如果每次都手动创建对象，代码会重复且容易状态不一致，因此使用单例模式和服务定位器模式；多个 API 路由都需要登录校验和错误处理，如果每个路由都写一遍，代码会混乱，因此使用装饰器模式；不同 AI provider 和 PaperBanana 返回结果不同，如果前端直接处理所有差异，会导致前端复杂度上升，因此使用适配器模式统一返回格式；PaperBanana 多个 Agent 都有相同的 `process()` 入口，因此使用模板模式和多态思想组织代码。

本次实验也让我认识到，设计模式的价值不在于“用了多少个模式”，而在于是否真正解决了项目中的复杂性。MatchDrawer 中的设计模式主要解决了四类问题：第一是模块解耦，例如路由层通过外观服务访问复杂业务；第二是流程组织，例如 PaperBanana 多 Agent 通过统一接口串联；第三是接口适配，例如不同 provider 和本地工作流都转换成统一结果结构；第四是复用和安全，例如服务单例、登录装饰器和密钥加密封装减少了重复代码。一个好的设计模式应用应该让代码更容易理解、更容易扩展、更容易测试。如果只是为了在报告中写出模式名称而强行套用，反而会增加复杂度。

在调试过程中，我对异步任务状态管理印象比较深。AI 图像生成不是一个瞬间完成的操作，如果直接同步等待，浏览器可能长时间无响应，用户也不知道任务是否还在运行。通过任务 ID、状态文件、阶段字段和前端轮询，系统能够把长时间任务拆成可观察的多个阶段，用户体验和调试效率都更好。

另一个收获是敏感信息处理必须从设计阶段就考虑。API Key 是调用外部 AI 服务的重要凭证，如果直接明文保存在前端或数据库中，会带来安全风险。本项目通过后端统一管理、数据库加密保存和前端掩码展示，提升了系统安全性。

总的来说，本项目完成了从自主选题、系统设计、功能实现、设计模式落地到测试分析的完整过程。通过本次实验，我不仅完成了一个可运行的 AI 科研绘图 Web 系统，也更加理解了设计模式在真实项目中的作用。后续如果继续完善，我会重点优化任务队列、provider 策略抽象、前端组件化和自动化测试覆盖率，使 MatchDrawer 在保持功能完整的同时，进一步体现低耦合、高内聚和易扩展的设计目标。

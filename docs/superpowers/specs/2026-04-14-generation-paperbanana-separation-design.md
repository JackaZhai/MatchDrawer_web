# Generation And PaperBanana Separation Design

**Goal**

把当前左侧 `图像生成` 页里混杂的通用生图能力与 `PaperBanana` 专业工作流拆成两个独立界面。

**Scope**

- 左侧导航新增独立的 `PaperBanana` 入口。
- `图像生成` 页面只保留通用生图参数、参考图、提交按钮和结果展示。
- `PaperBanana` 页面承接实验模式、检索、critic/eval、流程预览和阶段状态。
- 现有后端接口保持不变，前端根据当前页面决定提交哪些参数。

**Design**

- `templates/index.html` 增加新的导航项和新的页面 section。
- 通用页面移除所有 `PaperBanana` 专属控件与文案，改成简洁的单次生成表单。
- `PaperBanana` 页面单独展示工作流参数、状态图和阶段信息。
- `static/js/app.js` 继续复用现有生成与轮询逻辑，但把 DOM 绑定和提交参数拆分成“通用生成”和“PaperBanana 工作流”两套入口。
- 增加页面级 smoke test，确保两个页面的关键文案分离正确。

**Testing**

- 页面 smoke test 覆盖导航和两个页面的关键文案。
- 回归现有品牌与部署测试。

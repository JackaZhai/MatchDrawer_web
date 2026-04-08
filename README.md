# SCIdrawer Web

`SCIdrawer_web` 是 `SCIdrawer` 的网页版主仓库。当前已经迁入原项目的 Flask Web 子集，后续网页端改动应优先提交到这里。

## 当前内容

- Flask 应用入口 `app.py`
- Web UI 模板 `templates/`
- 静态资源 `static/`
- 核心后端模块 `src/`
- 基础运行配置 `requirements.txt`、`.env.example`、`pyproject.toml`

## 启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

默认访问地址：

```text
http://127.0.0.1:8788
```

默认登录账号：

- 用户名：`admin`
- 密码：`banana123`

可通过环境变量 `AUTH_USERNAME` 和 `AUTH_PASSWORD` 覆盖。

## 下一步迁移方向

- 清理桌面端/Electron 相关文案和发布逻辑
- 逐步补齐网页版部署方式
- 继续把新增功能统一落在这个仓库

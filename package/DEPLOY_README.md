# MatchDrawer Web Deployment Package

这个 `package/` 目录是从仓库中整理出的上线包，保留了当前 Linux 部署所需的主要运行文件，去掉了本地开发和仓库管理相关内容。

## 已包含

- Flask 应用入口：`app.py`
- 主站运行代码：`src/`
- 页面模板与静态资源：`templates/`、`static/`
- 生产配置：`gunicorn.conf.py`、`deploy/`、`scripts/deploy_linux.sh`
- 环境变量模板：`.env.example`
- 运行依赖：`requirements.txt`
- `PaperBanana` 运行子树：`integrations/PaperBanana/{agents,configs,prompts,style_guides,utils}`

## 未包含

- `.git/`、`.venv/`、`__pycache__/`
- `tests/`、`docs/`、`pyproject.toml`
- 本地数据库内容和运行日志
- `PaperBanana` 的 notebook、演示页面、仓库元信息等非主站运行必需内容

## 上线前要做

1. 复制 `.env.example` 为 `.env`
2. 修改以下关键配置：
   - `APP_SECRET_KEY`
   - `AUTH_USERNAME`
   - `AUTH_PASSWORD`
   - `NANO_BANANA_API_KEY`
3. 在服务器安装 Python 3.14 并执行：

```bash
python3.14 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

4. 按 `deploy/systemd/matchdrawer.service` 和 `deploy/nginx/matchdrawer.conf` 挂载服务

## 目录说明

- `data/` 和 `logs/` 已预留为空目录，供部署后生成数据库、任务状态和日志
- `integrations/PaperBanana` 使用的是运行所需子集；默认配置下如果缺少 `PaperBananaBench` 数据集，会自动退化为无检索模式


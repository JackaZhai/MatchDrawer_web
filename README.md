# MatchDrawer Web

`MatchDrawer_web` is the web-first repository for MatchDrawer. It contains the Flask-based browser console for general diagram work, while preserving the full `PaperBanana` professional workflow for complex structured generation tasks.

## Run Locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Default URL:

```text
http://127.0.0.1:8788
```

Default login:

- Username: `admin`
- Password: `banana123`

Override with `AUTH_USERNAME` and `AUTH_PASSWORD` when needed.

## Deploy On Linux

Docker Compose deployment:

```bash
git clone <your-repo-url> /opt/matchdrawer/MatchDrawer_web
cd /opt/matchdrawer/MatchDrawer_web
cp .env.example .env
docker compose up -d --build
```

The Compose stack exposes the app on port `8788` and persists runtime data under `runtime/data`.

Native Python deployment:

```bash
git clone <your-repo-url> /opt/matchdrawer/MatchDrawer_web
cd /opt/matchdrawer/MatchDrawer_web
/usr/bin/python3.14 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Deployment templates:

- systemd: [deploy/systemd/matchdrawer.service](deploy/systemd/matchdrawer.service)
- nginx: [deploy/nginx/matchdrawer.conf](deploy/nginx/matchdrawer.conf)
- gunicorn config: [gunicorn.conf.py](gunicorn.conf.py)
- helper script: [scripts/deploy_linux.sh](scripts/deploy_linux.sh)

Notes:

- Keep `integrations/PaperBanana` present on the server.
- Reverse proxy `/static/` with nginx when possible.
- For production, do not run `python app.py` directly.

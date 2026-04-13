# MatchDrawer Web

`MatchDrawer_web` is the web-first repository for MatchDrawer. It currently contains the migrated Flask web subset from the desktop project, and future browser-focused changes should land here.

## Current Scope

- Flask entrypoint in `app.py`
- Server-side templates in `templates/`
- Static assets in `static/`
- Core backend modules in `src/`
- Basic runtime config in `requirements.txt`, `.env.example`, and `pyproject.toml`

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

Recommended stack:

- `gunicorn` for the Flask app
- `systemd` for process management
- `nginx` as reverse proxy

Quick setup:

```bash
git clone <your-repo-url> /opt/matchdrawer/MatchDrawer_web
cd /opt/matchdrawer/MatchDrawer_web
/usr/bin/python3.14 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env`, especially:

- `APP_SECRET_KEY`
- `AUTH_USERNAME`
- `AUTH_PASSWORD`
- `NANO_BANANA_API_KEY`
- `NANO_BANANA_HOST`

Start with Gunicorn:

```bash
.venv/bin/gunicorn -c gunicorn.conf.py app:app
```

Deployment templates:

- systemd: [deploy/systemd/matchdrawer.service](deploy/systemd/matchdrawer.service)
- nginx: [deploy/nginx/matchdrawer.conf](deploy/nginx/matchdrawer.conf)
- gunicorn config: [gunicorn.conf.py](gunicorn.conf.py)
- helper script: [scripts/deploy_linux.sh](scripts/deploy_linux.sh)

## Notes

- Keep `integrations/PaperBanana` present on the server.
- Reverse proxy `/static/` with nginx when possible.
- For production, do not run `python app.py` directly.

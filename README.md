# SCIdrawer Web

`SCIdrawer_web` is the web-first repository for SCIdrawer. It currently contains the migrated Flask web subset from the desktop project, and future browser-focused changes should land here.

## Current Scope

- Flask entrypoint in `app.py`
- Server-side templates in `templates/`
- Static assets in `static/`
- Core backend modules in `src/`
- Basic runtime config in `requirements.txt`, `.env.example`, and `pyproject.toml`

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
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

## Next Steps

- Remove remaining legacy compatibility traces
- Add a clearer web deployment flow
- Keep new feature work unified in this repository

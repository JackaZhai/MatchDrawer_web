#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/scidrawer/SCIdrawer_web}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3.14}"

cd "$APP_DIR"

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p data logs

echo "Deployment dependencies installed."
echo "Next steps:"
echo "1. Edit $APP_DIR/.env"
echo "2. Install deploy/systemd/scidrawer.service to /etc/systemd/system/"
echo "3. Install deploy/nginx/scidrawer.conf to your nginx sites config"
echo "4. Start with: sudo systemctl enable --now scidrawer"

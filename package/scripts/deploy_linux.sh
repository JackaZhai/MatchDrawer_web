#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/matchdrawer/MatchDrawer_web}"
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
echo "2. Install deploy/systemd/matchdrawer.service to /etc/systemd/system/"
echo "3. Install deploy/nginx/matchdrawer.conf to your nginx sites config"
echo "4. Start with: sudo systemctl enable --now matchdrawer"

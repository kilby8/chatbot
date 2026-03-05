#!/usr/bin/env bash
set -euo pipefail

# Install and enable Site2CAD as a systemd service.
# This sets up a local virtualenv and starts Streamlit on boot.

SERVICE_NAME="${SERVICE_NAME:-site2cad}"
APP_DIR="${APP_DIR:-$(pwd)}"
APP_USER="${APP_USER:-${SUDO_USER:-$USER}}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8501}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"

usage() {
  echo "Usage:"
  echo "  APP_DIR=/opt/site2cad APP_USER=ubuntu ./scripts/setup_site2cad_service.sh"
  echo
  echo "Optional env vars:"
  echo "  SERVICE_NAME=site2cad"
  echo "  HOST=127.0.0.1         # use 0.0.0.0 only if you intentionally expose Streamlit"
  echo "  PORT=8501"
  echo "  PYTHON_BIN=python3"
  echo "  VENV_DIR=<app-dir>/.venv"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -f "$APP_DIR/streamlit_app.py" || ! -f "$APP_DIR/requirements.txt" ]]; then
  echo "Error: APP_DIR must contain streamlit_app.py and requirements.txt"
  echo "APP_DIR: $APP_DIR"
  exit 1
fi

if ! id "$APP_USER" >/dev/null 2>&1; then
  echo "Error: APP_USER does not exist: $APP_USER"
  exit 1
fi

run_system() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

run_as_app_user() {
  if [[ "$(id -u)" -eq 0 ]]; then
    if command -v runuser >/dev/null 2>&1; then
      runuser -u "$APP_USER" -- "$@"
    else
      su -s /bin/bash "$APP_USER" -c "$(printf '%q ' "$@")"
    fi
  elif [[ "$(id -un)" == "$APP_USER" ]]; then
    "$@"
  else
    sudo -u "$APP_USER" "$@"
  fi
}

echo "[1/5] Creating virtual environment..."
run_as_app_user "$PYTHON_BIN" -m venv "$VENV_DIR"

echo "[2/5] Installing Python dependencies..."
run_as_app_user "$VENV_DIR/bin/pip" install --upgrade pip
run_as_app_user "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
echo "[3/5] Writing systemd service: $SERVICE_FILE"
cat <<EOF | run_system tee "$SERVICE_FILE" >/dev/null
[Unit]
Description=Site2CAD Streamlit app
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${VENV_DIR}/bin/streamlit run ${APP_DIR}/streamlit_app.py --server.headless true --server.address ${HOST} --server.port ${PORT} --browser.gatherUsageStats false
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "[4/5] Enabling and starting service..."
run_system systemctl daemon-reload
run_system systemctl enable --now "$SERVICE_NAME"
run_system systemctl restart "$SERVICE_NAME"

echo "[5/5] Service ready."
echo
echo "Service status:"
echo "  sudo systemctl status ${SERVICE_NAME} --no-pager"
echo
echo "Service logs:"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
echo
echo "If using SSH tunnel:"
echo "  ssh -L ${PORT}:localhost:${PORT} ${APP_USER}@<SERVER_PUBLIC_IP>"
echo "Then open: http://localhost:${PORT}"

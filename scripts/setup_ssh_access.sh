#!/usr/bin/env bash
set -euo pipefail

# Secure SSH bootstrap for Ubuntu/Debian hosts.
# Defaults to key-based auth and disables root login.

APP_USER="${APP_USER:-${SUDO_USER:-$USER}}"
SSH_PORT="${SSH_PORT:-22}"
ALLOW_PASSWORD="${ALLOW_PASSWORD:-no}"
PUBLIC_KEY_FILE="${PUBLIC_KEY_FILE:-}"
PUBLIC_KEY_VALUE="${PUBLIC_KEY_VALUE:-}"

usage() {
  echo "Usage:"
  echo "  APP_USER=ubuntu PUBLIC_KEY_FILE=~/.ssh/id_ed25519.pub ./scripts/setup_ssh_access.sh"
  echo "  APP_USER=ubuntu PUBLIC_KEY_VALUE='ssh-ed25519 AAAA...' ./scripts/setup_ssh_access.sh"
  echo
  echo "Optional env vars:"
  echo "  SSH_PORT=22            # SSH daemon port"
  echo "  ALLOW_PASSWORD=no      # yes|no (default: no)"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "$PUBLIC_KEY_FILE" && -z "$PUBLIC_KEY_VALUE" ]]; then
  echo "Error: set PUBLIC_KEY_FILE or PUBLIC_KEY_VALUE."
  usage
  exit 1
fi

if [[ -n "$PUBLIC_KEY_FILE" && ! -f "$PUBLIC_KEY_FILE" ]]; then
  echo "Error: PUBLIC_KEY_FILE not found: $PUBLIC_KEY_FILE"
  exit 1
fi

SUDO="sudo"
if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=""
fi

echo "[1/6] Installing openssh-server..."
$SUDO apt-get update -y
$SUDO apt-get install -y openssh-server

if ! id "$APP_USER" >/dev/null 2>&1; then
  echo "[2/6] Creating user $APP_USER..."
  $SUDO adduser --disabled-password --gecos "" "$APP_USER"
else
  echo "[2/6] User $APP_USER already exists."
fi

echo "[3/6] Configuring authorized_keys..."
$SUDO mkdir -p "/home/$APP_USER/.ssh"
$SUDO chmod 700 "/home/$APP_USER/.ssh"

if [[ -n "$PUBLIC_KEY_FILE" ]]; then
  $SUDO cp "$PUBLIC_KEY_FILE" "/home/$APP_USER/.ssh/authorized_keys"
else
  echo "$PUBLIC_KEY_VALUE" | $SUDO tee "/home/$APP_USER/.ssh/authorized_keys" >/dev/null
fi

$SUDO chmod 600 "/home/$APP_USER/.ssh/authorized_keys"
$SUDO chown -R "$APP_USER:$APP_USER" "/home/$APP_USER/.ssh"

SSHD_CONFIG="/etc/ssh/sshd_config"
echo "[4/6] Hardening SSH config at $SSHD_CONFIG..."
$SUDO cp "$SSHD_CONFIG" "${SSHD_CONFIG}.bak.$(date +%s)"

set_sshd_option() {
  local key="$1"
  local value="$2"
  if $SUDO grep -Eq "^[#[:space:]]*${key}[[:space:]]+" "$SSHD_CONFIG"; then
    $SUDO sed -i -E "s|^[#[:space:]]*${key}[[:space:]]+.*|${key} ${value}|g" "$SSHD_CONFIG"
  else
    echo "${key} ${value}" | $SUDO tee -a "$SSHD_CONFIG" >/dev/null
  fi
}

set_sshd_option "Port" "$SSH_PORT"
set_sshd_option "PermitRootLogin" "no"
set_sshd_option "PubkeyAuthentication" "yes"
set_sshd_option "PasswordAuthentication" "$ALLOW_PASSWORD"
set_sshd_option "ChallengeResponseAuthentication" "no"
set_sshd_option "UsePAM" "yes"
set_sshd_option "AllowUsers" "$APP_USER"

echo "[5/6] Restarting SSH service..."
if $SUDO systemctl list-unit-files | grep -q "^ssh.service"; then
  $SUDO systemctl enable --now ssh
  $SUDO systemctl restart ssh
else
  $SUDO systemctl enable --now sshd
  $SUDO systemctl restart sshd
fi

echo "[6/6] Done."
echo
echo "Connect from your laptop:"
echo "  ssh -p ${SSH_PORT} ${APP_USER}@<SERVER_PUBLIC_IP>"
echo
echo "Tunnel Streamlit securely:"
echo "  ssh -p ${SSH_PORT} -L 8501:localhost:8501 ${APP_USER}@<SERVER_PUBLIC_IP>"
echo "Then open: http://localhost:8501"

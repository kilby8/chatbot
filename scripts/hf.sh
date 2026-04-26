#!/usr/bin/env bash
set -euo pipefail

VENV_PATH="${HF_CLI_VENV_PATH:-$HOME/.venvs/hf-cli}"
HF_BIN="$VENV_PATH/bin/hf"

if [[ ! -x "$HF_BIN" ]]; then
  echo "hf CLI venv not found at $VENV_PATH" >&2
  echo "Bootstrapping isolated hf CLI environment..." >&2
  "$(dirname "$0")/setup_hf_cli.sh" --no-skills --venv-path "$VENV_PATH"
fi

exec "$HF_BIN" "$@"

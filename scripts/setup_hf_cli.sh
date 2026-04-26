#!/usr/bin/env bash
set -euo pipefail

VENV_PATH="${HF_CLI_VENV_PATH:-$HOME/.venvs/hf-cli}"
INSTALL_SCOPE="global"
CLAUDE_MODE="false"
SKIP_SKILL_INSTALL="false"

usage() {
  cat <<'EOF'
Usage: scripts/setup_hf_cli.sh [options]

Creates an isolated Python virtual environment for the latest hf CLI,
then optionally installs Hugging Face agent skills.

Options:
  --venv-path PATH   Virtual environment path (default: ~/.venvs/hf-cli)
  --project          Install skills for current project only
  --global           Install skills globally (default)
  --claude           Use --claude flag for skill install commands
  --no-skills        Skip hf skills install step
  --help             Show this help message

Examples:
  scripts/setup_hf_cli.sh
  scripts/setup_hf_cli.sh --project
  scripts/setup_hf_cli.sh --claude --global
  scripts/setup_hf_cli.sh --no-skills

After setup, activate with:
  source "$HOME/.venvs/hf-cli/bin/activate"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv-path)
      [[ $# -ge 2 ]] || { echo "Missing value for --venv-path" >&2; exit 1; }
      VENV_PATH="$2"
      shift 2
      ;;
    --project)
      INSTALL_SCOPE="project"
      shift
      ;;
    --global)
      INSTALL_SCOPE="global"
      shift
      ;;
    --claude)
      CLAUDE_MODE="true"
      shift
      ;;
    --no-skills)
      SKIP_SKILL_INSTALL="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$VENV_PATH")"
python -m venv "$VENV_PATH"

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

python -m pip install --upgrade pip
python -m pip install --upgrade huggingface_hub

if ! command -v hf >/dev/null 2>&1; then
  echo "hf command was not found after install." >&2
  exit 1
fi

echo "hf version: $(hf --version)"

echo "Login with: hf auth login"

if [[ "$SKIP_SKILL_INSTALL" == "true" ]]; then
  echo "Skipping hf skills installation by request."
  exit 0
fi

if [[ "$INSTALL_SCOPE" == "project" ]]; then
  if [[ "$CLAUDE_MODE" == "true" ]]; then
    hf skills add --claude
  else
    hf skills add
  fi
else
  if [[ "$CLAUDE_MODE" == "true" ]]; then
    hf skills add --claude --global
  else
    hf skills add --global
  fi
fi

echo "Setup complete. Activate with: source \"$VENV_PATH/bin/activate\""

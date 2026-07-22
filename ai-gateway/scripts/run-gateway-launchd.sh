#!/usr/bin/env bash
set -euo pipefail

gateway_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${AI_GATEWAY_ENV_FILE:-$HOME/.config/local-ai/gateway.env}"
cd "$gateway_dir"

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing Python environment: $gateway_dir/.venv/bin/python" >&2
  exit 1
fi
if [[ ! -f "$env_file" ]]; then
  echo "Missing environment file: $env_file" >&2
  exit 1
fi

# The environment file uses KEY=value syntax, which works for launchd and Bash.
set -a
# shellcheck disable=SC1090
source "$env_file"
set +a

if [[ -z "${AI_GATEWAY_API_KEY:-}" ]]; then
  echo "AI_GATEWAY_API_KEY is not set." >&2
  exit 1
fi

mkdir -p logs
exec .venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info --access-log

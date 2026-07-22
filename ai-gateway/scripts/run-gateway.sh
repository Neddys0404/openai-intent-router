#!/usr/bin/env bash
set -euo pipefail

gateway_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$gateway_dir"

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing Python environment: $gateway_dir/.venv/bin/python" >&2
  exit 1
fi

if [[ -z "${AI_GATEWAY_API_KEY:-}" ]]; then
  echo "AI_GATEWAY_API_KEY is not set." >&2
  exit 1
fi

mkdir -p logs
timestamp="$(date '+%Y-%m-%dT%H:%M:%S%z')"
echo "[$timestamp] Starting AI Gateway on port 8000"
.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info --access-log 2>&1 | tee -a logs/gateway.log

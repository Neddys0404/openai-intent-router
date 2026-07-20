#!/usr/bin/env bash
# Source this from ~/.bashrc to start the gateway once per login session.
set -u

gateway_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
session_name="local-ai"
env_file="${AI_GATEWAY_ENV_FILE:-$HOME/.config/local-ai/gateway.env}"

# Keep the API key outside .bashrc and outside the repository.
if [[ -f "$env_file" ]]; then
  # shellcheck disable=SC1090
  source "$env_file"
fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "local-ai: tmux is not installed; gateway was not started." >&2
  return 0 2>/dev/null || exit 0
fi

if tmux has-session -t "$session_name" 2>/dev/null; then
  return 0 2>/dev/null || exit 0
fi

if [[ ! -x "$gateway_dir/.venv/bin/python" ]]; then
  echo "local-ai: missing $gateway_dir/.venv; gateway was not started." >&2
  return 0 2>/dev/null || exit 0
fi

if [[ -z "${AI_GATEWAY_API_KEY:-}" ]]; then
  echo "local-ai: AI_GATEWAY_API_KEY is not set; gateway was not started." >&2
  return 0 2>/dev/null || exit 0
fi

tmux new-session -d -s "$session_name" -c "$gateway_dir" bash ./scripts/run-gateway.sh
echo "local-ai: gateway started in tmux session '$session_name'."

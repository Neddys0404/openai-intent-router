#!/usr/bin/env bash
set -euo pipefail

gateway_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
service_file="$service_dir/ai-gateway.service"
env_file="${AI_GATEWAY_ENV_FILE:-$HOME/.config/local-ai/gateway.env}"

if [[ ! -x "$gateway_dir/.venv/bin/python" ]]; then
  echo "Missing Python environment: $gateway_dir/.venv/bin/python" >&2
  exit 1
fi
if [[ ! -f "$env_file" ]]; then
  echo "Missing environment file: $env_file" >&2
  exit 1
fi

mkdir -p "$service_dir"
cat > "$service_file" <<EOF
[Unit]
Description=Local AI Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$gateway_dir
EnvironmentFile=$env_file
ExecStart=$gateway_dir/.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info --access-log
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now ai-gateway.service
echo "Installed and started ai-gateway.service."

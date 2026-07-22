#!/usr/bin/env bash
set -euo pipefail

gateway_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
label="local.ai-gateway"
launch_agents_dir="$HOME/Library/LaunchAgents"
plist="$launch_agents_dir/$label.plist"
log_dir="$gateway_dir/logs"
uid="$(id -u)"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer must be run on macOS." >&2
  exit 1
fi
if [[ ! -x "$gateway_dir/.venv/bin/python" ]]; then
  echo "Missing macOS Python environment: $gateway_dir/.venv/bin/python" >&2
  exit 1
fi
if [[ ! -f "${AI_GATEWAY_ENV_FILE:-$HOME/.config/local-ai/gateway.env}" ]]; then
  echo "Missing environment file: ${AI_GATEWAY_ENV_FILE:-$HOME/.config/local-ai/gateway.env}" >&2
  exit 1
fi

mkdir -p "$launch_agents_dir" "$log_dir"
cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$gateway_dir/scripts/run-gateway-launchd.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$gateway_dir</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ProcessType</key>
  <string>Background</string>
  <key>StandardOutPath</key>
  <string>$log_dir/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>$log_dir/launchd.err.log</string>
</dict>
</plist>
EOF

plutil -lint "$plist"
launchctl bootout "gui/$uid/$label" 2>/dev/null || true
launchctl bootstrap "gui/$uid" "$plist"
launchctl kickstart -k "gui/$uid/$label"

echo "Installed and started $label."
echo "Status: launchctl print gui/$uid/$label"
echo "Logs:   tail -f '$log_dir/launchd.out.log' '$log_dir/launchd.err.log'"

#!/usr/bin/env bash
set -euo pipefail

gateway_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
label="local.ai-gateway"
plist="/Library/LaunchDaemons/$label.plist"
log_dir="$gateway_dir/logs"
target_user="${SUDO_USER:-}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer must be run on macOS." >&2
  exit 1
fi
if [[ "$(id -u)" -ne 0 || -z "$target_user" || "$target_user" == "root" ]]; then
  echo "Run this headless-server installer with sudo from the target user's SSH session:" >&2
  echo "  sudo bash scripts/install-launchd-headless-service.sh" >&2
  exit 1
fi

target_home="$(dscl . -read "/Users/$target_user" NFSHomeDirectory | awk '{print $2}')"
env_file="${AI_GATEWAY_ENV_FILE:-$target_home/.config/local-ai/gateway.env}"

if [[ ! -x "$gateway_dir/.venv/bin/python" ]]; then
  echo "Missing macOS Python environment: $gateway_dir/.venv/bin/python" >&2
  exit 1
fi
if [[ ! -f "$env_file" ]]; then
  echo "Missing environment file: $env_file" >&2
  exit 1
fi

mkdir -p "$log_dir"
chown "$target_user" "$log_dir"
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
  <key>UserName</key>
  <string>$target_user</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$target_home</string>
    <key>AI_GATEWAY_ENV_FILE</key>
    <string>$env_file</string>
  </dict>
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

chown root:wheel "$plist"
chmod 644 "$plist"
plutil -lint "$plist"
launchctl bootout "system/$label" 2>/dev/null || true
launchctl bootstrap system "$plist"
launchctl kickstart -k "system/$label"

echo "Installed and started $label as $target_user."
echo "Status: launchctl print system/$label"
echo "Logs:   tail -f '$log_dir/launchd.out.log' '$log_dir/launchd.err.log'"

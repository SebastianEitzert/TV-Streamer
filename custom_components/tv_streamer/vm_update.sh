#!/bin/sh
# TV Streamer – fetches docker-compose.yml from Home Assistant and applies it when it changed.
# Served by the Home Assistant integration "TV Streamer"; the values below are filled in by Home Assistant.
#
# Install once on the VM (as root), copy the exact command from the integration's options ("VM setup"):
#   curl -fsSL -H "Authorization: Bearer <token>" <ha>/api/tv_streamer/<entry>/update.sh | sh -s -- install
# After that a systemd timer runs it every 5 minutes. Log: journalctl -u tv-streamer-config
set -eu
HA_URL="__HA_URL__"
ENTRY_ID="__ENTRY_ID__"
HA_TOKEN="__VM_TOKEN__"
DIR="${DIR:-/opt/tv-streamer}"
API="$HA_URL/api/tv_streamer/$ENTRY_ID"

get() {
  curl -fsS -m 30 -H "Authorization: Bearer $HA_TOKEN" "$API/$1"
}

if [ "${1:-}" = "install" ]; then
  mkdir -p "$DIR"
  get update.sh > "$DIR/config-update.sh.neu"
  chmod 700 "$DIR/config-update.sh.neu"
  mv "$DIR/config-update.sh.neu" "$DIR/config-update.sh"
  cat > /etc/systemd/system/tv-streamer-config.service <<EOF
[Unit]
Description=TV Streamer: fetch configuration from Home Assistant
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/sh $DIR/config-update.sh
EOF
  cat > /etc/systemd/system/tv-streamer-config.timer <<'EOF'
[Unit]
Description=TV Streamer: check Home Assistant for a new configuration every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF
  systemctl daemon-reload
  systemctl enable --now tv-streamer-config.timer
  rm -f "$DIR/.config-version"
  echo "Installed – configuration is now fetched from $HA_URL every 5 minutes."
  if [ ! -f "$DIR/Dockerfile" ] && ! docker image inspect "$(grep -m1 'image:' "$DIR/docker-compose.yml" 2>/dev/null | awk '{print $2}')" >/dev/null 2>&1; then
    echo "Note: no Dockerfile in $DIR – the streamer image must be built first (see the README of the TV Streamer repository)."
  fi
fi

NEW=$(get version) || { echo "Home Assistant not reachable or token rejected"; exit 0; }
OLD=$(cat "$DIR/.config-version" 2>/dev/null || true)
[ -n "$NEW" ] || exit 0
[ "$NEW" = "$OLD" ] && exit 0
echo "new configuration $NEW (was: ${OLD:-none})"
cd "$DIR"
get docker-compose.yml > docker-compose.yml.neu
docker compose -f docker-compose.yml.neu config -q
[ -f docker-compose.yml ] && cp docker-compose.yml docker-compose.yml.bak
mv docker-compose.yml.neu docker-compose.yml
docker compose up -d --build --remove-orphans
echo "$NEW" > .config-version

"""Constants for the TV Streamer integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "tv_streamer"

# Config entry data (set once in the config flow)
CONF_HOST: Final = "host"  # address of the streamer VM
CONF_HA_URL: Final = "ha_url"  # address of Home Assistant as seen from the VM
CONF_VM_TOKEN: Final = "vm_token"  # bearer token the VM uses for the config endpoint
CONF_WEBHOOK_ID: Final = "webhook_id"  # webhook the streamers report to

# Config entry options (changed in the options flow)
CONF_STREAMERS: Final = "streamers"
CONF_LINKS: Final = "links"
CONF_START_URL: Final = "start_url"
CONF_FREEZE_AFTER: Final = "freeze_after"
CONF_HOME_AFTER: Final = "home_after"
CONF_RASTER_THREADS: Final = "raster_threads"
CONF_AUDIO: Final = "audio"
CONF_LG_RENEW_TIME: Final = "lg_renew_time"
CONF_IMAGE: Final = "image"
CONF_TIMEZONE: Final = "timezone"
CONF_GREEN_TAB: Final = "green_tab"  # what the green key opens: "first" extra tab, "none" or a tab name
GREEN_FIRST: Final = "first"
GREEN_NONE: Final = "none"

# Per streamer
CONF_ID: Final = "id"
CONF_NAME: Final = "name"
CONF_AREA: Final = "area"
CONF_MEDIA_PLAYER: Final = "media_player"
CONF_INDEX: Final = "index"  # slot number, determines all ports
CONF_TV_TYPE: Final = "tv_type"
CONF_VIDEO_PATH: Final = "video_path"
CONF_WIDTH: Final = "width"
CONF_HEIGHT: Final = "height"
CONF_ZOOM: Final = "zoom"
CONF_BITRATE: Final = "bitrate"
CONF_LG_TOKEN: Final = "lg_session_token"
CONF_WAKE: Final = "wake_entity"  # button/script that switches the TV on (e.g. Wake on LAN)
WAKE_DOMAINS: Final = ["button", "input_button", "script", "switch"]
TV_OFF_STATES: Final = {"off", "unavailable", "unknown", "standby"}
WAKE_TIMEOUT: Final = 90  # s until the TV must report itself on
LAUNCH_RETRY: Final = 3  # s to wait for the app to appear before starting it again
LAUNCH_TIMEOUT: Final = 20  # s to keep trying right after switching on
MOONLIGHT_APP: Final = "com.limelight.webos"

# Per link (extra browser tabs, e.g. a Loxone web interface)
CONF_URL: Final = "url"
CONF_REMEMBER_LOGIN: Final = "remember_login"
CONF_NO_RELOAD: Final = "no_reload"

VIDEO_MSE: Final = "mse"
VIDEO_WEBRTC: Final = "webrtc"
VIDEO_MOONLIGHT: Final = "moonlight"
VIDEO_PATHS: Final = [VIDEO_MSE, VIDEO_WEBRTC, VIDEO_MOONLIGHT]

TV_LG_WEBOS4: Final = "lg_webos4"
TV_LG_WEBOS5: Final = "lg_webos5"
TV_LG_OTHER: Final = "lg_other"
TV_OTHER: Final = "other"
TV_TYPES: Final = [TV_LG_WEBOS4, TV_LG_WEBOS5, TV_LG_OTHER, TV_OTHER]
LG_TV_TYPES: Final = {TV_LG_WEBOS4, TV_LG_WEBOS5, TV_LG_OTHER}

# Confirmed settings per TV type: width, height, zoom, bitrate, video path.
# webOS 4 (e.g. LG UK7550) shows WebRTC squeezed to 4:3 and frozen, so it gets MSE or Moonlight.
TV_PRESETS: Final[dict[str, dict]] = {
    TV_LG_WEBOS4: {CONF_WIDTH: 1920, CONF_HEIGHT: 1080, CONF_ZOOM: 1.25, CONF_BITRATE: 12, CONF_VIDEO_PATH: VIDEO_MOONLIGHT},
    TV_LG_WEBOS5: {CONF_WIDTH: 2560, CONF_HEIGHT: 1440, CONF_ZOOM: 1.67, CONF_BITRATE: 16, CONF_VIDEO_PATH: VIDEO_MOONLIGHT},
    TV_LG_OTHER: {CONF_WIDTH: 1920, CONF_HEIGHT: 1080, CONF_ZOOM: 1.25, CONF_BITRATE: 12, CONF_VIDEO_PATH: VIDEO_MSE},
    TV_OTHER: {CONF_WIDTH: 1920, CONF_HEIGHT: 1080, CONF_ZOOM: 1.25, CONF_BITRATE: 12, CONF_VIDEO_PATH: VIDEO_MSE},
}

DEFAULT_FREEZE_AFTER: Final = 60  # s without viewers before the HA tab rests
DEFAULT_HOME_AFTER: Final = 300  # s of Moonlight pause before the start view is shown again
DEFAULT_RASTER_THREADS: Final = 4  # Chromium maximum, makes pop-ups noticeably faster
DEFAULT_LG_RENEW_TIME: Final = "04:17:00"
DEFAULT_IMAGE: Final = "tv-streamer:local"

# Ports: slot n (0, 1, …) gets HTTP 8091+n, WebRTC 8555+n and a Sunshine port block starting at 47989+100·n
HTTP_PORT_BASE: Final = 8091
WEBRTC_PORT_BASE: Final = 8555
SUNSHINE_PORT_BASE: Final = 47989
SUNSHINE_PORT_STEP: Final = 100
MAX_STREAMERS: Final = 8

# LG developer mode session (webOS Dev Manager / developer.lge.com)
LG_RENEW_URL: Final = "https://developer.lge.com/secure/ResetDevModeSession.dev"
LG_CHECK_URL: Final = "https://developer.lge.com/secure/CheckDevModeSession.dev"

# Endpoints for the VM (authenticated with the VM token, not with an HA user)
API_BASE: Final = "/api/tv_streamer"
API_VERSION: Final = API_BASE + "/{entry_id}/version"
API_COMPOSE: Final = API_BASE + "/{entry_id}/docker-compose.yml"
API_UPDATE_SCRIPT: Final = API_BASE + "/{entry_id}/update.sh"
API_FILES: Final = API_BASE + "/{entry_id}/files"
API_FILE: Final = API_BASE + "/{entry_id}/files/{name}"

SCAN_INTERVAL_SECONDS: Final = 60
SIGNAL_KEY: Final = DOMAIN + "_key_{}_{}"  # entry id, streamer id
REMOTE_KEYS: Final = ["blue", "green", "play", "pause", "stop"]
EVENT_KEY: Final = "tv_streamer_key"  # remote key from the patched Moonlight app

# Commands understood by server.py (POST /api/cmd {"c": …})
CMD_START_VIEW: Final = "startansicht"
CMD_RELOAD: Final = "reload"
CMD_BACK: Final = "back"
CMD_HOME_TAB: Final = "zeige_home"

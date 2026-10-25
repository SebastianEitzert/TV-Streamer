# TV Streamer for Home Assistant

🇩🇪 [Deutsche Fassung](README.de.md)

Show Home Assistant dashboards on TVs, served from a small VM: one Chromium per TV, rendered off-screen and sent to the TV as
**MSE** video, **WebRTC** or via **Sunshine/Moonlight**. Mouse, TV remote and touch work on the dashboard as if a PC were connected.

This repository contains:

| Part | Status |
|---|---|
| `custom_components/tv_streamer` – Home Assistant integration (setup in the UI, devices, sensors, LG developer mode renewal, config endpoint for the VM) | **0.1 – first version** |
| VM image (Docker: `server.py`, Chromium, Sunshine) and Proxmox setup | planned |
| Floor plan Lovelace card (HACS) | planned |
| Patched Moonlight for LG webOS (`.ipk`, GPL-3.0) | planned |
| What we tested (webOS 4/5, MSE vs. WebRTC, raster threads, iGPU limits) | planned |

## The integration

**Setup in the UI** – no YAML:

- One config entry per VM: VM address and the address of Home Assistant as seen from the VM.
- **Options → Add streamer**: name, room, TV (`media_player`), TV type, video path (MSE / WebRTC / Moonlight), picture size, zoom,
  bit rate. The TV type fills in settings that were confirmed on real TVs:

  | TV type | Picture | Zoom | Recommended path |
  |---|---|---|---|
  | LG webOS 4 (e.g. UK7550) | 1920×1080 | 1.25 | Moonlight or MSE (WebRTC shows 4:3 and freezes) |
  | LG webOS 5+ (e.g. 86UN85) | 2560×1440 | 1.67 | Moonlight |
  | other | 1920×1080 | 1.25 | MSE |

- **Extra tabs** (e.g. Loxone): name, address, *remember login*, *never reload*.
- **General settings**: start view, rest time without viewers, *back to start view after* (Moonlight pause), Chromium raster threads, audio.
- **VM setup**: shows a one-line command for the VM (see below).

**Per streamer** you get a device (with a link to its web page) and:

| Entity | |
|---|---|
| `sensor.…_state` | showing / resting / ready, attributes: viewers, video path, format, TV |
| `sensor.…_viewers`, `_latency`, `_frame_rate`, `_data_rate` | measurements reported by the streamer |
| `sensor.…_tab`, `_version` | diagnostics |
| `binary_sensor.…_reachable`, `_moonlight_stream` | |
| `button.…_start_view`, `_reload`, `_back`, `_show_<tab>` | remote control of the streamer browser |

The streamers report to a webhook the integration creates (no template sensors needed), and are polled every 60 s.

### LG developer mode

Moonlight is a sideloaded app, so LG TVs need the **developer mode**. LG ends it after about 1000 hours unless it is renewed.
Paste the session token – or the whole renewal URL from the webOS Dev Manager – into the streamer's settings. The integration then

- renews the session every day (default 04:17, configurable),
- shows *developer mode expires* and *last renewal* as sensors and offers a *renew* button,
- raises a **repair** when LG rejects the renewal; the repair asks for a new token and checks it right away.

The token is stored in the config entry only. It is not written to `www/`, the compose file, logs or diagnostics.
Note that Home Assistant stores config entries unencrypted in `.storage/core.config_entries` – protect your backups.

### How the VM gets its configuration

The integration generates the `docker-compose.yml` for the VM and serves it at
`/api/tv_streamer/<entry_id>/docker-compose.yml`. The VM authenticates with its own **VM token** (created with the entry,
shown only in *Options → VM setup*), not with a Home Assistant user. Run the command shown there once as root on the VM:

```sh
curl -fsSL -H "Authorization: Bearer <vm token>" http://<ha>:8123/api/tv_streamer/<entry_id>/update.sh | sh -s -- install
```

It installs a systemd timer (`tv-streamer-config.timer`) that checks every 5 minutes and runs
`docker compose up -d --build --remove-orphans` when the configuration changed. Ports per streamer slot *n* (0, 1, …):
web page `8091+n`, WebRTC `8555+n`, Sunshine `47989+100·n` (web UI +1).

Moving an existing installation: see [docs/migration.md](docs/migration.md).

## Installation

HACS → *Custom repositories* → `https://github.com/SebastianEitzert/TV-Streamer`, category *Integration*. Or copy
`custom_components/tv_streamer` into your `config/custom_components`. Restart, then *Settings → Devices & services → Add integration → TV Streamer*.

## Development

```sh
pip install -r requirements_test.txt
pytest
```

## License

GPL-3.0 – see [LICENSE](LICENSE). The Moonlight part will be based on [moonlight-tv](https://github.com/mariotaku/moonlight-tv) (GPL-3.0).

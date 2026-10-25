<p align="center"><img src="docs/images/logo.png" alt="TV Streamer" width="420"></p>

# TV Streamer for Home Assistant

🇩🇪 [Deutsche Fassung](README.de.md)

Show Home Assistant dashboards on TVs, served from a small VM: one Chromium per TV, rendered off-screen and sent to the TV as
**MSE** video, **WebRTC** or via **Sunshine/Moonlight**. Mouse, TV remote and touch work on the dashboard as if a PC were connected.

| Part | Status |
|---|---|
| `custom_components/tv_streamer` – Home Assistant integration (setup in the UI, devices, sensors, LG developer mode renewal, config endpoint for the VM) | **0.1** |
| `vm/proxmox-vm.sh` – creates the VM on Proxmox VE | **0.1** |
| `custom_components/tv_streamer/streamer` – streamer image (Docker: `server.py`, Chromium, encoders, Sunshine), delivered to the VM by the integration | **0.3** |
| Floor plan Lovelace card (HACS) | planned |
| Patched Moonlight for LG webOS (`.ipk`, GPL-3.0) | planned |

## Setup guide

```
Proxmox VE host ──► VM "tv-streamer" (Debian 13 + Docker)
                     ├─ streamer 1 (Chromium + encoder/Sunshine) ──► TV 1
                     └─ streamer 2 …                             ──► TV 2
Home Assistant ◄──── status reports (webhook) ── streamers
Home Assistant ────► docker-compose.yml (token-protected endpoint) ──► VM
```

### 1. Install Proxmox VE

You need a host running [Proxmox VE](https://www.proxmox.com/en/proxmox-virtual-environment/overview).
Follow the official guide: **[Proxmox VE installation](https://pve.proxmox.com/wiki/Installation)**
([download](https://www.proxmox.com/en/downloads)). Home Assistant can run on the same host (e.g. HA OS as a VM).

Sizing for the streamer VM: per TV about 2 CPU cores and 2 GB RAM with software encoding at 1080p/1440p.
4K is too much for software encoding.

### 2. Create the streamer VM

In the Proxmox web UI open **your node → Shell** and run:

```sh
curl -fsSLo /root/tv-streamer-vm.sh https://raw.githubusercontent.com/SebastianEitzert/TV-Streamer/main/vm/proxmox-vm.sh
bash /root/tv-streamer-vm.sh
```

The script asks for the VM ID, IP address (or DHCP), bridge, storage, cores, RAM and a password for the user `tv`. It
downloads the Debian 13 cloud image (checksum verified), creates the VM and installs Docker on first boot (about 5 minutes).

Give the VM a **fixed IP address** (in the script or as a DHCP reservation in your router) – TVs and Moonlight connect to it.

### 3. Nothing to copy to the VM

The streamer image (`Dockerfile`, `server.py`, `client.html`, Chromium policies, Sunshine) ships **with the integration**.
In step 7 the VM fetches it from Home Assistant together with its configuration and builds it locally – the first build
takes about 10 minutes. After every integration update the VM rebuilds automatically, so both always match.

### 4. Install the integration

**HACS** (repository must be public): HACS → ⋮ → *Custom repositories* → `https://github.com/SebastianEitzert/TV-Streamer`,
category *Integration* → install → restart Home Assistant.

**Manually:** copy `custom_components/tv_streamer` (including `brand/` and `translations/`) to `/config/custom_components/`
of Home Assistant, e.g. with the *Samba share* or *File editor* app → restart Home Assistant.

### 5. Add the VM in Home Assistant

*Settings → Devices & services → Add integration → **TV Streamer***

- **VM address**: the fixed IP of the VM, e.g. `192.168.1.42`
- **Home Assistant address as seen from the VM**: the local URL, e.g. `http://192.168.1.10:8123`

### 6. Configure streamers and tabs

*TV Streamer → Configure*:

1. **Add streamer** – name and TV type, then room, TV (`media_player`), video path, picture size, zoom and bit rate.
   The TV type fills in values confirmed on real TVs:

   | TV type | Picture | Zoom | Recommended path |
   |---|---|---|---|
   | LG webOS 4 (e.g. UK7550) | 1920×1080 | 1.25 | Moonlight or MSE (WebRTC shows 4:3 and freezes) |
   | LG webOS 5+ (e.g. 86UN85) | 2560×1440 | 1.67 | Moonlight |
   | other | 1920×1080 | 1.25 | MSE |

   For LG TVs with Moonlight also paste the **developer mode session token** (see step 9).
2. **Add extra tab** (optional) – e.g. a Loxone or router web interface: name, address, *remember login*, *never reload*.
3. **General settings** – start view (the dashboard the TVs open), rest time, *back to start view after*, raster threads, audio, time zone.
4. **Save.**

Ports per streamer slot *n* (0, 1, …): web page `8091+n`, WebRTC `8555+n`, Sunshine `47989+100·n` (web UI +1).

### 7. Connect the VM to Home Assistant

*Configure → **VM setup*** shows a one-line command with the VM token. Run it once on the VM as root – in the VM console
(`sudo -i` first), or from the Proxmox shell without logging in:

```sh
qm guest exec <VMID> --timeout 600 -- sh -c "<command from VM setup>"
```

It installs the timer `tv-streamer-config.timer`, fetches the streamer image files (checked against SHA-256 checksums)
and the generated `docker-compose.yml`, builds the image and starts the containers.
From now on every change in the integration options reaches the VM within 5 minutes.
Check: `journalctl -u tv-streamer-config` and `docker compose ps` in `/opt/tv-streamer`.

### 8. First login (once per streamer)

On a PC open `http://<VM-IP>:8091/` (second streamer `:8092`, …). You see and control the streamer's Chromium.
Log in to Home Assistant with a dedicated user (e.g. `tv`) and tick *Keep me logged in*. Log in to extra tabs the same way.
The logins stay in the container's Docker volume.

### 9. Set up the TV

**Browser (MSE / WebRTC):** open `http://<VM-IP>:8091/` in the TV's web browser.

**Moonlight (LG webOS):**

1. Create a free LG developer account at <https://webostv.developer.lge.com>.
2. On the TV install **Developer Mode** from the LG Content Store, sign in, switch on *Dev Mode Status* (the TV restarts),
   then switch on *Key Server*.
3. On a PC install the [webOS Dev Manager](https://github.com/webosbrew/dev-manager-desktop/releases), add the TV
   (IP + passphrase from the Developer Mode app) and install [Moonlight TV](https://github.com/mariotaku/moonlight-tv/releases).
4. Open the Sunshine web UI `https://<VM-IP>:47990` (second streamer `:48090`), accept the certificate warning and create
   a Sunshine user and password.
5. In Moonlight on the TV add the host `<VM-IP>` (second streamer `<VM-IP>:48089`); enter the shown PIN in the Sunshine web UI.
6. **Session token for the integration:** copy the developer mode session token from the webOS Dev Manager – either the
   renewal URL (`…/ResetDevModeSession.dev?sessionToken=…`) or just the token. Paste it into the streamer's settings
   (*Configure → Edit streamer → LG developer mode session token*). The integration renews the session every day.

### 10. Check

Each streamer is a device with sensors (state, viewers, latency, frame rate, data rate), *reachable* and *Moonlight stream*
binary sensors and buttons (start view, reload, back, show tab, renew developer mode). If LG rejects a renewal, a
**repair** appears that asks for a new token.

Moving an existing hand-made installation: see [docs/migration.md](docs/migration.md).

## How it works

- The integration generates the `docker-compose.yml` and serves it at `/api/tv_streamer/<entry_id>/docker-compose.yml`.
  The VM authenticates with its own **VM token**, not with a Home Assistant user.
- The streamers report their status to a webhook created by the integration and are polled every 60 s.
- LG developer mode tokens are stored in the config entry only – not in `www/`, the compose file, logs or diagnostics.
  Home Assistant keeps config entries unencrypted in `.storage/`, so protect your backups.

## Development

```sh
pip install -r requirements_test.txt
pytest
```

## License

GPL-3.0 – see [LICENSE](LICENSE). The Moonlight part will be based on [moonlight-tv](https://github.com/mariotaku/moonlight-tv) (GPL-3.0).
Logo: own work, see `docs/images/icon.svg`.

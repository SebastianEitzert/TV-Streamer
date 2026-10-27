<p align="center"><img src="https://raw.githubusercontent.com/SebastianEitzert/TV-Streamer/main/docs/images/logo.png" alt="TV Streamer" width="420"></p>

# TV Streamer for Home Assistant

🇩🇪 [Deutsche Fassung](README.de.md)

If TV Streamer is useful to you, you can support its development:

<p align="center"><a href="https://buymeacoffee.com/SebastianEitzert"><img src="https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=&slug=SebastianEitzert&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff" alt="Buy me a coffee" height="45"></a></p>

Show Home Assistant dashboards on TVs, served from a small VM: one Chromium per TV, rendered off-screen and sent to the TV as
**MSE** video, **WebRTC** or via **Sunshine/Moonlight**. Mouse, TV remote and touch work on the dashboard as if a PC were connected.

| Part | Status |
|---|---|
| `custom_components/tv_streamer` – Home Assistant integration (setup in the UI, devices, sensors, remote key events, LG developer mode renewal, config endpoint for the VM), installable with HACS | **0.4** |
| `vm/proxmox-vm.sh` – creates the VM on Proxmox VE | **0.1** |
| `custom_components/tv_streamer/streamer` – streamer image (Docker: `server.py`, Chromium, encoders, Sunshine), delivered to the VM by the integration | **0.4** |
| Floor plan Lovelace card (HACS) | planned |
| `moonlight/` – patched Moonlight for LG webOS (`.ipk`, GPL-3.0) | **testing** |

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

#### Basic Proxmox settings (once, after installing)

- **Package repositories:** without a subscription switch to the *no-subscription* repository
  (*node → Updates → Repositories*: disable `enterprise`, add `No-Subscription`), then *Updates → Refresh → Upgrade*.
- **Fixed IP address for the Proxmox host** – set during installation; change later in *node → System → Network*.
- **Network bridge:** the installer creates `vmbr0` on your LAN port. The streamer VM must be on the same network as the
  TVs (no NAT, no VLAN in between unless you route it) – Moonlight and Wake on LAN need the LAN.
- **Storage:** `local-lvm` (or ZFS) for VM disks. The VM script adds the content type *Snippets* to the storage `local`
  automatically; doing it by hand: *Datacenter → Storage → local → Edit → Content: Snippets*.
- **Time zone:** *node → System → Time* (the VM takes its time zone from the integration settings).
- **Backups (optional):** *Datacenter → Backup → Add*. The streamer VM can be left out – the integration recreates its
  configuration, only logins and Moonlight pairings live in the VM (Docker volumes).
- **Home Assistant on the same host:** give Home Assistant priority – the script sets the streamer's CPU weight to 50
  (`cpuunits`, Home Assistant VM has the default 100), so HA always wins when the CPU is busy.

### 2. Create the streamer VM

In the Proxmox web UI open **your node → Shell** and run:

```sh
curl -fsSLo /root/tv-streamer-vm.sh https://raw.githubusercontent.com/SebastianEitzert/TV-Streamer/main/vm/proxmox-vm.sh
bash /root/tv-streamer-vm.sh
```

The script asks for the VM ID, IP address (or DHCP), bridge, storage, cores, RAM and a password for the user `tv`. It
downloads the Debian 13 cloud image (checksum verified), creates the VM and installs Docker on first boot (about 5 minutes).

Give the VM a **fixed IP address** (in the script or as a DHCP reservation in your router) – TVs and Moonlight connect to it.

#### What the script sets – or how to create the VM by hand

| Setting | Value | Note |
|---|---|---|
| OS image | Debian 13 *genericcloud* (`qcow2`, imported as disk) | small, cloud-init ready |
| Machine / BIOS | `q35`, SeaBIOS | |
| CPU | type **host**, 4 cores (2 TVs: **8**), CPU units **50** | `host` gives the software encoder all CPU features (AVX2) |
| Memory | 4096 MB, ballooning min. 2048 (2 TVs: **6144 MB**) | |
| Disk | 20 GB, VirtIO SCSI single, *discard* + *SSD emulation* + *IO thread* | |
| Network | VirtIO on `vmbr0`, **fixed IP** | |
| Display / console | serial console (`serial0`, display *Serial terminal 0*) | console in the Proxmox UI via xterm.js |
| QEMU guest agent | **on** | needed for `qm guest exec` and `qm guest passwd` |
| Start at boot | **on** | |
| Cloud-init | user `tv` + password, IP config, vendor snippet installing Docker | |

By hand: create the VM with these values (*Create VM*, or `qm create` / `qm importdisk` for the cloud image), add a
*CloudInit drive*, set user, password and IP in the *Cloud-Init* tab, start it and install Docker
(`curl -fsSL https://get.docker.com | sh`) and `qemu-guest-agent`.

**Change CPU or RAM later:** `qm set <VMID> --cores 8 --memory 6144`, then **stop and start** the VM from Proxmox
(`qm reboot <VMID>`) – a reboot inside the VM does not apply new hardware.

**Forgot the VM password?** On the Proxmox host: `qm guest passwd <VMID> tv`.

**GPU:** the streamer encodes in software (x264) – no GPU passthrough needed. One TV at 1440p uses roughly 1–1.5 cores.
Sharing an Intel iGPU between Home Assistant OS and the VM (SR-IOV) is not supported by every setup; it is not required.

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

   **Which video path?** All three show the same Chromium page from the VM; they differ in how the picture gets to the TV:

   | | MSE | WebRTC | Moonlight |
   |---|---|---|---|
   | On the TV | web browser (any TV) | web browser with WebRTC | Moonlight app (LG: developer mode) |
   | Delay | noticeable – the TV browser buffers about 0.5 s | clearly less than MSE (no buffer) | lowest – made for game streaming, the fastest reaction in our tests |
   | Picture | sharp, TV hardware decoder | sharp | sharp, TV hardware decoder |
   | Sound | yes | yes | yes |
   | Remote | browser pointer and keys | browser pointer and keys | Magic Remote pointer; with the [TV Streamer build](moonlight/README.md) also colour and play/pause keys |
   | Setup | just open the address | just open the address | developer mode, install the app, pair once, renew the session (automatic) |
   | Sensors in HA | latency, frame rate, data rate | latency, frame rate, data rate | – (Sunshine reports none) |
   | Limits | delay when clicking and pointing | webOS 4 (e.g. UK7550): 4:3, freezes or stays black | LG developer mode needed; no measurement sensors |

   Rule of thumb: **Moonlight** where the TV can run it (LG webOS), **WebRTC** for other TVs whose browser handles it,
   **MSE** as the fallback that runs everywhere. The VM encodes in software (no graphics card), so 1080p/1440p – 4K is too much.
2. **Add extra tab** (optional; later *Edit extra tab* changes address and options) – e.g. a Loxone or router web interface: name, address (`192.168.1.160` is enough,
   `http://` is added), *remember login*, *never reload*.
3. **General settings** – start view (the dashboard the TVs open; a path like `/dashboard-tv/home` is enough), rest time,
   *back to start view after*, raster threads, **green key** (first extra tab, a chosen tab or nothing), audio, time zone.

Every step is saved as soon as you confirm it – there is no separate save button.

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

**Browser (MSE / WebRTC):** open `http://<VM-IP>:8091/` in the TV's web browser (second streamer `:8092`, …).
*Show on TV* opens it for you.

**Moonlight (LG webOS, recommended):** Moonlight is not in the LG Content Store. It is installed as a developer app,
so the TV needs LG's **developer mode**. This takes about 30 minutes once.

#### 9.1 Developer mode on the TV
1. Create a free LG developer account at <https://webostv.developer.lge.com> (*Sign In → Create Account*).
2. On the TV open the **LG Content Store**, search for **Developer Mode** and install it.
3. Open *Developer Mode*, sign in with the developer account and switch **Dev Mode Status** on. The TV restarts.
4. Open *Developer Mode* again and switch **Key Server** on. The app now shows the TV's **IP address** and a
   **passphrase** – you need both in the next step. The session counter (about 1000 hours) starts here; the integration
   renews it every day once you entered the token (9.4).

#### 9.2 webOS Dev Manager on your PC
1. Install the [webOS Dev Manager](https://github.com/webosbrew/dev-manager-desktop/releases) (Windows, macOS, Linux).
2. *Add device*: enter the TV's IP address and the passphrase from the Developer Mode app. The Dev Manager fetches the
   SSH key from the TV's key server and connects.

#### 9.3 Install Moonlight
1. Download the latest `com.limelight.webos_<version>_arm.ipk` from the
   [Moonlight TV releases](https://github.com/mariotaku/moonlight-tv/releases)
   – or, recommended, the **TV Streamer build of Moonlight**:
   [**moonlight-tvs_arm.ipk** (latest)](https://github.com/SebastianEitzert/TV-Streamer/releases/latest/download/moonlight-tvs_arm.ipk)
   – attached to every [release](https://github.com/SebastianEitzert/TV-Streamer/releases) ([what it changes](moonlight/README.md)): it passes the blue, green and
   play/pause keys to the dashboard and brings the pointer back right after the arrow keys. Each key also shows up in
   Home Assistant as the event entity `event.tv_streamer_<streamer>_remote` (event types `blue`, `green`,
   `play`, `pause`, `stop`) – usable as a trigger in automations – and on the page itself as the event
   `tv-streamer-key` (e.g. for the floor plan card [Floorplan Lite](https://github.com/SebastianEitzert/HA-FloorplanLite):
   play/pause with the pointer over a room = its music).
2. In the Dev Manager open **Apps → Install** and select the `.ipk`. Moonlight appears in the TV's app list.
3. Open the Sunshine web UI of the streamer on your PC: `https://<VM-IP>:47990` (second streamer `:48090`, …). Accept the
   certificate warning (Sunshine uses its own certificate) and create a Sunshine user name and password.
4. On the TV open Moonlight → **+** (add host) → enter `<VM-IP>` (second streamer `<VM-IP>:48089`, …). Moonlight
   does not find the streamer automatically because it runs in Docker.
5. Moonlight shows a **4-digit PIN**. In the Sunshine web UI open **PIN**, enter the PIN and a name for the TV, send.
6. In Moonlight open the host and start **Home Assistant** once (and every extra tab, e.g. **Loxone**). From then on
   *Show on TV* starts these apps directly.

**Moonlight settings** (Moonlight → settings, once per TV):

| Setting | Value | Why |
|---|---|---|
| Resolution | same as the streamer: webOS 4 (e.g. UK7550) **1080p**, webOS 5+ (e.g. 86UN85) **1440p** | webOS 4 shows a green picture above 1080p |
| Frame rate | **60 fps** (30 if it stutters) | |
| Bit rate | 10–16 Mbit/s | |
| **Mute host PC while streaming** | **off** | otherwise there is **no sound** – Sunshine mutes the streamer's audio sink |
| Decoder | default | "SMP" has no sound and much more delay |
| Mouse | **absolute** (default) | the Magic Remote pointer maps 1:1 to the dashboard |

#### 9.4 Session token for the automatic renewal
LG ends the developer mode after about 1000 hours and removes Moonlight, unless the session is renewed.

1. Switch the TV **on** (the Dev Manager reads the token from the TV over SSH, so the TV must be on and connected).
   In the Dev Manager select the TV → **Info**. The page shows the remaining time and the buttons *Renew session* and
   **Renew automatically…**.
2. *Renew automatically…* shows the renewal URL
   `https://developer.lge.com/secure/ResetDevModeSession.dev?sessionToken=…` – copy it (the whole URL or just the token).
3. In Home Assistant: *TV Streamer → Configure → Edit streamer → LG developer mode session token*, paste, save.
   The integration checks the token right away.

Without the Dev Manager you can read the token on the TV via SSH: `cat /var/luna/preferences/devmode_enabled`.
The daily renewal itself does not need the TV: Home Assistant calls LG's server directly, so it also works while the TV is off.
The token changes when you switch the developer mode off and on again – the integration then raises a **repair** that
asks for the new one.

Keep the TV's firmware in mind: a firmware update can reset the developer mode; check the *Developer mode expires*
sensor after updates.

### 10. Check

Each streamer is a device with sensors (state, viewers; with MSE/WebRTC also latency, frame rate, data rate), *reachable*, *Moonlight stream*
(any Moonlight device, also while in the background) and **On TV** (the streamer's own TV shows it in front – use this one
in automations) binary sensors, and buttons (start view, reload, back, show tab, renew developer mode). If LG rejects a renewal, a
**repair** appears that asks for a new token.

Moving an existing hand-made installation: see [docs/migration.md](docs/migration.md).

## Troubleshooting

| Problem | Cause / fix |
|---|---|
| Moonlight: picture but **no sound** | Moonlight setting *Mute host PC while streaming* must be **off**. |
| Moonlight: green or black picture, or only a still image | Resolution too high for the TV (webOS 4: max. 1080p). Set the same size in Moonlight and in the streamer settings. |
| Moonlight does not find the host | Add it by hand: `<VM-IP>` (second streamer `<VM-IP>:48089`). Docker hides the discovery. |
| Sunshine web UI says *forbidden* / CSRF error | Open it with the VM's IP address as configured in the integration (`https://<VM-IP>:47990`), not with a host name. |
| Sunshine does not start (`docker logs tv-<name>` shows `… .so: cannot open shared object file`) | A library the Sunshine AppImage expects is missing. The image installs all known ones (e.g. `libpipewire-0.3-0t64`); if a new Sunshine version needs more, add the package in `streamer/Dockerfile` and open an issue. |
| Developer mode expired, Moonlight is gone | Switch the developer mode on again (9.1), reinstall Moonlight (9.3), enter the **new** token (9.4) – the repair in Home Assistant asks for it. |
| VM does not pick up changes | On the VM: `journalctl -u tv-streamer-config -n 50`. "token rejected" → run the command from *VM setup* again. |
| *Show on TV* does nothing while the TV is off | Set *Switch on with (Wake on LAN)* in the streamer settings; Wake on LAN must be enabled on the TV (e.g. *Settings → General → Mobile TV On*; the menu name differs by model). |

## How it works

- The integration generates the `docker-compose.yml` and serves it at `/api/tv_streamer/<entry_id>/docker-compose.yml`.
  The VM authenticates with its own **VM token**, not with a Home Assistant user.
- The streamers report their status to a webhook created by the integration and are polled every 60 s.
- LG developer mode tokens are stored in the config entry only – not in `www/`, the compose file, logs or diagnostics.
  Home Assistant keeps config entries unencrypted in `.storage/`, so protect your backups.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). Changes: [CHANGELOG.md](CHANGELOG.md). Security: [SECURITY.md](SECURITY.md).
Third-party software: [THIRD_PARTY.md](THIRD_PARTY.md).

```sh
pip install -r requirements_test.txt
pytest
```

## License

GPL-3.0 – see [LICENSE](LICENSE). The Moonlight part will be based on [moonlight-tv](https://github.com/mariotaku/moonlight-tv) (GPL-3.0).
Logo: own work, see `docs/images/icon.svg`.

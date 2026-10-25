# Moving an existing streamer VM to the integration

🇩🇪 [Deutsch](migration.de.md)

For installations that were set up with `bootstrap.sh` from Home Assistant's `www/tv-streamer` (hand-written
`docker-compose.yml`, template sensors on a webhook, `shell_command` for the LG renewal).

## 1. Keep containers, volumes and Moonlight pairing

Container and volume names come from the streamer name, ports from the order in which the streamers are added.
Add the streamers **with their existing service names and in the existing port order**:

| Existing | Add as | Result |
|---|---|---|
| service `tv1`, port 8091, Sunshine 47989 | 1st streamer, name `tv1` | `tv-tv1`, volume `tv-tv1`, 8091, 47989 |
| service `tv2`, port 8092, Sunshine 48089 | 2nd streamer, name `tv2` | `tv-tv2`, volume `tv-tv2`, 8092, 48089 |

Then browser logins, Sunshine pairing and Moonlight host entries stay valid. Copy width, height, zoom and bit rate from the old
compose file – the TV type only fills in defaults. In *General settings*, set *Docker image* to the old `image:` value.

## 2. Stop the old mechanism from overwriting the compose file

The old `update.sh` reloads `docker-compose.yml` from `www/tv-streamer` whenever `VERSION` changes there. Before installing the
new timer, remove `docker-compose.yml` from the file list in `www/tv-streamer/bootstrap.sh` (the loop `for f in server.py …`).
`server.py`, `client.html` etc. keep coming from there until the VM image is part of this repository.

## 3. Install on the VM

Run the command from *Options → VM setup* as root on the VM. Check with `journalctl -u tv-streamer-config` and `docker compose ps`
in `/opt/tv-streamer`. The previous file is kept as `docker-compose.yml.bak`.

## 4. Remove the old parts in Home Assistant

The streamers now report to the integration's own webhook. Once the new entities show values:

- remove the template sensors on the old webhook (`configuration.yaml`, `template:` with `trigger: webhook`) and update
  dashboards / automations that use them,
- remove the automation that renewed the LG developer mode and its `shell_command` entries (they contain the token),
- check automations that were triggered by the old webhook – they no longer receive reports.

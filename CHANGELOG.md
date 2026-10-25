# Changelog

All notable changes to this project. Versions follow the `version` in `custom_components/tv_streamer/manifest.json`.

## 0.4.0 – unreleased
- `moonlight/`: patched Moonlight for webOS (blue/green/play-pause/stop to the host, pointer back after arrow keys),
  built by a GitHub Action from the upstream release v1.6.37.
- Streamer: blue = Home Assistant, green = first extra tab, every remote key also fires the Home Assistant event
  `tv_streamer_key`.
- Jarvis-style automations can use the "Show on TV" buttons instead of scripts.

## 0.3.1
- "Show on TV": no fixed 8 s pause after switching the TV on any more. The app start is repeated until webOS reports
  the app in the foreground (at most 20 s).

## 0.3.0
- The streamer image (Dockerfile, `server.py`, `client.html`, `clock.html`) ships with the integration. The VM fetches it
  together with its configuration, verifies SHA-256 checksums and rebuilds automatically after updates.
- One Moonlight app per extra tab.
- CI builds the streamer image and smoke-tests it.

## 0.2.0
- Buttons "Show on TV" and "Show *tab* on TV": wake the TV (Wake on LAN button, script or switch) and start Moonlight
  with the right Sunshine host and app, or open the TV browser.

## 0.1.1
- Logo, `vm/proxmox-vm.sh`, step-by-step setup guide.

## 0.1.0
- First version: config and options flow, devices, sensors, buttons, LG developer mode renewal with repair flow,
  token-protected config endpoint for the VM.

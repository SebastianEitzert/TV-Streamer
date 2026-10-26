# Changelog

All notable changes to this project. Versions follow the `version` in `custom_components/tv_streamer/manifest.json`.

## 0.4.5 – 2026-10-26
- The remote keys from the TV Streamer build of Moonlight (blue, green, play, stop, pause) also reach the page itself as
  a `tv-streamer-key` event, e.g. for the floor plan card Floorplan Lite: play / pause with the pointer over a room
  start / pause its music. The Home Assistant event entity stays as it is.

## 0.4.4 – 2026-10-26
- New binary sensor **On TV** per streamer: on only when the streamer's own TV shows it in front – Moonlight: the TV has
  the Moonlight app in front and a stream runs (Moonlight keeps streams open in the background, and any paired device
  can stream); browser: the TV has its web browser in front and a viewer has the TV's IP address (from the LG webOS
  integration). *Viewers* and *Moonlight stream* still count every device.

## 0.4.3 – 2026-10-26
- General settings: **green key** – first extra tab (default, as before), a chosen tab or nothing (only the Home
  Assistant event). Streamer 2026-10-26.42.
- README: comparison of the video paths MSE, WebRTC and Moonlight (delay, setup, limits).

## 0.4.2 – 2026-10-26
- Moonlight streamers no longer get the sensors latency, frame rate and data rate (they are measured by the receiving
  page in the TV browser, MSE/WebRTC only); existing ones are removed.
- Streamer settings: for LG TVs the TV must be the entity of the LG webOS integration. The Music Assistant speaker of the
  same TV has a similar name but cannot start apps – "Show on TV" then only switched the tab and nothing seemed to happen.

## 0.4.1 – 2026-10-25
- "Show on TV" starts Moonlight also when it still holds a stream in the background while another app (e.g. YouTube)
  is in front – before, the button only switched the tab and the TV stayed on the other app.
- Remote keys: separate events `play` and `pause` (the LG remote has two keys) instead of `play_pause`. Moonlight build:
  Pause is sent as F17; streamer 2026-10-25.41 maps F13–F17.
- Removed two keymap dump files that had slipped into 0.4.0.

## 0.4.0 – 2026-10-25
- `moonlight/`: patched Moonlight for webOS (blue/green/play-pause/stop to the host, pointer back after arrow keys),
  built by a GitHub Action from the upstream release v1.6.37.
- Streamer: blue = Home Assistant, green = first extra tab, every remote key also fires the Home Assistant event
  `tv_streamer_key`.
- Event entity "Remote" per streamer (`event.tv_streamer_<streamer>_remote`) with the event types `blue`, `green`,
  `play`, `pause` and `stop` – a clean automation trigger for the remote keys.
- Options: every step is saved right away, the "Save" menu entry is gone.
- Addresses without `http://` are accepted (`192.168.1.160`), the start view also as a bare path (`/dashboard-tv/home`).
- Moonlight build: Play/Pause and Stop are sent as F15/F16 (Sunshine on Linux drops media keys); the app is called
  "Moonlight TVS" so the patched build is easy to recognise. The streamer recognises the keys by key code.
- Options: new "Edit extra tab" (address, remember login, never reload); tab names show capitalised in button names.
- VM update script: also switches off the old `tv-streamer-update.timer` when it is only running (not enabled) – it kept
  copying old streamer files over the new ones. The script now keeps itself up to date.
- Streamer 2026-10-25.39: F13–F16 get key codes in the virtual screen. Sunshine passes keys on via XTest and silently
  dropped keys without a key code – that is why blue, green and play/pause never arrived. Xvfb runs with `-noreset`
  so the mapping survives a browser restart.
- Streamer 2026-10-25.40: the Back key in Moonlight uses the same guarded way back as the Back button – never past
  the start view, so it no longer lands on the blank resting page.
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

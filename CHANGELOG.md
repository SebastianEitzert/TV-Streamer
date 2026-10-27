# Changelog

All notable changes to this project. Versions follow the `version` in `custom_components/tv_streamer/manifest.json`.

## 0.4.9 – 2026-10-27
- Moonlight (test 2): the Magic Remote sensor is asked to stay awake (`sleep: false`) – in test 1 its data paused for as long as webOS' pointer after an arrow key (1.0–1.7 s).
- README: Kiosk Mode and the floor plan card (Floorplan Lite) on the TV, with a pointer to the location (Bermuda) section of Floorplan Lite.

## 0.4.8 – 2026-10-27
- The Moonlight IPK is attached to every release (also as `moonlight-tvs_arm.ipk`); the README links the latest one.
- Moonlight (test): after an arrow key the patched Moonlight reads where the Magic Remote points straight from webOS' remote service (`com.webos.service.mrcu`) and moves the host's mouse with it until real pointer motion comes back – webOS itself sends none for up to 3 s. New measurement markers F21 (sensor data came), F22 (service not callable), F23 (refused) in `pointer_measurement` (`sensor`, `sensor_fehler`, `sensor_abgelehnt`).
- Back key on the TV: the address of a Floorplan Lite card view (`#plan=…&floor=…`) is no pop-up any more – Back from a building leads to the site instead of jumping out of the dashboard (white page).

## 0.4.7 – 2026-10-27
- Every page knows its TV: `window.__tvStreamer = {name}` (the streamer's name) – the floor plan card Floorplan Lite uses
  it to start each TV in its own room.
- Back on the TV: an address like `#plan=house&floor=og` (a view of the floor plan card) is no pop-up any more, Back goes
  one view back there (from the building to the site). Pop-ups stay `#name`.

## 0.4.6 – 2026-10-26
- Measurement for the frozen pointer after the arrow keys: the TV Streamer build of Moonlight marks when webOS hides
  and shows the Magic Remote pointer and when the remote moves first after an arrow key (keys F18–F20, never seen by
  the page). The streamer measures the times per arrow key and the state sensor shows the last 20 as attribute
  `pointer_measurement` (ms from the key press: `hide`, `show`, `tv_bew` = motion at the TV, `host_bew` = pointer
  moved in the browser, `los` = key released, `vorher` = ms since the last motion before the key).
- Moonlight build: asks for the pointer again after every arrow key (at once and after 30–350 ms).

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

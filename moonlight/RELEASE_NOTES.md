Patched build of [Moonlight TV](https://github.com/mariotaku/moonlight-tv) for LG webOS, made for TV Streamer.
Source: the upstream release named in `moonlight/UPSTREAM` plus the patches in `moonlight/patches/` (GPL-3.0).

Changes against upstream:
- **Blue** and **green** keys are sent to the host (as F13 / F14) – TV Streamer shows Home Assistant / the first extra tab.
- **Play**, **Stop** and **Pause** are sent as F15 / F16 / F17 (Sunshine on Linux drops media keys) – TV Streamer fires
  the Home Assistant event `tv_streamer_key`.
- The app is called **Moonlight TVS** in the TV's app list, so you can see the patched build is installed.
- **Yellow** is always a right click while streaming (upstream only after a click in Moonlight's own UI – a stream
  started from Home Assistant or with OK made it a menu key, which Sunshine on Linux drops).
- The **pointer** is not switched off by Moonlight on the arrow keys while streaming (upstream does that on every
  arrow key) and is asked back at once. A short pause remains: the Magic Remote itself sends no motion for about
  1–1.7 s after any key press (measured, see below) – no app can change that.
- **Pause** is sent as F17 (TV Streamer event `pause`), **Play** as F15 (event `play`).

Install over the official Moonlight with the webOS Dev Manager (same app id – pairings and settings stay), then switch the
TV off at the mains once so no old Moonlight keeps running in the background.

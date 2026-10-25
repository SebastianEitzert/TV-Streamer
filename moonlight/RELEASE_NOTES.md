Patched build of [Moonlight TV](https://github.com/mariotaku/moonlight-tv) for LG webOS, made for TV Streamer.
Source: the upstream release named in `moonlight/UPSTREAM` plus the patches in `moonlight/patches/` (GPL-3.0).

Changes against upstream:
- **Blue** and **green** keys are sent to the host (as F13 / F14) – TV Streamer shows Home Assistant / the first extra tab.
- **Play/Pause** and **Stop** are sent as media keys – TV Streamer fires the Home Assistant event `tv_streamer_key`.
- The **pointer** comes back right after using the arrow keys, without shaking the Magic Remote.

Install over the official Moonlight with the webOS Dev Manager (same app id – pairings and settings stay).

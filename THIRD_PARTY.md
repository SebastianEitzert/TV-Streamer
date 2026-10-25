# Third-party software

The streamer image (`custom_components/tv_streamer/streamer/Dockerfile`) downloads and runs the following software. It is
not part of this repository; each keeps its own license.

| Software | Use | License |
|---|---|---|
| [Debian](https://www.debian.org/) (`debian:trixie-slim`) with Chromium, Xvfb, FFmpeg, PulseAudio, xdotool | base system, browser, virtual display, encoders | various free licenses (see Debian packages) |
| [go2rtc](https://github.com/AlexxIT/go2rtc) | WebRTC | MIT |
| [PyAV](https://github.com/PyAV-Org/PyAV) | own H.264 encoder for WebRTC | BSD-3-Clause (bundles FFmpeg, LGPL/GPL) |
| [Sunshine](https://github.com/LizardByte/Sunshine) | Moonlight host | GPL-3.0 |
| [Moonlight TV](https://github.com/mariotaku/moonlight-tv) | app on the TV (installed by you) | GPL-3.0 |

"Home Assistant", "LG", "webOS", "Moonlight", "Sunshine" and "Proxmox" are names of their respective owners. This
project is not affiliated with any of them.

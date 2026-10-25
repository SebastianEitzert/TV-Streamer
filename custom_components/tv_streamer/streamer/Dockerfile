# TV Streamer – KI generiert (Claude, 21.10.2026; 23.10.: Debian 13, Schriften optional, init über Docker,
# Chromium-Richtlinie ohne Passwort-Manager und ohne Abfragen – Browser-Fenster wie „Speichern?“ sind fernbedient nicht klickbar)
# Aktueller Chromium in einem virtuellen Bildschirm, Bild als H.264 an den Fernseher, Bedienung zurück.
# 23.10. (.12): go2rtc für den Bildweg WebRTC (feste Fassung mit Prüfsumme – stimmt sie nicht, bricht der Bau ab
# und die laufenden Container bleiben unverändert).
# 24.10. (.30): PulseAudio für den Ton (Senke im Container, Chromium spielt dorthin; Opus per WebRTC, AAC im MSE-Strom).
FROM debian:trixie-slim
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends chromium xvfb xdotool ffmpeg pulseaudio python3 python3-aiohttp ca-certificates tzdata && for p in fonts-noto-core fonts-noto-color-emoji fonts-roboto fonts-dejavu-core; do apt-get install -y --no-install-recommends $p || echo "Schrift $p nicht gefunden - weiter ohne"; done && rm -rf /var/lib/apt/lists/* && useradd -m -u 1000 tv && mkdir -p /data && chown tv:tv /data
RUN mkdir -p /etc/chromium/policies/managed && printf '%s' '{"PasswordManagerEnabled": false, "AutofillAddressEnabled": false, "AutofillCreditCardEnabled": false, "TranslateEnabled": false, "BrowserSignin": 0, "SyncDisabled": true, "DefaultNotificationsSetting": 2, "DefaultGeolocationSetting": 2, "AudioCaptureAllowed": false, "VideoCaptureAllowed": false, "PromotionalTabsEnabled": false, "DefaultBrowserSettingEnabled": false}' > /etc/chromium/policies/managed/tv-streamer.json
ARG GO2RTC_VERSION=1.9.14
ARG GO2RTC_SHA256=32d616af226bd731678ffde328b94cfb94e30339bfefc469cfb76323144615a6
RUN python3 -c "import hashlib, sys, urllib.request; d = urllib.request.urlopen('https://github.com/AlexxIT/go2rtc/releases/download/v${GO2RTC_VERSION}/go2rtc_linux_amd64', timeout=180).read(); h = hashlib.sha256(d).hexdigest(); h == '${GO2RTC_SHA256}' or sys.exit('go2rtc: Pruefsumme stimmt nicht: ' + h); open('/usr/local/bin/go2rtc', 'wb').write(d)" && chmod 755 /usr/local/bin/go2rtc && /usr/local/bin/go2rtc -version
# 23.10. (.15): PyAV (feste Fassung mit Prüfsumme, bringt sein eigenes FFmpeg mit x11grab und libx264 mit) für den
# eigenen WebRTC-Kodierer – Schlüsselbild nur auf Abruf. Klappt die Installation nicht, läuft WebRTC über go2rtc exec.
ARG AV_VERSION=17.1.0
ARG AV_SHA256=f9a65d1f48b818323fb411e80358f89d77dec340b01d27c6b2dfbb9cbf4b779f
RUN { apt-get update && apt-get install -y --no-install-recommends python3-pip && printf 'av==%s --hash=sha256:%s\n' "${AV_VERSION}" "${AV_SHA256}" > /tmp/av.txt && pip install --break-system-packages --no-cache-dir --no-deps --only-binary=:all: --require-hashes -r /tmp/av.txt && python3 -c "import av; assert 'x11grab' in av.formats_available and 'libx264' in av.codecs_available; print('PyAV', av.__version__)"; } || echo "PyAV fehlt - WebRTC ueber go2rtc exec"; rm -rf /var/lib/apt/lists/* /tmp/av.txt
# 24.10. (.37c): Bibliotheken, die das Sunshine-AppImage beim System erwartet (nicht mitgeliefert) – ohne libpipewire startete
# Sunshine nicht („libpipewire-0.3.so.0: cannot open shared object file“; .37d: dann libgpg-error.so.0 – jetzt alle 27 Fremd-Bibliotheken).
RUN apt-get update && for p in libpipewire-0.3-0t64 libegl1 libgl1 libglx0 libopengl0 libice6 libsm6 libx11-xcb1 libwayland-client0 libgbm1 libdrm2 libfontconfig1 libfreetype6 libharfbuzz0b libgmp10 libgpg-error0 libcom-err2 zlib1g libstdc++6 libgcc-s1 libx11-6 libxcb1; do apt-get install -y --no-install-recommends $p || echo "Paket $p nicht gefunden - weiter"; done; rm -rf /var/lib/apt/lists/*
# 24.10. (.37): Sunshine (LizardByte) als Moonlight-Host – feste Fassung mit Prüfsumme, AppImage entpackt (kein FUSE nötig).
# Startet nur mit MOONLIGHT=1 (server.py). Klappt das Entpacken nicht, baut das Image trotzdem und der Streamer läuft ohne
# Moonlight. libXtst (XTest-Eingabe ohne /dev/uinput) ist über xdotool schon da.
ARG SUNSHINE_VERSION=2026.914.233613
ARG SUNSHINE_SHA256=6f80297a853bcf8cda114ff131b5c0a8c9a4d96a2a9c3dee1f04c39c54206846
RUN { python3 -c "import hashlib, sys, urllib.request; d = urllib.request.urlopen('https://github.com/LizardByte/Sunshine/releases/download/v${SUNSHINE_VERSION}/Sunshine_${SUNSHINE_VERSION}_x86_64.AppImage', timeout=300).read(); h = hashlib.sha256(d).hexdigest(); h == '${SUNSHINE_SHA256}' or sys.exit('Sunshine: Pruefsumme stimmt nicht: ' + h); open('/tmp/sun.AppImage', 'wb').write(d)" && cd /opt && chmod +x /tmp/sun.AppImage && /tmp/sun.AppImage --appimage-extract >/dev/null && mv squashfs-root /opt/sunshine && { ldd /opt/sunshine/usr/bin/sunshine | grep 'not found' || true; } && /opt/sunshine/usr/bin/sunshine --version && rm -f /tmp/sun.AppImage && chown -R tv:tv /opt/sunshine; } || echo "Sunshine fehlt im Image - Moonlight nicht verfuegbar"
COPY server.py client.html clock.html /app/
USER tv
VOLUME ["/data"]
EXPOSE 8090 8555/udp 8555/tcp
# .37 (nur mit MOONLIGHT=1 belegt): Moonlight/Sunshine
EXPOSE 47984-47990/tcp 48010/tcp 47998-48000/udp
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/api/status', timeout=4)" || exit 1
CMD ["python3", "/app/server.py"]

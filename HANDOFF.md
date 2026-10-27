# HANDOFF – TV-Streamer

Stand: 2026-10-27 (abends). Diese Datei wird bei jeder Änderung mitgepflegt. Keine Zugangsdaten hier ablegen.

## 1. Stand

| | |
|---|---|
| Letztes Release | **0.5.0**, Tag `v0.5.0` (GitHub-Release mit `tv_streamer.zip`) |
| Streamer-Fassung im Paket | `FASSUNG = "2026-10-28.48"` (`custom_components/tv_streamer/streamer/server.py`) |
| In Home Assistant eingespielt | Integration 0.4.9, Fassung `2026-10-27.47`. 0.5.0 ist veröffentlicht, aber noch nicht installiert. |
| Dateien unter `www/` | keine |
| Moonlight-IPK | Am Release jeder Version, neueste: https://github.com/SebastianEitzert/TV-Streamer/releases/latest/download/moonlight-tvs_arm.ipk (App „Moonlight TVS“, moonlight-tv v1.6.37 + Patch). Auf den Fernsehern: Test-Build 0.4.9, 0.5.0-IPK noch zu installieren. |
| Branch | nur `main` |

## 2. Aktueller Auftrag

Für die Grundstücks-Karte (Floorplan Lite) wichtig:
- **Erledigt:** `window.__tvStreamer = {name}` für Gerätenamen (0.4.7), Pop-up-Erkennung ignoriert `#plan=…` (Seite: .45; Zurück-Logik im Streamer: .46, 0.4.8).
- **Abgeschlossen (nicht lösbar):** Mauszeiger pausiert nach Pfeiltasten 1–1,7 s. Messungen 26.–27.10.: die Magic Remote selbst sendet nach einem Tastendruck keine Bewegung – weder an den webOS-Zeiger noch an den Sensordienst `com.webos.service.mrcu` (auch nicht mit `sleep:false`). Versuche (Zeiger nicht abschalten, mehrfach wieder einschalten, Sensor-Abo mit eigener Mausbewegung) wurden in 0.5.0 bis auf „nicht abschalten + einmal wieder einschalten“ entfernt, ebenso alle Messmarken (F18–F23) und `pointer_measurement`. Nicht noch einmal versuchen.
- **Halb fertig:** nichts.

## 3. Nicht committete / nicht gepushte Änderungen

Keine. Alles ist auf `main` gepusht.

## 4. Aufbau

```
custom_components/tv_streamer/
  __init__.py, config_flow.py   Einrichtung je Streamer-VM (Config Flow + Optionen), Webhook für Meldungen der VM
  api.py                        HTTP-Endpunkte für die VM: /api/tv_streamer/<entry>/{version,compose,update.sh,files,file/<name>}
  compose.py                    erzeugt docker-compose.yml für die VM
  streamer_files.py             liefert die Streamer-Dateien (streamer/) samt sha256-Manifest
  streamer/                     Image der VM: Dockerfile, server.py (Chromium/CDP, Moonlight-Tasten, Messung), client.html, clock.html
  vm_update.sh                  Skript auf der VM (systemd-Timer alle 5 min)
  coordinator.py, sensor.py, binary_sensor.py, button.py, event.py, lg.py, show.py   Entitäten, LG-TV-Steuerung
moonlight/                      UPSTREAM (moonlight-tv-Version), patches/, RELEASE_NOTES.md
vm/proxmox-vm.sh                VM in Proxmox anlegen
tests/                          pytest
```

- **Kein Bundling.** Prüfung: `python3 -c "import ast; ast.parse(open('…/server.py').read())"`, Tests `pytest -q` (Action `validate.yml`).
- **Release:** Version in `manifest.json` erhöhen, `CHANGELOG.md` `## <version> – <Datum>`, auf `main` pushen → `release.yml` erstellt Tag, Release und `tv_streamer.zip`. Bei geänderten Streamer-Dateien `FASSUNG` in `server.py` hochzählen.
- **Moonlight-IPK:** Jeder Push auf `main` startet `moonlight-webos.yml`; das IPK hängt danach am Release der aktuellen Version, auch als `moonlight-tvs_arm.ipk` (Link für Nutzer: https://github.com/SebastianEitzert/TV-Streamer/releases/latest/download/moonlight-tvs_arm.ipk). Ablauf: klont moonlight-tv (Tag aus `moonlight/UPSTREAM`), wendet `moonlight/patches/*.patch` mit `git apply` an, baut mit dem webOS-NDK/Homebrew-Toolchain und legt das IPK als Artefakt `moonlight-webos-tvstreamer` ab. Installation mit dem webOS Dev Manager über die offizielle App (gleiche App-ID), danach TV einmal vom Netz trennen.
- **Commits:** Autor `SebastianEitzert <35038662+SebastianEitzert@users.noreply.github.com>`.

## 5. Verbindung Integration – Streamer-VM – HA

- **Config Flow:** je VM ein Eintrag (Adresse der VM, HA-URL, Start-URL, Reiter/Links, Fernseher-Typ und -Adresse, Bild/Ton). Optionen zeigen den Einrichtungsbefehl für die VM.
- **Token:** die Integration erzeugt beim Einrichten einen eigenen VM-Token (`CONF_VM_TOKEN`) und eine Webhook-ID; beides steht im Config-Entry (HA `.storage`), auf der VM in `/opt/tv-streamer/config-update.sh`. Der LG-Pairing-Schlüssel (`CONF_LG_TOKEN`) ebenfalls im Entry. Niemals in Repos.
- **Endpunkte:** die VM holt mit `Authorization: Bearer <VM-Token>` von `<HA>/api/tv_streamer/<entry>/…` die Compose-Datei, das Update-Skript und die Streamer-Dateien; der Streamer meldet Zustand/Tasten/Messwerte an den Webhook (lokal).
- **Update auf die VM:** neue Integration über HACS + HA-Neustart → neue Dateien/Manifest-Hash → der systemd-Timer auf der VM (alle 5 min) holt sie und baut die Container neu. Kontrolle: Sensor „Fassung“.

## 6. Bekannte Fehler, offene Fragen, Entscheidungen

- **Zeiger pausiert nach Pfeiltasten** (siehe 2): Ursache Magic Remote, steht in der README. Empfehlung: Mausrad/Farbtasten statt Pfeile.
- **Offene Fragen an Sebastian:** keine.
- **Entscheidungen:** Zurück im Streamer nie hinter die Startseite (.40); F13–F23 per XChangeKeyboardMapping belegt, weil Sunshine unter Linux Medientasten verwirft; Farb-/Medientasten als F13–F17; Messmarken F18–F23.

## 7. Geänderte HA-Objekte

| Objekt | ID | Änderung |
|---|---|---|
| Integration | TV Streamer (Schlafzimmer, Wohnzimmer) | Config-Entries (bestehend) |
| Dashboard | `tv-dashboard` | `kiosk_mode` für Benutzer TV (bestehend) |

Keine Skripte, Automationen oder Helfer durch diese Arbeitsrunde geändert.

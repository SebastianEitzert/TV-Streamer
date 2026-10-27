# HANDOFF – TV-Streamer

Stand: 2026-10-27 (abends). Diese Datei wird bei jeder Änderung mitgepflegt. Keine Zugangsdaten hier ablegen.

## 1. Stand

| | |
|---|---|
| Letztes Release | **0.4.8**, Tag `v0.4.8` (GitHub-Release mit `tv_streamer.zip`) |
| Streamer-Fassung im Paket | `FASSUNG = "2026-10-27.47"` (`custom_components/tv_streamer/streamer/server.py`) |
| In Home Assistant eingespielt | Integration 0.4.7, Fassung `2026-10-27.45` (Sensor `sensor.tv_streamer_schlafzimmer_fassung`). 0.4.8 ist veröffentlicht, aber noch **nicht** über HACS installiert. |
| Dateien unter `www/` | keine |
| Moonlight-IPK | Test-Build vom 27.10. 20:31: https://github.com/SebastianEitzert/TV-Streamer/actions/runs/40578741552 (Artefakt `moonlight-webos-tvstreamer`, App „Moonlight TVS“, moonlight-tv v1.6.37 + Patch). Auf den Fernsehern ist noch der Build davor installiert. |
| Branch | nur `main` |

## 2. Aktueller Auftrag

Für die Grundstücks-Karte (Floorplan Lite) wichtig:
- **Erledigt:** `window.__tvStreamer = {name}` für Gerätenamen (0.4.7), Pop-up-Erkennung ignoriert `#plan=…` (Seite: .45; Zurück-Logik im Streamer: .46, 0.4.8).
- **Offen / Test läuft:** Mauszeiger hängt nach Pfeiltasten. Messung (0.4.6) ergab: webOS liefert nach einer Pfeiltaste 1–3 s keine Zeigerbewegung und meldet kein Aus-/Einblenden; Wiedereinschalten des Zeigers (bisheriger Patch) hilft daher nicht. Test-Build 0.4.8: Moonlight abonniert `luna://com.webos.service.mrcu/sensor/getSensorData` und bewegt in der Sperrzeit die Maus selbst. Marken F21 (Daten kamen), F22 (Dienst nicht aufrufbar), F23 (abgelehnt) erscheinen in `pointer_measurement`. Ergebnis von Sebastians Test steht aus.
- **Halb fertig:** nichts im Code. Datei/Funktion des Tests: `moonlight/patches/0001-tv-streamer-remote-keys-and-pointer.patch` → `keyboard_webos.c`: `tvs_sensor_start`, `tvs_sensor_cb`; `CMakeLists.txt`: `TVS_HELPERS`.

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

- **Zeiger hängt nach Pfeiltasten** (siehe 2): Ursache in webOS (keine Bewegungsdaten in 5-Way-Modus). Wenn der Sensor-Test scheitert: Pfeiltasten in der Skript-Vorlage meiden oder hinnehmen.
- **Offene Frage an Sebastian:** Ergebnis des Sensor-Tests (Messung lesen: Attribut `pointer_measurement` am Zustand-Sensor `sensor.tv_streamer_schlafzimmer_zustand`).
- **Entscheidungen:** Zurück im Streamer nie hinter die Startseite (.40); F13–F23 per XChangeKeyboardMapping belegt, weil Sunshine unter Linux Medientasten verwirft; Farb-/Medientasten als F13–F17; Messmarken F18–F23.

## 7. Geänderte HA-Objekte

| Objekt | ID | Änderung |
|---|---|---|
| Integration | TV Streamer (Schlafzimmer, Wohnzimmer) | Config-Entries (bestehend) |
| Dashboard | `tv-dashboard` | `kiosk_mode` für Benutzer TV (bestehend) |

Keine Skripte, Automationen oder Helfer durch diese Arbeitsrunde geändert.

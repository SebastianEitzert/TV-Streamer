# HANDOFF – TV-Streamer

Stand: 2026-10-27. Diese Datei wird bei jeder Änderung mitgepflegt. Sie ist öffentlich: keine Zugangsdaten, IPs, Entitäts-IDs oder Benutzernamen. Installationsbezogene Details stehen in einer privaten Übergabedatei außerhalb des Repos.

## 1. Stand

| | |
|---|---|
| Letztes Release | **0.5.0**, Tag `v0.5.0` (GitHub-Release mit `tv_streamer.zip`) |
| Streamer-Fassung im Paket | `FASSUNG = "2026-10-28.48"` (`custom_components/tv_streamer/streamer/server.py`) |
| Moonlight-IPK | am Release jeder Version, neueste: https://github.com/SebastianEitzert/TV-Streamer/releases/latest/download/moonlight-tvs_arm.ipk (App „Moonlight TVS“, moonlight-tv v1.6.37 + Patch) |
| Branch | nur `main` |

## 2. Status

- `window.__tvStreamer = {name}` für Gerätenamen; Pop-up-Erkennung ignoriert `#plan=…` (für Floorplan Lite).
- **Abgeschlossen (nicht lösbar):** Mauszeiger pausiert nach Pfeiltasten 1–1,7 s. Ursache ist die Magic Remote selbst (sendet nach Tastendruck keine Bewegung). Versuche wurden in 0.5.0 entfernt; nicht erneut versuchen.
- Halb fertig: nichts. Nicht gepushte Änderungen: keine.

## 3. Aufbau

```
custom_components/tv_streamer/
  __init__.py, config_flow.py   Einrichtung je Streamer-VM, Webhook für Meldungen der VM
  api.py                        HTTP-Endpunkte für die VM: /api/tv_streamer/<entry>/{version,compose,update.sh,files,file/<name>}
  compose.py                    erzeugt docker-compose.yml für die VM
  streamer_files.py             liefert die Streamer-Dateien (streamer/) samt sha256-Manifest
  streamer/                     Image der VM: Dockerfile, server.py, client.html, clock.html
  vm_update.sh                  Skript auf der VM (systemd-Timer alle 5 min)
  coordinator.py, sensor.py, binary_sensor.py, button.py, event.py, lg.py, show.py   Entitäten, LG-TV-Steuerung
moonlight/                      UPSTREAM, patches/, RELEASE_NOTES.md
vm/proxmox-vm.sh                VM in Proxmox anlegen
tests/                          pytest
```

- **Kein Bundling.** Prüfung: `python3 -c "import ast; ast.parse(open('…/server.py').read())"`, Tests `pytest -q` (Action `validate.yml`).

## 4. Build und Release

- **Release:** Version in `manifest.json` erhöhen, `CHANGELOG.md` `## <version> – <Datum>`, auf `main` pushen → `release.yml` erstellt Tag, Release und `tv_streamer.zip`. Bei geänderten Streamer-Dateien `FASSUNG` in `server.py` hochzählen. Release erst, wenn der Maintainer es freigibt.
- **Moonlight-IPK:** Jeder Push auf `main` startet `moonlight-webos.yml`: klont moonlight-tv (Tag aus `moonlight/UPSTREAM`), wendet `moonlight/patches/*.patch` an, baut mit dem webOS-NDK und hängt das IPK an das Release der aktuellen Version (auch als `moonlight-tvs_arm.ipk`). Installation mit dem webOS Dev Manager (gleiche App-ID wie die offizielle App), danach TV einmal vom Netz trennen.
- **Commits** unter der GitHub-noreply-Adresse des Maintainers. Doku zweisprachig (Deutsch/Englisch).

## 5. Verbindung Integration – VM – HA

- **Config Flow:** je VM ein Eintrag (Adresse der VM, HA-URL, Start-URL, Reiter, Fernseher, Bild/Ton). Optionen zeigen den Einrichtungsbefehl für die VM.
- **Token:** eigener VM-Token und Webhook-ID im Config-Entry; auf der VM in `/opt/tv-streamer/config-update.sh`. LG-Pairing-Schlüssel ebenfalls im Entry. Niemals in Repos.
- **Update:** neue Integration über HACS + HA-Neustart → der systemd-Timer auf der VM (alle 5 min) holt neue Dateien und baut die Container neu. Kontrolle: Sensor „Fassung“.

## 6. Entscheidungen

- Zurück im Streamer nie hinter die Startseite.
- F13–F17 für Farb-/Medientasten per XChangeKeyboardMapping, weil Sunshine unter Linux Medientasten verwirft.
- Zeiger-Pause: Mausrad/Farbtasten statt Pfeiltasten empfehlen (README).

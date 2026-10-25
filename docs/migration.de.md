# Bestehende Streamer-VM auf die Integration umstellen

🇬🇧 [English](migration.md)

Für Installationen, die mit `bootstrap.sh` aus `www/tv-streamer` von Home Assistant eingerichtet wurden (handgeschriebene
`docker-compose.yml`, Vorlagen-Sensoren an einem Webhook, `shell_command` für die LG-Verlängerung).

## 1. Container, Volumes und Moonlight-Kopplung behalten

Container- und Volume-Namen ergeben sich aus dem Streamer-Namen, die Ports aus der Reihenfolge, in der die Streamer angelegt
werden. Die Streamer deshalb **mit ihren bisherigen Dienstnamen und in der bisherigen Port-Reihenfolge** anlegen:

| Bisher | Anlegen als | Ergebnis |
|---|---|---|
| Dienst `tv1`, Port 8091, Sunshine 47989 | 1. Streamer, Name `tv1` | `tv-tv1`, Volume `tv-tv1`, 8091, 47989 |
| Dienst `tv2`, Port 8092, Sunshine 48089 | 2. Streamer, Name `tv2` | `tv-tv2`, Volume `tv-tv2`, 8092, 48089 |

So bleiben Browser-Anmeldungen, Sunshine-Kopplung und die Host-Einträge in Moonlight gültig. Breite, Höhe, Zoom und Bitrate aus
der alten Compose-Datei übernehmen – der Fernsehertyp setzt nur Vorschläge. Unter *Allgemeine Einstellungen* das *Docker-Image*
auf den alten `image:`-Wert setzen.

## 2. Verhindern, dass der alte Weg die Compose-Datei überschreibt

Das alte `update.sh` lädt `docker-compose.yml` aus `www/tv-streamer` neu, sobald sich dort `VERSION` ändert. Vor dem Einrichten
des neuen Timers `docker-compose.yml` aus der Dateiliste in `www/tv-streamer/bootstrap.sh` entfernen (Schleife `for f in server.py …`).
`server.py`, `client.html` usw. kommen weiter von dort, bis das VM-Image Teil dieses Repositorys ist.

> Seit Fassung 0.3 liefert die Integration auch die Dateien des Streamer-Images und schaltet den alten
> `tv-streamer-update.timer` auf der VM beim ersten Update selbst ab.

## 3. Auf der VM einrichten

Den Befehl aus *Optionen → VM-Einrichtung* als root auf der VM ausführen. Prüfen mit `journalctl -u tv-streamer-config` und
`docker compose ps` in `/opt/tv-streamer`. Die vorherige Datei bleibt als `docker-compose.yml.bak` erhalten.

## 4. Alte Teile in Home Assistant entfernen

Die Streamer melden jetzt an den eigenen Webhook der Integration. Sobald die neuen Entitäten Werte zeigen:

- die Vorlagen-Sensoren am alten Webhook entfernen (`configuration.yaml`, `template:` mit `trigger: webhook`) und Dashboards /
  Automationen anpassen, die sie verwenden,
- die Automation zur LG-Verlängerung und ihre `shell_command`-Einträge entfernen (sie enthalten das Token),
- Automationen prüfen, die vom alten Webhook ausgelöst wurden – sie bekommen keine Meldungen mehr.

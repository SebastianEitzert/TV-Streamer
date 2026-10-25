# TV-Streamer für Home Assistant

🇬🇧 [English version](README.md)

Home-Assistant-Dashboards auf Fernsehern, geliefert von einer kleinen VM: je Fernseher ein Chromium, unsichtbar gezeichnet und als
**MSE**-Video, über **WebRTC** oder über **Sunshine/Moonlight** zum Fernseher geschickt. Maus, Fernbedienung und Touch bedienen das
Dashboard, als hinge ein PC am Fernseher.

Dieses Repository enthält:

| Teil | Stand |
|---|---|
| `custom_components/tv_streamer` – Home-Assistant-Integration (Einrichtung in der Oberfläche, Geräte, Sensoren, Verlängerung des LG-Developer-Modus, Konfig-Endpunkt für die VM) | **0.1 – erste Fassung** |
| VM-Image (Docker: `server.py`, Chromium, Sunshine) und Proxmox-Einrichtung | geplant |
| Grundriss-Karte für Lovelace (HACS) | geplant |
| Angepasstes Moonlight für LG webOS (`.ipk`, GPL-3.0) | geplant |
| Dokumentiertes Wissen (webOS 4/5, MSE vs. WebRTC, Zeichen-Threads, iGPU-Grenzen) | geplant |

## Die Integration

**Einrichtung in der Oberfläche**, ganz ohne YAML:

- Ein Eintrag je VM: Adresse der VM und Adresse von Home Assistant aus Sicht der VM.
- **Optionen → Streamer hinzufügen**: Name, Raum, Fernseher (`media_player`), Fernsehertyp, Bildweg (MSE / WebRTC / Moonlight),
  Bildgröße, Zoom, Bitrate. Der Fernsehertyp setzt Werte, die an echten Geräten bestätigt sind:

  | Fernsehertyp | Bild | Zoom | Empfohlener Bildweg |
  |---|---|---|---|
  | LG webOS 4 (z. B. UK7550) | 1920×1080 | 1,25 | Moonlight oder MSE (WebRTC zeigt 4:3 und friert ein) |
  | LG webOS 5+ (z. B. 86UN85) | 2560×1440 | 1,67 | Moonlight |
  | andere | 1920×1080 | 1,25 | MSE |

- **Zusätzliche Reiter** (z. B. Loxone): Name, Adresse, *Anmeldung merken*, *nie neu laden*.
- **Allgemeine Einstellungen**: Startansicht, Ruhezeit ohne Zuschauer, *zurück zur Startansicht nach* (Moonlight-Pause), Chromium-Zeichen-Threads, Ton.
- **VM-Einrichtung**: zeigt einen einzeiligen Befehl für die VM (siehe unten).

**Je Streamer** gibt es ein Gerät (mit Link auf seine Webseite) und:

| Entität | |
|---|---|
| Zustand | zeigt / ruht / bereit, Attribute: Zuschauer, Bildweg, Format, Fernseher |
| Zuschauer, Verzögerung, Bildrate, Datenrate | Messwerte des Streamers |
| Reiter, Fassung | Diagnose |
| Erreichbar, Moonlight-Stream | Binärsensoren |
| Startansicht, Neu laden, Zurück, *<Reiter>* zeigen | Buttons zur Fernsteuerung des Streamer-Browsers |


Die Streamer melden sich an einem Webhook, den die Integration selbst anlegt (keine Vorlagen-Sensoren mehr nötig), und werden
zusätzlich alle 60 s abgefragt.

### LG-Developer-Modus

Moonlight ist eine selbst installierte App, deshalb brauchen LG-Fernseher den **Developer-Modus**. LG beendet ihn nach etwa
1000 Stunden, wenn er nicht verlängert wird. Das Session-Token – oder die ganze Verlängerungs-URL aus dem webOS Dev Manager – in
die Einstellungen des Streamers einfügen. Die Integration

- verlängert die Sitzung täglich (Standard 04:17, einstellbar),
- zeigt *Developer-Modus endet* und *zuletzt verlängert* als Sensoren und bietet einen Button *verlängern*,
- meldet eine **Reparatur**, wenn LG die Verlängerung ablehnt; die Reparatur fragt ein neues Token ab und prüft es sofort.

Das Token steht nur im Konfigurationseintrag – nicht in `www/`, nicht in der Compose-Datei, nicht in Logs oder Diagnosedaten.
Hinweis: Home Assistant speichert Konfigurationseinträge unverschlüsselt in `.storage/core.config_entries` – Sicherungen schützen.

### Wie die VM ihre Konfiguration bekommt

Die Integration erzeugt die `docker-compose.yml` der VM und liefert sie unter
`/api/tv_streamer/<entry_id>/docker-compose.yml` aus. Die VM meldet sich mit ihrem eigenen **VM-Token** an (entsteht mit dem
Eintrag, sichtbar nur unter *Optionen → VM-Einrichtung*), nicht mit einem HA-Benutzer. Den dort angezeigten Befehl einmal als root
auf der VM ausführen:

```sh
curl -fsSL -H "Authorization: Bearer <VM-Token>" http://<ha>:8123/api/tv_streamer/<entry_id>/update.sh | sh -s -- install
```

Er richtet einen systemd-Timer ein (`tv-streamer-config.timer`), der alle 5 Minuten prüft und bei einer neuen Konfiguration
`docker compose up -d --build --remove-orphans` ausführt. Ports je Streamer-Platz *n* (0, 1, …): Webseite `8091+n`,
WebRTC `8555+n`, Sunshine `47989+100·n` (Web-Oberfläche +1).

Umstieg einer bestehenden Installation: [docs/migration.de.md](docs/migration.de.md).

## Installation

HACS → *Benutzerdefinierte Repositories* → `https://github.com/SebastianEitzert/TV-Streamer`, Kategorie *Integration*. Oder
`custom_components/tv_streamer` nach `config/custom_components` kopieren. Neu starten, dann *Einstellungen → Geräte & Dienste →
Integration hinzufügen → TV Streamer*.

## Lizenz

GPL-3.0 – siehe [LICENSE](LICENSE). Der Moonlight-Teil wird auf [moonlight-tv](https://github.com/mariotaku/moonlight-tv) (GPL-3.0) aufbauen.

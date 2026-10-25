<p align="center"><img src="docs/images/logo.png" alt="TV Streamer" width="420"></p>

# TV-Streamer für Home Assistant

🇬🇧 [English version](README.md)

Home-Assistant-Dashboards auf Fernsehern, geliefert von einer kleinen VM: je Fernseher ein Chromium, unsichtbar gezeichnet und als
**MSE**-Video, über **WebRTC** oder über **Sunshine/Moonlight** zum Fernseher geschickt. Maus, Fernbedienung und Touch bedienen das
Dashboard, als hinge ein PC am Fernseher.

| Teil | Stand |
|---|---|
| `custom_components/tv_streamer` – Home-Assistant-Integration (Einrichtung in der Oberfläche, Geräte, Sensoren, Verlängerung des LG-Developer-Modus, Konfig-Endpunkt für die VM) | **0.1** |
| `vm/proxmox-vm.sh` – legt die VM in Proxmox VE an | **0.1** |
| `custom_components/tv_streamer/streamer` – Streamer-Image (Docker: `server.py`, Chromium, Kodierer, Sunshine), liefert die Integration an die VM | **0.3** |
| Grundriss-Karte für Lovelace (HACS) | geplant |
| Angepasstes Moonlight für LG webOS (`.ipk`, GPL-3.0) | geplant |

## Anleitung

```
Proxmox-VE-Host ──► VM „tv-streamer“ (Debian 13 + Docker)
                     ├─ Streamer 1 (Chromium + Kodierer/Sunshine) ──► Fernseher 1
                     └─ Streamer 2 …                              ──► Fernseher 2
Home Assistant ◄──── Statusmeldungen (Webhook) ── Streamer
Home Assistant ────► docker-compose.yml (Endpunkt mit Token) ──► VM
```

### 1. Proxmox VE installieren

Du brauchst einen Rechner mit [Proxmox VE](https://www.proxmox.com/de/proxmox-virtual-environment/uebersicht).
Offizielle Anleitung: **[Proxmox-VE-Installation](https://pve.proxmox.com/wiki/Installation)**
([Download](https://www.proxmox.com/de/downloads)). Home Assistant kann auf demselben Rechner laufen (z. B. HA OS als VM).

Größe der Streamer-VM: je Fernseher etwa 2 CPU-Kerne und 2 GB RAM bei Software-Kodierung mit 1080p/1440p.
4K ist für Software-Kodierung zu viel.

### 2. Streamer-VM anlegen

In der Proxmox-Oberfläche **Knoten → Shell** öffnen und ausführen:

```sh
curl -fsSLo /root/tv-streamer-vm.sh https://raw.githubusercontent.com/SebastianEitzert/TV-Streamer/main/vm/proxmox-vm.sh
bash /root/tv-streamer-vm.sh
```

Das Skript fragt VM-ID, IP-Adresse (oder DHCP), Bridge, Speicher, Kerne, RAM und ein Passwort für den Benutzer `tv`. Es lädt
das Debian-13-Cloud-Image (mit Prüfsumme), legt die VM an und installiert beim ersten Start Docker (etwa 5 Minuten).

Gib der VM eine **feste IP-Adresse** (im Skript oder als DHCP-Reservierung im Router) – Fernseher und Moonlight verbinden sich dorthin.

### 3. Nichts auf die VM kopieren

Das Streamer-Image (`Dockerfile`, `server.py`, `client.html`, Chromium-Richtlinien, Sunshine) ist **Teil der Integration**.
In Schritt 7 holt die VM es zusammen mit ihrer Konfiguration von Home Assistant und baut es selbst – der erste Bau dauert
etwa 10 Minuten. Nach jedem Update der Integration baut die VM automatisch neu, beide passen also immer zusammen.

### 4. Integration installieren

**HACS** (Repository muss öffentlich sein): HACS → ⋮ → *Benutzerdefinierte Repositories* →
`https://github.com/SebastianEitzert/TV-Streamer`, Kategorie *Integration* → installieren → Home Assistant neu starten.

**Von Hand:** `custom_components/tv_streamer` (samt `brand/` und `translations/`) nach `/config/custom_components/` von
Home Assistant kopieren, z. B. mit der App *Samba share* oder *File editor* → Home Assistant neu starten.

### 5. VM in Home Assistant eintragen

*Einstellungen → Geräte & Dienste → Integration hinzufügen → **TV Streamer***

- **Adresse der VM**: die feste IP der VM, z. B. `192.168.1.42`
- **Adresse von Home Assistant aus Sicht der VM**: die lokale Adresse, z. B. `http://192.168.1.10:8123`

### 6. Streamer und Reiter einrichten

*TV Streamer → Konfigurieren*:

1. **Streamer hinzufügen** – Name und Fernsehertyp, danach Raum, Fernseher (`media_player`), Bildweg, Bildgröße, Zoom und Bitrate.
   Der Fernsehertyp setzt an echten Geräten bestätigte Werte:

   | Fernsehertyp | Bild | Zoom | Empfohlener Bildweg |
   |---|---|---|---|
   | LG webOS 4 (z. B. UK7550) | 1920×1080 | 1,25 | Moonlight oder MSE (WebRTC zeigt 4:3 und friert ein) |
   | LG webOS 5+ (z. B. 86UN85) | 2560×1440 | 1,67 | Moonlight |
   | andere | 1920×1080 | 1,25 | MSE |

   Bei LG-Fernsehern mit Moonlight zusätzlich das **Developer-Mode-Session-Token** eintragen (siehe Schritt 9).
2. **Reiter hinzufügen** (optional) – z. B. Loxone oder die Router-Oberfläche: Name, Adresse, *Anmeldung merken*, *nie neu laden*.
3. **Allgemeine Einstellungen** – Startansicht (das Dashboard, das die Fernseher öffnen), Ruhezeit, *zurück zur Startansicht nach*,
   Zeichen-Threads, Ton, Zeitzone.
4. **Speichern.**

Ports je Streamer-Platz *n* (0, 1, …): Webseite `8091+n`, WebRTC `8555+n`, Sunshine `47989+100·n` (Web-Oberfläche +1).

### 7. VM mit Home Assistant verbinden

*Konfigurieren → **VM-Einrichtung*** zeigt einen einzeiligen Befehl mit dem VM-Token. Ihn einmal als root auf der VM ausführen –
in der Konsole der VM (vorher `sudo -i`) oder ohne Anmeldung aus der Proxmox-Shell:

```sh
qm guest exec <VMID> --timeout 600 -- sh -c "<Befehl aus der VM-Einrichtung>"
```

Er richtet den Timer `tv-streamer-config.timer` ein, holt die Dateien des Streamer-Images (geprüft per SHA-256) und die
erzeugte `docker-compose.yml`, baut das Image und startet die Container.
Ab dann erreicht jede Änderung in den Optionen der Integration die VM innerhalb von 5 Minuten.
Prüfen: `journalctl -u tv-streamer-config` und `docker compose ps` in `/opt/tv-streamer`.

### 8. Erstanmeldung (einmal je Streamer)

Am PC `http://<VM-IP>:8091/` öffnen (zweiter Streamer `:8092`, …). Man sieht und bedient den Chromium des Streamers.
In Home Assistant mit einem eigenen Benutzer (z. B. `tv`) anmelden und *Angemeldet bleiben* anhaken. Zusätzliche Reiter genauso.
Die Anmeldungen bleiben im Docker-Volume des Containers.

### 9. Fernseher einrichten

**Browser (MSE / WebRTC):** im Browser des Fernsehers `http://<VM-IP>:8091/` öffnen.

**Moonlight (LG webOS):**

1. Kostenloses LG-Entwicklerkonto anlegen: <https://webostv.developer.lge.com>.
2. Am Fernseher aus dem LG Content Store **Developer Mode** installieren, anmelden, *Dev Mode Status* einschalten (der
   Fernseher startet neu), danach *Key Server* einschalten.
3. Am PC den [webOS Dev Manager](https://github.com/webosbrew/dev-manager-desktop/releases) installieren, den Fernseher
   hinzufügen (IP und Passphrase aus der Developer-Mode-App) und [Moonlight TV](https://github.com/mariotaku/moonlight-tv/releases) installieren.
4. Die Sunshine-Oberfläche `https://<VM-IP>:47990` öffnen (zweiter Streamer `:48090`), die Zertifikatswarnung bestätigen und
   Sunshine-Benutzer und -Kennwort anlegen.
5. In Moonlight am Fernseher den Host `<VM-IP>` hinzufügen (zweiter Streamer `<VM-IP>:48089`); die angezeigte PIN in der
   Sunshine-Oberfläche eintragen.
6. **Session-Token für die Integration:** das Developer-Mode-Session-Token aus dem webOS Dev Manager kopieren – entweder die
   Verlängerungs-URL (`…/ResetDevModeSession.dev?sessionToken=…`) oder nur das Token – und in den Einstellungen des Streamers
   eintragen (*Konfigurieren → Streamer bearbeiten → LG-Developer-Mode-Session-Token*). Die Integration verlängert täglich.

### 10. Prüfen

Jeder Streamer ist ein Gerät mit Sensoren (Zustand, Zuschauer, Verzögerung, Bildrate, Datenrate), den Binärsensoren
*Erreichbar* und *Moonlight-Stream* und Buttons (Startansicht, Neu laden, Zurück, Reiter zeigen, Developer-Modus verlängern).
Lehnt LG eine Verlängerung ab, erscheint eine **Reparatur**, die ein neues Token abfragt.

Umstieg einer bestehenden, von Hand eingerichteten Installation: [docs/migration.de.md](docs/migration.de.md).

## So funktioniert es

- Die Integration erzeugt die `docker-compose.yml` und liefert sie unter `/api/tv_streamer/<entry_id>/docker-compose.yml` aus.
  Die VM meldet sich mit ihrem eigenen **VM-Token** an, nicht mit einem HA-Benutzer.
- Die Streamer melden ihren Zustand an einen Webhook der Integration und werden zusätzlich alle 60 s abgefragt.
- LG-Session-Tokens stehen nur im Konfigurationseintrag – nicht in `www/`, in der Compose-Datei, in Logs oder Diagnosedaten.
  Home Assistant speichert Konfigurationseinträge unverschlüsselt in `.storage/` – Sicherungen schützen.

## Lizenz

GPL-3.0 – siehe [LICENSE](LICENSE). Der Moonlight-Teil wird auf [moonlight-tv](https://github.com/mariotaku/moonlight-tv) (GPL-3.0) aufbauen.
Logo: eigene Gestaltung, siehe `docs/images/icon.svg`.

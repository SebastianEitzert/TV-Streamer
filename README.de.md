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
| `moonlight/` – angepasstes Moonlight für LG webOS (`.ipk`, GPL-3.0) | **erste Fassung** |

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

#### Grundeinstellungen in Proxmox (einmalig nach der Installation)

- **Paketquellen:** ohne Abo auf das *no-subscription*-Repository umstellen (*Knoten → Updates → Repositories*:
  `enterprise` deaktivieren, `No-Subscription` hinzufügen), danach *Updates → Aktualisieren → Upgrade*.
- **Feste IP-Adresse des Proxmox-Hosts** – bei der Installation festlegen; später unter *Knoten → System → Netzwerk*.
- **Netzwerk-Bridge:** Der Installer legt `vmbr0` auf dem LAN-Anschluss an. Die Streamer-VM muss im selben Netz wie die
  Fernseher hängen (kein NAT, kein VLAN dazwischen, außer es ist geroutet) – Moonlight und Wake on LAN brauchen das LAN.
- **Speicher:** `local-lvm` (oder ZFS) für die VM-Platten. Das VM-Skript ergänzt am Speicher `local` den Inhaltstyp
  *Snippets* selbst; von Hand: *Rechenzentrum → Storage → local → Bearbeiten → Inhalt: Snippets*.
- **Zeitzone:** *Knoten → System → Zeit* (die VM bekommt ihre Zeitzone aus den Einstellungen der Integration).
- **Sicherungen (optional):** *Rechenzentrum → Backup → Hinzufügen*. Die Streamer-VM kann draußen bleiben – ihre
  Konfiguration stellt die Integration wieder her; nur Anmeldungen und Moonlight-Kopplungen liegen in der VM (Docker-Volumes).
- **Home Assistant auf demselben Rechner:** Home Assistant Vorrang geben – das Skript setzt das CPU-Gewicht des Streamers
  auf 50 (`cpuunits`, die HA-VM hat den Standard 100); bei voller CPU gewinnt so immer Home Assistant.

### 2. Streamer-VM anlegen

In der Proxmox-Oberfläche **Knoten → Shell** öffnen und ausführen:

```sh
curl -fsSLo /root/tv-streamer-vm.sh https://raw.githubusercontent.com/SebastianEitzert/TV-Streamer/main/vm/proxmox-vm.sh
bash /root/tv-streamer-vm.sh
```

Das Skript fragt VM-ID, IP-Adresse (oder DHCP), Bridge, Speicher, Kerne, RAM und ein Passwort für den Benutzer `tv`. Es lädt
das Debian-13-Cloud-Image (mit Prüfsumme), legt die VM an und installiert beim ersten Start Docker (etwa 5 Minuten).

Gib der VM eine **feste IP-Adresse** (im Skript oder als DHCP-Reservierung im Router) – Fernseher und Moonlight verbinden sich dorthin.

#### Was das Skript einstellt – bzw. wie man die VM von Hand anlegt

| Einstellung | Wert | Hinweis |
|---|---|---|
| Betriebssystem | Debian 13 *genericcloud* (`qcow2`, als Platte importiert) | klein, mit cloud-init |
| Maschine / BIOS | `q35`, SeaBIOS | |
| CPU | Typ **host**, 4 Kerne (2 Fernseher: **8**), CPU-Gewicht **50** | `host` gibt dem Software-Kodierer alle CPU-Befehle (AVX2) |
| Arbeitsspeicher | 4096 MB, Ballooning mind. 2048 (2 Fernseher: **6144 MB**) | |
| Platte | 20 GB, VirtIO SCSI single, *Discard* + *SSD-Emulation* + *IO-Thread* | |
| Netzwerk | VirtIO an `vmbr0`, **feste IP** | |
| Anzeige / Konsole | serielle Konsole (`serial0`, Anzeige *Serial terminal 0*) | Konsole in der Proxmox-Oberfläche per xterm.js |
| QEMU Guest Agent | **an** | nötig für `qm guest exec` und `qm guest passwd` |
| Beim Booten starten | **an** | |
| Cloud-Init | Benutzer `tv` + Passwort, IP, Vendor-Snippet installiert Docker | |

Von Hand: VM mit diesen Werten anlegen (*VM erstellen*, oder `qm create` / `qm importdisk` für das Cloud-Image), ein
*CloudInit-Laufwerk* hinzufügen, im Reiter *Cloud-Init* Benutzer, Passwort und IP setzen, starten und Docker
(`curl -fsSL https://get.docker.com | sh`) sowie `qemu-guest-agent` installieren.

**CPU oder RAM später ändern:** `qm set <VMID> --cores 8 --memory 6144`, danach die VM in Proxmox **stoppen und starten**
(`qm reboot <VMID>`) – ein Neustart innerhalb der VM übernimmt neue Hardware nicht.

**VM-Passwort vergessen?** Auf dem Proxmox-Host: `qm guest passwd <VMID> tv`.

**Grafikkarte:** Der Streamer kodiert in Software (x264) – kein Durchreichen einer GPU nötig. Ein Fernseher mit 1440p braucht
etwa 1–1,5 Kerne. Eine Intel-iGPU zwischen Home Assistant OS und der VM zu teilen (SR-IOV) klappt nicht überall und ist
nicht erforderlich.

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
2. **Reiter hinzufügen** (optional) – z. B. Loxone oder die Router-Oberfläche: Name, Adresse (`192.168.1.160` genügt,
   `http://` wird ergänzt), *Anmeldung merken*, *nie neu laden*.
3. **Allgemeine Einstellungen** – Startansicht (das Dashboard, das die Fernseher öffnen; ein Pfad wie `/dashboard-tv/home`
   genügt), Ruhezeit, *zurück zur Startansicht nach*, Zeichen-Threads, Ton, Zeitzone.

Jeder Schritt wird gespeichert, sobald er bestätigt ist – einen eigenen Speichern-Knopf gibt es nicht.

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

**Browser (MSE / WebRTC):** im Browser des Fernsehers `http://<VM-IP>:8091/` öffnen (zweiter Streamer `:8092`, …).
*Am Fernseher zeigen* öffnet die Seite selbst.

**Moonlight (LG webOS, empfohlen):** Moonlight gibt es nicht im LG Content Store. Es wird als Entwickler-App installiert,
der Fernseher braucht dafür LGs **Entwicklermodus**. Das dauert einmalig etwa 30 Minuten.

#### 9.1 Entwicklermodus am Fernseher
1. Kostenloses LG-Entwicklerkonto anlegen: <https://webostv.developer.lge.com> (*Sign In → Create Account*).
2. Am Fernseher den **LG Content Store** öffnen, nach **Developer Mode** suchen und installieren.
3. *Developer Mode* öffnen, mit dem Entwicklerkonto anmelden und **Dev Mode Status** einschalten. Der Fernseher startet neu.
4. *Developer Mode* wieder öffnen und **Key Server** einschalten. Die App zeigt jetzt die **IP-Adresse** des Fernsehers und
   eine **Passphrase** – beides braucht der nächste Schritt. Hier läuft auch der Zähler der Sitzung (etwa 1000 Stunden);
   die Integration verlängert ihn täglich, sobald das Token eingetragen ist (9.4).

#### 9.2 webOS Dev Manager am PC
1. Den [webOS Dev Manager](https://github.com/webosbrew/dev-manager-desktop/releases) installieren (Windows, macOS, Linux).
2. *Gerät hinzufügen*: IP-Adresse des Fernsehers und die Passphrase aus der Developer-Mode-App eintragen. Der Dev Manager
   holt den SSH-Schlüssel vom Key Server des Fernsehers und verbindet sich.

#### 9.3 Moonlight installieren
1. Die neueste `com.limelight.webos_<Fassung>_arm.ipk` von den
   [Moonlight-TV-Releases](https://github.com/mariotaku/moonlight-tv/releases) herunterladen
   – oder, empfohlen, die [TV-Streamer-Fassung von Moonlight](moonlight/README.md): Sie gibt Blau, Grün und
   Wiedergabe/Pause an das Dashboard weiter und zeigt den Zeiger nach den Pfeiltasten sofort wieder. Jede Taste erscheint
   außerdem in Home Assistant als Ereignis-Entität `event.tv_streamer_<streamer>_fernbedienung` (Ereignistypen `blue`,
   `green`, `play_pause`, `stop`) – nutzbar als Auslöser in Automationen.
2. Im Dev Manager **Apps → Installieren** öffnen und die `.ipk` wählen. Moonlight erscheint in der App-Liste des Fernsehers.
3. Am PC die Sunshine-Oberfläche des Streamers öffnen: `https://<VM-IP>:47990` (zweiter Streamer `:48090`, …). Die
   Zertifikatswarnung bestätigen (Sunshine nutzt ein eigenes Zertifikat) und Sunshine-Benutzername und -Kennwort anlegen.
4. Am Fernseher Moonlight → **+** (Host hinzufügen) → `<VM-IP>` eintragen (zweiter Streamer `<VM-IP>:48089`, …).
   Moonlight findet den Streamer nicht von selbst, weil er in Docker läuft.
5. Moonlight zeigt eine **4-stellige PIN**. In der Sunshine-Oberfläche **PIN** öffnen, PIN und einen Namen für den
   Fernseher eintragen, senden.
6. In Moonlight den Host öffnen und **Home Assistant** einmal starten (und jeden zusätzlichen Reiter, z. B. **Loxone**).
   Danach startet *Am Fernseher zeigen* diese Apps direkt.

**Moonlight-Einstellungen** (Moonlight → Einstellungen, einmal je Fernseher):

| Einstellung | Wert | Warum |
|---|---|---|
| Auflösung | wie der Streamer: webOS 4 (z. B. UK7550) **1080p**, webOS 5+ (z. B. 86UN85) **1440p** | webOS 4 zeigt über 1080p ein grünes Bild |
| Bildrate | **60 Bilder/s** (30, falls es ruckelt) | |
| Bitrate | 10–16 Mbit/s | |
| **PC während des Streamings stummschalten** | **aus** | sonst **kein Ton** – Sunshine schaltet die Tonausgabe des Streamers stumm |
| Decoder | Voreinstellung | „SMP“ hat keinen Ton und viel mehr Verzögerung |
| Maus | **absolut** (Voreinstellung) | der Zeiger der Magic Remote trifft 1:1 auf das Dashboard |

#### 9.4 Session-Token für die automatische Verlängerung
LG beendet den Entwicklermodus nach etwa 1000 Stunden und entfernt Moonlight, wenn die Sitzung nicht verlängert wird.

1. Den Fernseher **einschalten** (der Dev Manager liest das Token per SSH vom Fernseher – er muss an und verbunden sein).
   Im Dev Manager den Fernseher wählen → **Info**. Die Seite zeigt die Restlaufzeit und die Knöpfe *Renew session* und
   **Renew automatically…**.
2. *Renew automatically…* zeigt die Verlängerungs-URL
   `https://developer.lge.com/secure/ResetDevModeSession.dev?sessionToken=…` – kopieren (ganze URL oder nur das Token).
3. In Home Assistant: *TV Streamer → Konfigurieren → Streamer bearbeiten → LG-Developer-Mode-Session-Token*, einfügen,
   speichern. Die Integration prüft das Token sofort.

Ohne Dev Manager lässt sich das Token per SSH am Fernseher lesen: `cat /var/luna/preferences/devmode_enabled`.
Die tägliche Verlängerung selbst braucht den Fernseher nicht: Home Assistant ruft direkt den LG-Server auf, das klappt
auch, wenn der Fernseher aus ist.
Das Token ändert sich, wenn der Entwicklermodus aus- und wieder eingeschaltet wird – die Integration meldet dann eine
**Reparatur**, die das neue abfragt.

Achtung bei Firmware-Updates des Fernsehers: Sie können den Entwicklermodus zurücksetzen – danach den Sensor
*Developer-Modus endet* prüfen.

### 10. Prüfen

Jeder Streamer ist ein Gerät mit Sensoren (Zustand, Zuschauer, Verzögerung, Bildrate, Datenrate), den Binärsensoren
*Erreichbar* und *Moonlight-Stream* und Buttons (Startansicht, Neu laden, Zurück, Reiter zeigen, Developer-Modus verlängern).
Lehnt LG eine Verlängerung ab, erscheint eine **Reparatur**, die ein neues Token abfragt.

Umstieg einer bestehenden, von Hand eingerichteten Installation: [docs/migration.de.md](docs/migration.de.md).

## Fehlersuche

| Problem | Ursache / Lösung |
|---|---|
| Moonlight: Bild, aber **kein Ton** | Moonlight-Einstellung *PC während des Streamings stummschalten* muss **aus** sein. |
| Moonlight: grünes oder schwarzes Bild, nur ein Standbild | Auflösung zu hoch für den Fernseher (webOS 4: höchstens 1080p). In Moonlight und in den Streamer-Einstellungen dieselbe Größe einstellen. |
| Moonlight findet den Host nicht | Von Hand hinzufügen: `<VM-IP>` (zweiter Streamer `<VM-IP>:48089`). Docker verhindert die automatische Suche. |
| Sunshine-Oberfläche meldet *forbidden* / CSRF-Fehler | Mit der IP-Adresse der VM öffnen, wie sie in der Integration eingetragen ist (`https://<VM-IP>:47990`), nicht mit einem Hostnamen. |
| Sunshine startet nicht (`docker logs tv-<name>` zeigt `… .so: cannot open shared object file`) | Eine Bibliothek, die das Sunshine-AppImage erwartet, fehlt. Das Image installiert alle bekannten (z. B. `libpipewire-0.3-0t64`); braucht eine neue Sunshine-Fassung mehr, das Paket in `streamer/Dockerfile` ergänzen und ein Issue anlegen. |
| Entwicklermodus abgelaufen, Moonlight ist weg | Entwicklermodus wieder einschalten (9.1), Moonlight neu installieren (9.3), das **neue** Token eintragen (9.4) – die Reparatur in Home Assistant fragt danach. |
| VM übernimmt Änderungen nicht | Auf der VM: `journalctl -u tv-streamer-config -n 50`. „token rejected“ → Befehl aus der *VM-Einrichtung* erneut ausführen. |
| *Am Fernseher zeigen* tut nichts, wenn der Fernseher aus ist | In den Streamer-Einstellungen *Einschalten mit (Wake on LAN)* setzen; am Fernseher muss Einschalten über das Netz an sein (z. B. *Einstellungen → Allgemein → Mobile TV On*; der Menüname unterscheidet sich je Modell). |

## So funktioniert es

- Die Integration erzeugt die `docker-compose.yml` und liefert sie unter `/api/tv_streamer/<entry_id>/docker-compose.yml` aus.
  Die VM meldet sich mit ihrem eigenen **VM-Token** an, nicht mit einem HA-Benutzer.
- Die Streamer melden ihren Zustand an einen Webhook der Integration und werden zusätzlich alle 60 s abgefragt.
- LG-Session-Tokens stehen nur im Konfigurationseintrag – nicht in `www/`, in der Compose-Datei, in Logs oder Diagnosedaten.
  Home Assistant speichert Konfigurationseinträge unverschlüsselt in `.storage/` – Sicherungen schützen.

## Mitmachen

Siehe [CONTRIBUTING.md](CONTRIBUTING.md) (englisch). Änderungen: [CHANGELOG.md](CHANGELOG.md).
Sicherheit: [SECURITY.md](SECURITY.md). Fremdsoftware: [THIRD_PARTY.md](THIRD_PARTY.md).

## Lizenz

GPL-3.0 – siehe [LICENSE](LICENSE). Der Moonlight-Teil wird auf [moonlight-tv](https://github.com/mariotaku/moonlight-tv) (GPL-3.0) aufbauen.
Logo: eigene Gestaltung, siehe `docs/images/icon.svg`.

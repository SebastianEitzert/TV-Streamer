#!/usr/bin/env python3
"""TV Streamer – KI generiert (Claude, 21.10.2026)

Ein aktueller Chromium läuft auf der VM in einem virtuellen Bildschirm (Xvfb) und zeigt Home Assistant
oder Loxone. ffmpeg kodiert diesen Bildschirm als H.264. Der Fernseher bekommt das Bild als fragmentiertes
MP4 über WebSocket und spielt es mit seinem normalen Videoweg (MSE, Hardware-Decoder) ab – der Browser des
Fernsehers muss also nur Video abspielen, egal wie aufwendig die Seite ist. Zeiger, Klicks, Mausrad und
Tasten der Magic Remote gehen per WebSocket zurück und werden über das DevTools-Protokoll (CDP) in den
Chromium eingespeist.

Je Fernseher läuft eine Instanz (eigener Container, eigenes Browser-Profil, eigener Port).
Python: aiohttp, PyAV (WebRTC-Kodierer; ohne PyAV ffmpeg über go2rtc). Programme: Xvfb, chromium, ffmpeg, xdotool, go2rtc.

23.10.2026 (.12): zweiter Bildweg WebRTC – deutlich weniger Verzögerung als MSE (dort puffert der Fernseher ~0,5 s).
go2rtc läuft als Unterprozess, startet seinen eigenen Kodierer nur, solange jemand per WebRTC zuschaut, und ist nur
über eine Unix-Socket-Datei erreichbar (keine offene Schnittstelle). Die Verbindung handelt die Empfangsseite über
den Video-WebSocket aus (?mode=webrtc); das Bild kommt per UDP/TCP über WEBRTC_PORT. MSE bleibt Rückfall.

23.10.2026 (.15): Für WebRTC kodiert der Streamer selbst (PyAV) und liefert per RTSP an go2rtc. Schlüsselbilder gibt es nur
auf Abruf (Einstieg, Paketverlust) – kein Paket-Schwall, und trotzdem läuft das Bild nach einer Störung sofort weiter.

23.10.2026 (.17): Fehlersuche aus der Ferne – die Meldungen an HA enthalten die letzten Ereignisse des Streamers
(meldungen), den Zustand von go2rtc (was kommt an, was geht an wen) und 5 s nach jedem Aushandeln eine Prüfung, ob go2rtc
dem Fernseher wirklich Bilder schickt. Eigener Kodierer ohne spaltenweise Erneuerung (WEBRTC_REFRESH=0): Schlüsselbilder
gibt es ohnehin nur auf Abruf, und das wandernde Erneuerungsband kann flimmern.

23.10.2026 (.19): Beim Aushandeln stehen die Videoformate aus Angebot und Antwort in den Meldungen (Fehlersuche
Schlafzimmer: der Fernseher verwarf nach einem Abbruch alle WebRTC-Pakete bis zum Aus/An). Die Seite bekommt die Fassung
mit und lädt sich nach einem Update selbst neu.

23.10.2026 (.21): Die Fassung, die die Seite bekommt, enthält eine Prüfsumme der Empfangsseite – so lädt sie sich auch
neu, wenn sich nur `client.html` geändert hat. Empfangsseite: zu langsames Dekodieren → MSE (siehe dort).

23.10.2026 (.23): Seiten-Wächter. (1) Steht ein Kamerabild auf der HA-Seite länger als 20 s (Schlafzimmer 19:44: Kamera
stand, der Rest lief), wird erst der Kamera-Player neu eingehängt (startet seinen Stream neu), hilft das nicht, die Seite
neu geladen (höchstens alle 10 min). (2) Die HA-Sprache des angemeldeten Benutzers wird auf HA_SPRACHE gestellt (Dashboard
war englisch), Chromium meldet Deutsch als Sprache. (3) Die Messwerte enthalten den freien Speicher der VM, den Speicher
von Chromium und die Last – die Proxmox-Anzeige zählt den Datei-Puffer mit und sagt wenig.

23.10.2026 (.24): Fernseher bekommen das WebRTC-Bild in 1920×1070 (WEBRTC_TV=fhd) – so groß ist ihre Browserfläche; das
volle Bild verkleinerten sie ohnehin selbst. Der Wohnzimmer-Fernseher schaffte das volle Bild ab 18:54 nur noch mit
7 Bildern/s, 1920er und 1280er mit 30. Die Empfangsseite stuft bei zu langsamem Dekodieren selbst weiter ab.

24.10.2026 (.27): Keine Hinweistexte (Tooltips) mehr. Chromium setzt sie an den echten Mauszeiger des virtuellen Bildschirms,
und der steht immer in der Mitte (der Zeiger des Fernsehers kommt nur über das DevTools-Protokoll in die Seite) – über dem
X eines Pop-ups erschien „close“ mitten im Bild (Wohnzimmer 24.10. 01:18). Jede Seite bekommt ein kleines Skript, das beim
Überfahren die title-Attribute (und SVG-<title>) der Elemente unter dem Zeiger entfernt.
Tastatur für den Fernseher: Bekommt im Chromium ein Textfeld den Fokus, meldet ein kleines Skript in der Seite das über eine
Bindung (Runtime.addBinding) an den Streamer; der schickt es an die Empfangsseiten. Dort erscheint ein eigenes Eingabefeld –
ein Klick darauf öffnet die Tastatur des Fernsehers (bzw. des Handys). Was dort getippt wird, kommt als echte Eingabe
(insertText, Rücktaste, Enter) in das Feld im Chromium. Inhalte von Passwortfeldern werden weder gemeldet noch protokolliert.

24.10.2026 (.28): Zurück geht nie hinter die Startseite. Dort bleibt die Taste ohne Wirkung, außer ein Pop-up (#raum) oder ein
HA-Dialog ist offen – den schließt sie. Vorher kam auf der Startseite die leere Seite vom Ruhen (about:blank, Wohnzimmer 24.10.
01:43). Leere Seiten und Fehlerseiten im Verlauf werden übersprungen; im Loxone-Reiter führt Zurück von dessen erster Seite zu
Home Assistant.

24.10.2026 (.29): Keine Bildlaufleisten mehr (HIDE_SCROLLBARS, Chromium --hide-scrollbars) – am Fernseher scrollt man mit dem
Rad; im Schlafzimmer (Seite 1280×713) war das Dashboard ein paar Punkte zu hoch und zeigte rechts eine Leiste. Zurück erkennt
offene HA-Dialoge auch an der Adresse (?more-info-entity-id=… – so öffnet HA die große Kamera-Ansicht) und schließt sie.

24.10.2026 (.30): Loxone (KEIN_NEULADEN) wird nicht neu geladen – weder mit Gelb/„Neu laden“ noch mit erneutem Grün; das
meldete jedes Mal ab (Test 24.10. 02:17). Kurze Hinweise erscheinen am Fernseher (z. B. „Schon auf der Startseite“).
Loxone-Anmeldung merken (ZUGANG_REITER): Nach einer erfolgreichen Anmeldung im Loxone-Reiter liegen Benutzer und Kennwort
im Volume des Containers (/data, nur für den Container lesbar – nie in HA, nie im Protokoll); erscheint die Anmeldeseite
wieder, füllt der Streamer beide Felder aus (anmelden klickt man selbst). Löschen: /api/cmd {"c": "zugang_vergessen"}.
Ton (AUDIO=1): PulseAudio-Senke im Container, Chromium gibt dorthin aus; go2rtc liefert den Ton als Opus per WebRTC dazu,
im MSE-Strom steckt er als AAC (Stücke zu 33 ms). Die Empfangsseite fordert ihn bisher nur mit ?ton=1 an (zum Testen).
Bindungen (Tastatur, Anmeldung) werden nach jedem Seitenwechsel neu gesetzt – ohne Runtime.enable übernimmt Chromium sie
nicht in neue Seiten (das Eingabefeld fehlte sonst nach dem Ruhen des HA-Reiters).

24.10.2026 (.32): VP8-Quelle „bild_vp8“ (WEBRTC_VP8, Standard 1280 breit) – Versuch fürs Schlafzimmer: Dort dekodiert der
Fernseher das H.264-WebRTC-Bild, zeigt es aber nicht an (schwarz oder stehend, auch per Canvas schwarz – 24.10. 09:34/09:47).
VP8 dekodiert der Browser selbst; vielleicht läuft es an der defekten Videoebene vorbei. Kodiert über go2rtc exec (libvpx,
Schlüsselbild jede Sekunde), nur solange jemand diese Quelle anfordert (Empfangsseite ?webrtc=vp8).
Beim Öffnen der Empfangsseite kommt der HA-Reiter nach vorn (Befehl „zeige_home“, Test 24.10. 09:53: Loxone lässt
sich aus seinem schwarzen Bildschirmschoner nur durch Bewegung holen – Tests sollen immer mit Home Assistant beginnen).
Bildweg JPEG (?video=jpeg, Test 24.10. 10:04: „Die wäre natürlich interessant“): Einzelbilder statt Video, gezeichnet
von der Empfangsseite selbst (zwei <img> im Wechsel) – am Videoweg des Schlafzimmer-Fernsehers vorbei, der WebRTC zwar
dekodiert, aber nicht anzeigt; Seiteninhalt (die Einblendung) zeigte er immer. Ein Kodierer-Thread (PyAV: x11grab →
verkleinern → mjpeg) schickt nur geänderte Bilder und nur an Seiten, die das vorige angezeigt haben (höchstens JPEG_VORRAT
unterwegs) – nichts staut sich, die Verzögerung bleibt bei Aufnahme + Kodieren + Übertragen + Dekodieren. JPEG_TV (hd 1280 /
fhd 1920 / voll), JPEG_Q (Qualität wie ffmpeg -q:v). Die Seite meldet jedes angezeigte Bild; der Streamer misst damit
„Aufnahme bis Anzeige“ (mit Rückweg) auf seiner eigenen Uhr.

24.10.2026 (.33): JPEG auch 960 breit (?jpeg=sd). Am Schlafzimmer-Fernseher dekodierte <img> ein 1280er-Bild in ~130 ms
(7,5 Bilder/s, Aufnahme bis Anzeige ~240 ms; mit kleinerer Datei q=10 kaum schneller) – die Empfangsseite kann deshalb jetzt
auch per createImageBitmap dekodieren (?jzeichnen=bitmap, mehrere Bilder zugleich).

24.10.2026 (.34): Video-WebSocket ohne Kompression (permessage-deflate). aiohttp hatte jedes MSE- und JPEG-Stück zusätzlich
mit zlib gepackt – nutzlos (schon komprimiert), kostet die VM Rechenzeit und den Fernseher das Entpacken jedes Stücks.

24.10.2026 (.35): Messungen, wo die Reaktionszeit bleibt. (1) CPU je Prozessgruppe dieses Containers (Chromium Seiten /
Zeichnen / Rest, ffmpeg, go2rtc, Xvfb, Streamer, Ton) in % eines Kerns, dazu die VM gesamt und „steal“ (Rechenzeit, die
Proxmox der VM gerade nicht gibt) – alle 10 s, im Status unter „cpu“. (2) Reaktion im Browser: in jedem Reiter misst ein
PerformanceObserver (Event Timing) je Eingabe die Zeit von der Eingabe bis zum nächsten gezeichneten Bild, dazu lange
Aufgaben (> 50 ms) – im Status unter „leistung“ (letzte 2 min). (3) /api/cmd {"c": "probe", "art": "pfeil"|"maus"} löst
Testeingaben aus (← und → wechseln das Geschoss; Zeiger fährt hin und her). (4) /api/cmd {"c": "ruhig", "stufe": 0|1|2}:
1 = Seiten sehen „weniger Bewegung“ (prefers-reduced-motion), 2 = zusätzlich ohne Unschärfe-Filter, Animationen und
Übergänge (wirkt nach dem nächsten Neuladen der Seite ganz). Voreinstellung RUHIG (0) – Stufe 2 ist nur zum Messen gedacht.

24.10.2026 (.36): Pop-up-Messung. Am Schlafzimmer brauchte ein Raum-Pop-up 2–3 s bis ganz offen, mit JPEG (~0,3 s Bildweg)
noch 1–1,5 s, und der Klick, der es öffnet, kam erst nach bis zu 408 ms zum nächsten Bild (Event Timing) – ein Teil der
Zeit entsteht also beim Aufbauen im Browser. /api/cmd {"c": "popup", "hash": "#wohnzimmer,#kuche", "ms": 3000} öffnet die
Pop-ups nacheinander wie die Grundriss-Karte (history.pushState + location-changed), misst bis zu ms lang und schließt sie
wieder (history.back). Gemessen: Zeit bis zum ersten Bild, lange Bilder (Long Animation Frames ≥ 50 ms) mit Summe,
Blockierzeit, Stil/Layout und Skripten (nach Datei und Funktion), lange Aufgaben, Bilder/s, „ruhig ab“ (Ende des letzten
langen Bildes). Nur im HA-Reiter, nur ohne offenes Pop-up, nur Adressen der Form #name. Ergebnisse unter „popup“ im Status
und einmal in der Meldung an HA.

24.10.2026 (.37): Sunshine-Host für Moonlight (MOONLIGHT=1, zuerst nur Schlafzimmer – Standard aus, dann unverändert).
Sunshine (LizardByte, im Image unter /opt/sunshine) nimmt denselben Xvfb-Bildschirm auf wie der Browser (X11-Aufnahme,
Software-Kodierung libx264, keine Grafikkarte) und schickt ihn per Moonlight-Protokoll an die Moonlight-TV-App auf dem
Fernseher – am Browser des Fernsehers und am MSE/WebRTC-Weg vorbei. Konfig und Kopplung liegen nur im Volume
(/data/sunshine), nie in HA. Ein laufender Moonlight-Stream hält den HA-Reiter wach: Sunshine ruft über global_prep_cmd
beim Start/Ende /api/cmd {"c":"moonlight","an":0|1} auf. Web-UI zum Anlegen von Benutzer/Kennwort und zur PIN-Kopplung:
https://<IP der VM>:47990 (origin_web_ui_allowed = lan). Ports 47984–47990/tcp, 48010/tcp, 47998–48000/udp.
"""
import asyncio
import base64
import collections
import ipaddress
import json
import logging
import os
import re
import shutil
import signal
import struct
import sys
import threading
import time
import zlib
from fractions import Fraction
from urllib.parse import urlsplit

from aiohttp import ClientSession, ClientTimeout, UnixConnector, WSMsgType, web

try:   # PyAV: eigener WebRTC-Kodierer, der auf Abruf ein Schlüsselbild liefert (fehlt es → go2rtc exec)
    import av
    if not ({"x11grab", "rtsp"} <= set(av.formats_available) and "libx264" in av.codecs_available):
        av = None
except Exception:
    av = None
JPEG_OK = av is not None and "mjpeg" in av.codecs_available     # .32: Bildweg JPEG braucht PyAV (x11grab + mjpeg)


def env(name, default):
    return os.environ.get(name, default)


CFG = dict(
    name=env("TV_NAME", "tv"),
    start_url=env("START_URL", "http://homeassistant.local:8123/"),
    links=json.loads(env("LINKS", '{}')),
    width=int(env("WIDTH", "1920")),
    height=int(env("HEIGHT", "1080")),
    zoom=float(env("ZOOM", "1.5")),             # 1.5 → Seiten werden mit 1280×720 Punkten aufgebaut, gezeichnet in 1920×1080
    fps=int(env("FPS", "30")),
    bitrate=env("BITRATE", "8M"),
    gop=float(env("GOP_SECONDS", "1")),          # Schlüsselbild-Abstand: so lange wartet ein neu verbundener Fernseher höchstens
    codec=env("CODEC", "h264"),                  # h264 (Fernseher) | vp9 (nur für Tests in Browsern ohne H.264)
    preset=env("X264_PRESET", "veryfast"),
    port=int(env("PORT", "8090")),
    display=env("DISPLAY_NUM", ":99"),
    profile=env("PROFILE_DIR", "/data/profile"),
    cdp_port=int(env("CDP_PORT", "9222")),
    chromium=env("CHROMIUM_BIN", shutil.which("chromium") or shutil.which("chromium-browser") or "chromium"),
    chromium_flags=env("CHROMIUM_FLAGS", ""),
    accept_lang=env("ACCEPT_LANG", "de-DE,de"),           # Sprache, die Chromium Webseiten meldet (HA wählt danach)
    chromium_language=env("CHROMIUM_LANGUAGE", "de_DE:de"),   # Sprache von Chromium selbst (Linux: Umgebungsvariable LANGUAGE)
    ha_sprache=env("HA_SPRACHE", "de"),                  # HA-Sprache des angemeldeten Benutzers (leer = nicht anfassen)
    seiten_waechter=env("SEITEN_WAECHTER", "1") == "1",  # stehende Kamerabilder erkennen und neu starten
    hide_scrollbars=env("HIDE_SCROLLBARS", "1") == "1",  # keine Bildlaufleisten (am Fernseher scrollt das Rad)
    # Reiter, die nie neu geladen werden (Loxone meldet dabei ab); Reiter, dessen Anmeldung gemerkt und ausgefüllt wird
    kein_neuladen=[n.strip() for n in env("KEIN_NEULADEN", "").split(",") if n.strip()],
    zugang_reiter=env("ZUGANG_REITER", ""),
    ruhig=int(env("RUHIG", "0")),                # .35: 1 = weniger Bewegung, 2 = auch ohne Unschärfe/Animationen (Messung)
    moonlight=env("MOONLIGHT", "0") == "1",      # .37: Sunshine-Host für Moonlight auf dem Fernseher (zuerst nur Schlafzimmer)
    sunshine_bin=env("SUNSHINE_BIN", "/opt/sunshine/AppRun"),
    sunshine_dir=env("SUNSHINE_DIR", "/data/sunshine"),
    browser_bild=env("BROWSER_BILD", "1") == "1",
    moonlight_startseite_s=int(env("MOONLIGHT_STARTSEITE_S", "300")),   # .37n: Pause, nach der Moonlight wieder mit der HA-Startansicht beginnt   # .37j: 0 = kein Bild für den Fernseher-Browser (Code bleibt, Moonlight übernimmt)
    sunshine_port=int(env("SUNSHINE_PORT", "47989")),  # .37g: Basis-Port (Web-UI = +1); zweiter Fernseher auf eigener Portreihe
    zugang_hosts=[h.strip().lower() for h in env("ZUGANG_HOSTS", ".loxonecloud.com").split(",") if h.strip()],
    audio=env("AUDIO", "0") == "1",              # Ton: PulseAudio-Senke im Container, Opus per WebRTC (Empfangsseite: ?ton=1)
    audio_bitrate=env("AUDIO_BITRATE", "96k"),
    allow=env("ALLOW", "127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"),
    idle_stop=float(env("IDLE_STOP_SECONDS", "15")),        # Kodierer läuft nur, solange jemand zuschaut (+ Nachlauf)
    freeze_after=float(env("FREEZE_AFTER_SECONDS", "300")),  # Seite ruhen lassen (leere Seite), wenn so lange niemand zuschaut (0 = nie)
    ha_webhook=env("HA_WEBHOOK", ""),            # Messwerte alle 30 s an Home Assistant melden, solange jemand zuschaut
    # WebRTC (go2rtc). WEBRTC_PORT = Port, unter dem die Fernseher diesen Container erreichen (Docker: Host-Port); 0 = aus
    webrtc_port=int(env("WEBRTC_PORT", "0")),
    webrtc_listen=int(env("WEBRTC_LISTEN", "8555")),  # Port im Container (UDP und TCP)
    public_ip=env("PUBLIC_IP", ""),              # Adresse der VM – der Container kennt nur sein Docker-Netz
    video_tv=env("VIDEO_TV", "mse"),             # Bildweg für Fernseher ohne ?video= (mse | webrtc)
    video_pc=env("VIDEO_PC", "webrtc"),          # Bildweg für PC, Handy, Tablet ohne ?video=
    webrtc_tv=env("WEBRTC_TV", "fhd"),           # WebRTC-Bild für Fernseher ohne ?webrtc=: "" voll, fhd 1920, hd 1280 breit
    webrtc_vp8=env("WEBRTC_VP8", "hd"),          # .32: VP8-Quelle „bild_vp8“: hd 1280 / fhd 1920 breit, leer = keine
    webrtc_vp8_bitrate=env("WEBRTC_VP8_BITRATE", "6M"),
    # .32: Bildweg JPEG (?video=jpeg): Einzelbilder statt Video – die Empfangsseite zeichnet sie selbst (img), am Videoweg
    # des Fernsehers vorbei. Nur geänderte Bilder und nur so viele, wie der Fernseher anzeigt (siehe JpegEncoder).
    jpeg_tv=env("JPEG_TV", "hd"),                # JPEG-Bild ohne ?jpeg=: hd 1280, fhd 1920 breit, voll = volles Bild
    jpeg_q=int(env("JPEG_Q", "5")),              # Qualität wie ffmpeg -q:v: 2 beste … 31 schlechteste (5: Dashboard ~60–70 KB bei 1280)
    jpeg_vorrat=int(env("JPEG_VORRAT", "2")),    # so viele Bilder dürfen unterwegs sein (geschickt, noch nicht angezeigt)
    webrtc_profile=env("WEBRTC_PROFILE", "baseline"),   # baseline: versteht jeder WebRTC-Empfänger (Angebot meist 42e01f)
    webrtc_bitrate=env("WEBRTC_BITRATE", ""),    # leer = BITRATE
    # Große Schlüsselbilder kommen als Paket-Schwall – der Wohnzimmer-Fernseher verlor per UDP fast die Hälfte (23.10.).
    # Deshalb keine regelmäßigen Schlüsselbilder: Der eigene Kodierer schickt sie nur auf Abruf (klein gehalten durch
    # WEBRTC_BUFSIZE). WEBRTC_REFRESH=1 erneuert das Bild zusätzlich spaltenweise (intra refresh, .14/.15) – das wandernde
    # Band kann flimmern (Wohnzimmer 23.10. 17:24), deshalb seit .17 aus. Der exec-Rückfall erneuert immer spaltenweise.
    webrtc_refresh=env("WEBRTC_REFRESH", "0") == "1",
    webrtc_bufsize=env("WEBRTC_BUFSIZE", "1M"),  # begrenzt die Größe eines Bildes (1M → höchstens ~100 KB)
    # pyav: eigener Kodierer im Streamer, Schlüsselbild nur auf Abruf (Einstieg, Paketverlust) – go2rtc kann das bei
    # „exec“ nicht. exec: ffmpeg über go2rtc mit Schlüsselbild alle 2 s (Rückfall, falls PyAV fehlt).
    webrtc_encoder=env("WEBRTC_ENCODER", "pyav"),
    go2rtc=env("GO2RTC_BIN", shutil.which("go2rtc") or "/usr/local/bin/go2rtc"),
    go2rtc_dir=env("GO2RTC_DIR", "/tmp"),
    go2rtc_rtsp=int(env("GO2RTC_RTSP_PORT", "8554")),   # nur intern (127.0.0.1): ffmpeg → go2rtc
)
FASSUNG = "2026-10-25.41"
try:    # Prüfsumme dieser Datei – in den Meldungen; zeigt nach dem Einspielen, ob sie unverändert angekommen ist
    with open(os.path.abspath(__file__), "rb") as _fh:
        QUELLE = "%08x" % (zlib.crc32(_fh.read()) & 0xffffffff)
except OSError:
    QUELLE = "?"
HERE = os.path.dirname(os.path.abspath(__file__))
# Ton (.30): PulseAudio im Container ohne Hardware – Senke „tv“, ihr Abgriff „tv.monitor“ ist die Tonquelle
PULSE_DIR = os.path.join(CFG["go2rtc_dir"], "pulse-" + CFG["name"])
PULSE_SOCK = os.path.join(PULSE_DIR, "native")
PULSE_ENV = {"PULSE_SERVER": "unix:" + PULSE_SOCK, "PULSE_RUNTIME_PATH": PULSE_DIR}


def pulse_ready():
    return CFG["audio"] and os.path.exists(PULSE_SOCK)


def pulse_argv():
    os.makedirs(PULSE_DIR, mode=0o700, exist_ok=True)
    try:
        os.remove(PULSE_SOCK)            # Rest nach Absturz
    except OSError:
        pass
    return ["pulseaudio", "--daemonize=no", "--exit-idle-time=-1", "--disallow-exit=yes", "--use-pid-file=no", "-n",
            "--log-target=stderr", "--log-level=warning",
            "--load=module-native-protocol-unix socket=%s auth-anonymous=1" % PULSE_SOCK,
            "--load=module-null-sink sink_name=tv rate=48000 channels=2 sink_properties=device.description=Fernseher"]
NETS = [ipaddress.ip_network(n.strip(), strict=False) for n in CFG["allow"].split(",") if n.strip()]
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("tv-" + CFG["name"])


# ---------------------------------------------------------------- MP4-Boxen lesen

def boxes(data, start=0, end=None):
    """Kind-Boxen in data[start:end] als (Typ, Anfang Nutzdaten, Ende)."""
    end = len(data) if end is None else end
    i = start
    while i + 8 <= end:
        size, typ = struct.unpack(">I4s", data[i:i + 8])
        hdr = 8
        if size == 1:
            size = struct.unpack(">Q", data[i + 8:i + 16])[0]
            hdr = 16
        elif size == 0:
            size = end - i
        if size < hdr:
            break
        yield typ.decode("latin1"), i + hdr, i + size
        i += size


def find(data, path, start=0, end=None):
    """Erste Box entlang eines Pfads, z. B. ['moov', 'trak', 'mdia', 'mdhd'] → (Anfang, Ende) der Nutzdaten."""
    for typ, s, e in boxes(data, start, end):
        if typ == path[0]:
            if len(path) == 1:
                return s, e
            sub = s
            if typ in ("stsd",):
                sub = s + 8          # Version/Flags + Anzahl
            elif typ in ("avc1", "vp09"):
                sub = s + 78         # VisualSampleEntry
            elif typ == "mp4a":
                sub = s + 28         # AudioSampleEntry
            r = find(data, path[1:], sub, e)
            if r:
                return r
    return None


def track_list(moov):
    """Spuren im moov (.30: Bild und Ton): {track_ID: {"art": "vide"/"soun", "ts": Zeitbasis, "codec": …, "flags": …}}.
    flags = voreingestellte Bild-Merkmale aus trex (daran erkennt man Schlüsselbilder)."""
    out = {}
    stsd = ["mdia", "minf", "stbl", "stsd"]
    for typ, s, e in boxes(moov, 8):
        if typ == "trak":
            tk = find(moov, ["tkhd"], s, e)
            if not tk:
                continue
            p = tk[0]
            o = 20 if moov[p] == 1 else 12
            tid = struct.unpack(">I", moov[p + o:p + o + 4])[0]
            hd = find(moov, ["mdia", "hdlr"], s, e)
            art = moov[hd[0] + 8:hd[0] + 12].decode("latin1") if hd else "?"
            md = find(moov, ["mdia", "mdhd"], s, e)
            ts = 90000
            if md:
                q = md[0]
                ts = struct.unpack(">I", moov[q + 20:q + 24])[0] if moov[q] == 1 else struct.unpack(">I", moov[q + 12:q + 16])[0]
            codec = None
            r = find(moov, stsd + ["avc1", "avcC"], s, e)
            if r:
                codec = "avc1.%02X%02X%02X" % (moov[r[0] + 1], moov[r[0] + 2], moov[r[0] + 3])
            else:
                r = find(moov, stsd + ["vp09", "vpcC"], s, e)
                if r:
                    q = r[0] + 4             # Version/Flags
                    codec = "vp09.%02d.%02d.%02d" % (moov[q], moov[q + 1], moov[q + 2] >> 4)
                elif find(moov, stsd + ["mp4a"], s, e):
                    codec = "mp4a.40.2"      # AAC-LC (ffmpeg aac)
            t = out.setdefault(tid, {"flags": 0})
            t.update(art=art, ts=ts, codec=codec)
        elif typ == "mvex":
            for t2, s2, e2 in boxes(moov, s, e):
                if t2 == "trex":
                    tid = struct.unpack(">I", moov[s2 + 4:s2 + 8])[0]
                    out.setdefault(tid, {"art": "?", "ts": 90000, "codec": None})["flags"] = struct.unpack(">I", moov[s2 + 20:s2 + 24])[0]
    return out


def video_track(tracks):
    return next((t for t in tracks.values() if t.get("art") == "vide"), None) or next(iter(tracks.values()), {})


def codec_string(tracks):
    """Format für MediaSource, z. B. „avc1.640033“ oder mit Ton „avc1.640033,mp4a.40.2“ (Bild zuerst)."""
    cs = [t["codec"] for _, t in sorted(tracks.items(), key=lambda x: (x[1].get("art") != "vide", x[0])) if t.get("codec")]
    return ",".join(cs) or "avc1.640029"


def fragment_info(moof, tracks):
    """(Schlüsselbild?, baseMediaDecodeTime, Bildspur?) eines moof – nur die Bildspur zählt (Tonstücke sind immer
    „Schlüsselbilder“). Ohne Ton trägt jedes moof genau ein Bild (frag_every_frame), mit Ton ~33 ms Bild und Ton."""
    key, bmdt, vid = False, None, False
    single = len(tracks) <= 1
    for typ, s, e in boxes(moof, 8):
        if typ != "traf":
            continue
        tid, flags, tb = None, None, None
        for t2, s2, e2 in boxes(moof, s, e):
            vf = struct.unpack(">I", moof[s2:s2 + 4])[0]
            ver, fl = vf >> 24, vf & 0xFFFFFF
            if t2 == "tfhd":
                tid = struct.unpack(">I", moof[s2 + 4:s2 + 8])[0]
                flags = (tracks.get(tid) or {}).get("flags", 0)
                p = s2 + 8
                p += 8 if fl & 0x1 else 0
                p += 4 if fl & 0x2 else 0
                p += 4 if fl & 0x8 else 0
                p += 4 if fl & 0x10 else 0
                if fl & 0x20:
                    flags = struct.unpack(">I", moof[p:p + 4])[0]
            elif t2 == "tfdt":
                tb = struct.unpack(">Q", moof[s2 + 4:s2 + 12])[0] if ver == 1 else struct.unpack(">I", moof[s2 + 4:s2 + 8])[0]
            elif t2 == "trun":
                p = s2 + 8
                p += 4 if fl & 0x1 else 0
                if fl & 0x4:
                    flags = struct.unpack(">I", moof[p:p + 4])[0]
                elif fl & 0x400:
                    p += 4 if fl & 0x100 else 0
                    p += 4 if fl & 0x200 else 0
                    flags = struct.unpack(">I", moof[p:p + 4])[0]
        if single or (tracks.get(tid) or {}).get("art") == "vide":
            vid = True
            key = not ((flags or 0) & 0x10000)
            bmdt = tb
    return key, bmdt, vid


# ---------------------------------------------------------------- Prozesse

class Recent(logging.Handler):
    """Die letzten Meldungen (Warnungen und alles zu WebRTC, Fernsehern, Kodierern) – gehen mit den Messwerten an HA.
    So sieht man ohne Zugang zur VM, was im Streamer passiert ist."""
    KEYS = ("WebRTC", "Fernseher", "Kodierer", "go2rtc", "Loxone", "PulseAudio", "Ton", "Moonlight", "Sunshine")

    def __init__(self):
        super().__init__(logging.INFO)
        self.items = collections.deque(maxlen=60)
        self.seq = 0
        self.warn_seq = 0

    def emit(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return
        if "not enough frames to estimate rate" in msg:      # harmloser Hinweis von ffmpeg bei jedem Start
            return
        if record.levelno >= logging.WARNING or any(k in msg for k in self.KEYS):
            self.seq += 1
            if record.levelno >= logging.WARNING:
                self.warn_seq = self.seq
            self.items.append((self.seq, "%s %s%s" % (time.strftime("%H:%M:%S", time.localtime(record.created)),
                                                      "! " if record.levelno >= logging.WARNING else "", msg[:300])))

    def since(self, seq, limit=25):
        return [t for n, t in self.items if n > seq][-limit:]


RECENT = Recent()
log.addHandler(RECENT)

CHILDREN = set()      # alle gestarteten Programme – werden beim Beenden mit beendet
RUNNING = {}          # laufendes Programm je Name (supervise) – z. B. um go2rtc mit neuer Einstellung neu zu starten
STOPPING = False


def x_socket():
    return "/tmp/.X11-unix/X" + CFG["display"].lstrip(":").split(".")[0]


async def supervise(name, argv, echo=False, extra_env=None):
    """Startet ein Programm und startet es nach einem Absturz neu. argv darf eine Funktion sein (wird je Start neu gebaut).
    echo: jede Meldung des Programms gleich ins Protokoll (für go2rtc – meldet nur Warnungen)."""
    delay = 1
    while not STOPPING:
        args = argv() if callable(argv) else argv
        e = dict(os.environ, DISPLAY=CFG["display"], **(extra_env or {}))
        t0 = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(*args, env=e, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        except (FileNotFoundError, PermissionError):
            log.error("%s: Programm nicht gefunden (%s)", name, args[0])
            await asyncio.sleep(10)
            continue
        CHILDREN.add(proc)
        RUNNING[name] = proc
        log.info("%s gestartet (pid %s)", name, proc.pid)
        tail = []
        async for line in proc.stderr:
            text = line.decode("utf-8", "replace").rstrip()
            tail = (tail + [text])[-8:]
            if echo and text and "mDNS over IPv6" not in text:     # Container ohne IPv6 – harmlos
                log.warning("%s: %s", name, text[:300])
        code = await proc.wait()
        CHILDREN.discard(proc)
        if STOPPING:
            return
        log.warning("%s beendet (Code %s): %s", name, code, " | ".join(tail[-3:]))
        delay = 1 if time.time() - t0 > 60 else min(30, delay * 2)
        await asyncio.sleep(delay)


def chromium_argv():
    prof = CFG["profile"]
    os.makedirs(prof, exist_ok=True)
    for f in ("SingletonLock", "SingletonSocket", "SingletonCookie"):   # nach Absturz/Neustart des Containers
        try:
            os.remove(os.path.join(prof, f))
        except OSError:
            pass
    pref = os.path.join(prof, "Default", "Preferences")                 # keine „Wiederherstellen?“-Leiste nach Absturz
    try:
        with open(pref, encoding="utf-8") as fh:
            p = json.load(fh)
        p.setdefault("profile", {})["exit_type"] = "Normal"
        p["profile"]["exited_cleanly"] = True
        if CFG["accept_lang"]:                                          # navigator.languages → HA wählt Deutsch
            p.setdefault("intl", {})["accept_languages"] = CFG["accept_lang"]
            p["intl"]["selected_languages"] = CFG["accept_lang"]
        with open(pref, "w", encoding="utf-8") as fh:
            json.dump(p, fh)
    except (OSError, ValueError):
        pass
    argv = [
        CFG["chromium"], "--user-data-dir=" + prof, "--remote-debugging-port=%d" % CFG["cdp_port"],
        # Fenstergröße zählt in Seitenpunkten (nach Zoom): 1920×1080 bei Zoom 1,5 → 1280×720
        "--kiosk", "--window-position=0,0",
        "--window-size=%d,%d" % (round(CFG["width"] / CFG["zoom"]), round(CFG["height"] / CFG["zoom"])),
        "--force-device-scale-factor=%s" % CFG["zoom"],
        "--no-first-run", "--no-default-browser-check", "--noerrdialogs", "--disable-infobars",
        "--disable-session-crashed-bubble", "--hide-crash-restore-bubble", "--password-store=basic",
        "--disable-features=Translate,MediaRouter,OptimizationHints,AutofillServerCommunication",
        "--autoplay-policy=no-user-gesture-required", "--disable-dev-shm-usage", "--disable-gpu",
        "--disable-background-networking", "--disable-component-update", "--disable-sync", "--disable-default-apps",
        "--overscroll-history-navigation=0", "--lang=de-DE",
    ]
    if os.geteuid() == 0 or env("NO_SANDBOX", "1") == "1":
        argv.append("--no-sandbox")    # im Container ohne User-Namespaces nötig; der Browser öffnet nur HA/Loxone
    if CFG["accept_lang"]:
        argv.append("--accept-lang=" + CFG["accept_lang"])
    if CFG["hide_scrollbars"]:
        argv.append("--hide-scrollbars")     # .29: auch im sichtbaren Fenster wirksam (lokal geprüft)
    argv += [f for f in CFG["chromium_flags"].split() if f]
    argv.append(CFG["start_url"])
    return argv


async def wait_for_x():
    for _ in range(100):
        if os.path.exists(x_socket()):
            return True
        await asyncio.sleep(0.1)
    return False


def _tasten_belegen():
    """Läuft im Executor: F13–F17 per XChangeKeyboardMapping auf die Tastencodes 191–195 legen (libX11 über ctypes)."""
    import ctypes
    import ctypes.util
    x = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11") or "libX11.so.6")
    x.XOpenDisplay.restype = ctypes.c_void_p
    x.XStringToKeysym.restype = ctypes.c_ulong
    d = x.XOpenDisplay(CFG["display"].encode())
    if not d:
        raise OSError("Bildschirm %s nicht erreichbar" % CFG["display"])
    d = ctypes.c_void_p(d)
    try:
        syms = (ctypes.c_ulong * 5)(*[x.XStringToKeysym(b"F%d" % n) for n in (13, 14, 15, 16, 17)])
        x.XChangeKeyboardMapping(d, 191, 1, syms, 5)
        x.XSync(d, 0)
        if x.XKeysymToKeycode(d, ctypes.c_ulong(syms[0])) != 191:
            raise OSError("Belegung nicht übernommen")
    finally:
        x.XCloseDisplay(d)


async def tasten_belegen():
    """.39: F13–F17 (.41: F17 = Pause) auf freie Tastencodes legen. Sunshine gibt Tasten über XTest weiter und braucht dafür einen Tastencode;
    in der Standardbelegung von Xvfb hat F13–F17 keinen (191–195 heißen dort XF86Tools/XF86Launch5–8) – ohne diese Belegung
    verwirft Sunshine Blau, Grün, Wiedergabe/Pause und Stopp des angepassten Moonlight stillschweigend.
    (xmodmap übernimmt die Belegung im Xvfb nicht zuverlässig, daher direkt über libX11.)"""
    fehler = None
    for _ in range(20):
        try:
            await asyncio.get_running_loop().run_in_executor(None, _tasten_belegen)
            log.info("Tasten F13–F17 belegt (Farb- und Medientasten aus Moonlight)")
            return
        except Exception as e:
            fehler = e
            await asyncio.sleep(0.5)
    log.warning("Tasten F13–F17 nicht belegt: %s", fehler)


# ---------------------------------------------------------------- Chromium fernsteuern (CDP)

# Hinweistexte (Tooltips) unterdrücken (.27): Chromium zeigt sie am echten Mauszeiger des virtuellen Bildschirms, und der
# steht immer in der Mitte – der Zeiger des Fernsehers kommt nur über das DevTools-Protokoll in die Seite. Beim Überfahren
# verlieren die Elemente unter dem Zeiger (auch in Shadow-DOMs) ihr title-Attribut und SVG-<title>; der Text bleibt in
# data-tv-title erhalten.
OHNE_HINWEIS_JS = r"""(() => {
  if (window.__tvOhneHinweis) { return; }
  window.__tvOhneHinweis = 1;
  const weg = (e) => {
    const path = e.composedPath ? e.composedPath() : [e.target];
    for (const el of path) {
      if (!el || el.nodeType !== 1) { continue; }
      if (el.hasAttribute('title')) { el.setAttribute('data-tv-title', el.getAttribute('title')); el.removeAttribute('title'); }
      if (el.namespaceURI === 'http://www.w3.org/2000/svg') {
        for (const c of Array.from(el.children)) { if (c.localName === 'title') { c.remove(); } }
      }
    }
  };
  for (const t of ['pointerover', 'mouseover', 'mousemove']) { window.addEventListener(t, weg, true); }
})()"""

# Textfeld mit Fokus melden (.27): der Fernseher hat keine Tastatur für die Seite im Chromium – die Empfangsseite blendet
# ein eigenes Eingabefeld ein. Meldet über die Bindung __tvTastatur: an/aus, Art (text/password/number), Bezeichnung und –
# außer bei Passwörtern – den aktuellen Inhalt.
TASTATUR_JS = r"""(() => {
  if (window.__tvFeld) { return; }
  window.__tvFeld = 1;
  const melde = (o) => { try { if (window.__tvTastatur) { window.__tvTastatur(JSON.stringify(o)); } } catch (e) {} };
  const tief = () => { let a = document.activeElement; while (a && a.shadowRoot && a.shadowRoot.activeElement) { a = a.shadowRoot.activeElement; } return a; };
  const art = (el) => {
    if (!el || el.nodeType !== 1 || el.disabled || el.readOnly) { return null; }
    if (el.localName === 'textarea') { return 'text'; }
    if (el.localName === 'input') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      if (t === 'password') { return 'password'; }
      if (t === 'number') { return 'number'; }
      return ['text', 'search', 'email', 'url', 'tel'].indexOf(t) >= 0 ? 'text' : null;
    }
    return el.isContentEditable ? 'text' : null;
  };
  let offen = '', t = 0, n = 0;
  const nr = new WeakMap();
  const pruefe = () => {
    const el = tief(), typ = art(el);
    if (typ) {
      const host = el.getRootNode && el.getRootNode().host;
      const titel = String((host && host.label) || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('name') || '').slice(0, 80);
      const wert = typ === 'password' ? '' : String(el.value !== undefined ? el.value : (el.textContent || '')).slice(0, 500);
      if (!nr.has(el)) { nr.set(el, ++n); }
      const sig = typ + '|' + nr.get(el);   /* je Feld eine Meldung – auch bei gleich benannten Feldern */
      if (sig !== offen) { offen = sig; melde({ an: true, typ: typ, titel: titel, wert: wert }); }
    } else if (offen) {
      offen = '';
      melde({ an: false });
    }
  };
  window.addEventListener('focusin', () => { clearTimeout(t); t = setTimeout(pruefe, 30); }, true);
  window.addEventListener('focusout', () => { clearTimeout(t); t = setTimeout(pruefe, 200); }, true);
  window.addEventListener('pagehide', () => { if (offen) { offen = ''; melde({ an: false }); } });
})()"""

# Anmeldung merken (.30) – nur im Reiter ZUGANG_REITER (Loxone). Meldet über die Bindung __tvZugang: „formular“, sobald eine
# leere Anmeldeseite (Kennwortfeld) sichtbar ist (der Streamer füllt dann aus), und „angemeldet“ mit Benutzer und Kennwort,
# wenn die ausgefüllte Anmeldeseite danach ~3 s verschwunden bleibt (erfolgreich angemeldet). Sonst verlässt nichts die Seite.
ZUGANG_JS = r"""(() => {
  if (window.__tvZugangJs) { return; }
  window.__tvZugangJs = 1;
  const sende = (o) => { try { if (window.__tvZugang) { window.__tvZugang(JSON.stringify(o)); } } catch (e) {} };
  const alle = (root, out) => { for (const e of root.querySelectorAll('*')) { if (e.localName === 'input') { out.push(e); } if (e.shadowRoot) { alle(e.shadowRoot, out); } } return out; };
  const sichtbar = (e) => { const r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2 && getComputedStyle(e).visibility !== 'hidden'; };
  const felder = () => {
    const ins = alle(document, []).filter((e) => !e.disabled && sichtbar(e));
    const pw = ins.find((e) => (e.type || '').toLowerCase() === 'password');
    if (!pw) { return null; }
    let user = null;
    for (let k = ins.indexOf(pw) - 1; k >= 0; k--) { if (['text', 'email', ''].indexOf((ins[k].getAttribute('type') || '').toLowerCase()) >= 0) { user = ins[k]; break; } }
    return { pw: pw, user: user };
  };
  let letzt = null, gefragt = null, weg = 0, adresse = '';
  /* bei jeder Eingabe, Taste und jedem Klick (vor der Seite) den Stand merken – auch Enter direkt nach dem Tippen */
  const merke = () => { const f = felder(); if (f && f.pw.value && f.user && f.user.value) { letzt = { u: f.user.value, p: f.pw.value }; adresse = location.href; } };
  for (const t of ['input', 'change', 'keydown', 'click', 'submit']) { document.addEventListener(t, merke, true); }
  setInterval(() => {
    const f = felder();
    if (f) {
      weg = 0;
      if (f.pw !== gefragt && !f.pw.value) { gefragt = f.pw; sende({ art: 'formular' }); }
      merke();
    } else if (letzt && (++weg >= 4 && location.href !== adresse || weg >= 10)) {   /* weg und neue Adresse (bzw. 7 s weg) */
      sende({ art: 'angemeldet', u: letzt.u, p: letzt.p });
      letzt = null;
    }
  }, 700);
})()"""

# Anmeldeseite ausfüllen (.30): Werte wie getippt setzen (input/change, auch für Frameworks), leere Felder nur – nie absenden.
FUELLEN_JS = r"""((z) => {
  const alle = (root, out) => { for (const e of root.querySelectorAll('*')) { if (e.localName === 'input') { out.push(e); } if (e.shadowRoot) { alle(e.shadowRoot, out); } } return out; };
  const sichtbar = (e) => { const r = e.getBoundingClientRect(); return r.width > 2 && r.height > 2 && getComputedStyle(e).visibility !== 'hidden'; };
  const ins = alle(document, []).filter((e) => !e.disabled && sichtbar(e));
  const pw = ins.find((e) => (e.type || '').toLowerCase() === 'password');
  if (!pw) { return 'kein Formular'; }
  let user = null;
  for (let k = ins.indexOf(pw) - 1; k >= 0; k--) { if (['text', 'email', ''].indexOf((ins[k].getAttribute('type') || '').toLowerCase()) >= 0) { user = ins[k]; break; } }
  const setze = (el, v) => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v);
    el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
    el.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
  };
  if (user && !user.value) { setze(user, z.u); }
  if (!pw.value) { setze(pw, z.p); }
  return (user && user.value ? 'u' : '-') + (pw.value ? 'p' : '-');
})(%s)"""

# .35: Reaktion im Browser messen. Event Timing liefert je Eingabe (Zeiger, Klick, Taste) die Zeit von der Eingabe bis zum
# nächsten gezeichneten Bild („duration“, auf 8 ms gerundet) und wie lange die Verarbeitung dauerte. Lange Aufgaben
# (> 50 ms) zeigen, wie beschäftigt die Seite ist. Abgeholt alle 10 s per Runtime.evaluate (__tvLeistung).
PERF_JS = r"""(() => {
  if (window.__tvLeistung) return;
  const L = {ev: [], lt: 0, ltn: 0, t0: performance.now()};
  const C = {zeiger: 0, klick: 0, taste: 0};   /* alle Eingaben zählen – Event Timing meldet nur die ab 16 ms */
  addEventListener('pointerover', () => { C.zeiger += 1; }, true);
  addEventListener('pointerdown', () => { C.klick += 1; }, true);
  addEventListener('keydown', () => { C.taste += 1; }, true);
  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        const n = e.name;
        if (!/^(pointer|mouse|click|key|wheel)/.test(n)) continue;
        L.ev.push([n, Math.round(e.duration), Math.round(e.processingStart - e.startTime), Math.round(e.processingEnd - e.processingStart)]);
        if (L.ev.length > 300) L.ev.shift();
      }
    }).observe({type: 'event', buffered: true, durationThreshold: 16});
  } catch (e) {}
  try {
    new PerformanceObserver((list) => { for (const e of list.getEntries()) { L.lt += e.duration; L.ltn += 1; } })
      .observe({type: 'longtask', buffered: true});
  } catch (e) {}
  window.__tvLeistung = () => {
    const r = {ev: L.ev.splice(0), alle: Object.assign({}, C), lt_ms: Math.round(L.lt), lt_n: L.ltn, s: Math.round((performance.now() - L.t0) / 100) / 10};
    L.lt = 0; L.ltn = 0; L.t0 = performance.now(); C.zeiger = 0; C.klick = 0; C.taste = 0;
    return JSON.stringify(r);
  };
})();"""

# .35: Ruhig-Stufe 2 (nur zum Messen): Unschärfe-Filter, Animationen und Übergänge aus – auch in den Shadow-Roots der
# HA-Oberfläche (eigene Stilvorlage, die beim Setzen von adoptedStyleSheets immer mit angehängt wird).
RUHIG_JS = r"""(() => {
  if (window.__tvRuhig) return; window.__tvRuhig = 1;
  const css = '*,*::before,*::after{backdrop-filter:none!important;-webkit-backdrop-filter:none!important;' +
    'animation-duration:0s!important;animation-delay:0s!important;animation-iteration-count:1!important;' +
    'transition-duration:0s!important;transition-delay:0s!important}';
  let S;
  try { S = new CSSStyleSheet(); S.replaceSync(css); } catch (e) { return; }
  const add = (root) => { try { const a = root.adoptedStyleSheets; if (!a.includes(S)) root.adoptedStyleSheets = [...a, S]; } catch (e) {} };
  for (const P of [ShadowRoot.prototype, Document.prototype]) {
    const d = Object.getOwnPropertyDescriptor(P, 'adoptedStyleSheets');
    if (d && d.set && d.get) {
      Object.defineProperty(P, 'adoptedStyleSheets', {configurable: true, enumerable: d.enumerable,
        get() { return d.get.call(this); }, set(v) { d.set.call(this, (v || []).includes(S) ? v : [...(v || []), S]); }});
    }
  }
  const att = Element.prototype.attachShadow;
  Element.prototype.attachShadow = function (i) { const r = att.call(this, i); add(r); return r; };
  const walk = (n) => { if (n.shadowRoot) { add(n.shadowRoot); n.shadowRoot.querySelectorAll('*').forEach(walk); } };
  add(document);
  document.querySelectorAll('*').forEach(walk);
})();"""

# .36: Raum-Pop-up öffnen und schließen wie die Grundriss-Karte und dabei messen, was der Browser tut (siehe Kopftext).
# .37h Moonlight (nur mit MOONLIGHT=1): großer LG-artiger Zeiger (pink mit weißem Rand) – auch in den Shadow-Roots von HA
# (Lit setzt adoptedStyleSheets selbst, deshalb hängt der Setter unsere Regel immer an) – und Programm hoch/runter als
# schneller Wechsel: Bild auf (PageUp) → Loxone, Bild ab (PageDown) → Home Assistant. Nicht druckbare Tasten (key länger als
# ein Zeichen) gehen zum Nachsehen ins Protokoll; Buchstaben/Ziffern nie.
MOONLIGHT_JS = r"""(() => {
  if (window.__tvMoon) { return; }
  window.__tvMoon = 1;
  const svg = "<svg xmlns='http://www.w3.org/2000/svg' width='38' height='46' viewBox='0 0 38 46'>" +
    "<path d='M3 3 L3 37 L12 29 L18 43 L24 40 L18 27 L31 27 Z' fill='%23e6006e' stroke='white' stroke-width='3' stroke-linejoin='round'/></svg>";
  const css = "*, *::before, *::after { cursor: url(\"data:image/svg+xml," + svg.replace(/"/g, "'") + "\") 3 3, default !important; }";
  let sheet = null;
  try { sheet = new CSSStyleSheet(); sheet.replaceSync(css); } catch (e) {}
  const add = (root) => { try { if (sheet && root.adoptedStyleSheets.indexOf(sheet) < 0) { root.adoptedStyleSheets = root.adoptedStyleSheets.concat([sheet]); } } catch (e) {} };
  if (sheet) {
    const d = Object.getOwnPropertyDescriptor(ShadowRoot.prototype, 'adoptedStyleSheets');
    if (d && d.set) {
      Object.defineProperty(ShadowRoot.prototype, 'adoptedStyleSheets', { configurable: true, enumerable: d.enumerable,
        get() { return d.get.call(this); },
        set(v) { const a = Array.from(v || []); if (a.indexOf(sheet) < 0) { a.push(sheet); } d.set.call(this, a); } });
    }
    const att = Element.prototype.attachShadow;
    Element.prototype.attachShadow = function (o) { const r = att.call(this, o); add(r); return r; };
    const doc = () => add(document);
    if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', doc); } else { doc(); }
    /* schon vorhandene Shadow-Roots (Skript kam nach dem Laden) */
    const walk = (n) => { if (n.shadowRoot) { add(n.shadowRoot); walk(n.shadowRoot); } for (const c of n.children || []) { walk(c); } };
    try { walk(document.documentElement); } catch (e) {}
  }
  const melde = (o) => { try { if (window.__tvWechsel) { window.__tvWechsel(JSON.stringify(o)); } } catch (e) {} };
  window.addEventListener('keydown', (e) => {
    /* Angepasstes Moonlight (Repo-Ordner moonlight/): Blau = F13, Grün = F14, Wiedergabe = F15, Stopp = F16, Pause = F17
       (Sunshine verwirft unter Linux die Medientasten; die werden trotzdem erkannt, falls sie einmal ankommen) */
    /* e.code statt e.key: Unter X11 heißt F13 als Zeichen „XF86Tools“ und F14 „XF86Launch5“, der Tastencode bleibt F13/F14 */
    const fb = ['F13', 'F14', 'F15', 'F16', 'F17', 'MediaPlayPause', 'MediaStop'].find((k) => e.code === k || e.key === k);
    if (fb) {
      e.preventDefault(); e.stopImmediatePropagation();
      if (!e.repeat) { melde({ fernbedienung: fb }); }
      return;
    }
    if (e.key === 'PageUp' || e.key === 'PageDown') {
      e.preventDefault(); e.stopImmediatePropagation();
      if (!e.repeat) { melde({ richtung: e.key === 'PageUp' ? 1 : -1 }); }
    } else if (e.key === 'Escape' && !e.repeat && location.port === '8123' && !(location.hash && location.hash.length > 1)) {
      /* .37o: Zurück am Fernseher = Escape. Ohne Pop-up und ohne offenen HA-Dialog eine Seite zurück (z. B. aus /tv-dashboard/ranch) */
      const ha = document.querySelector('home-assistant');
      const r = ha && ha.shadowRoot;
      const dialog = r && Array.from(r.children).some((c) => /dialog/.test(c.localName));
      /* .40: nicht selbst history.back() – das führte von der Startseite auf die leere Ruheseite (about:blank). Der Streamer
         geht zurück wie der Zurück-Knopf: nie hinter die Startseite, leere Seiten und Fehlerseiten übersprungen. */
      if (!dialog) { setTimeout(() => { if (!(location.hash && location.hash.length > 1)) melde({ zurueck: 1 }); }, 120); }
    } else if (e.key && e.key.length > 1) {
      melde({ taste: e.key, code: e.code });
    }
  }, true);
})()"""

POPUP_JS = r"""(async (hash, ms) => {
  const raf = () => new Promise((r) => requestAnimationFrame(() => r(performance.now())));
  const pause = (t) => new Promise((r) => setTimeout(r, t));
  const datei = (u) => { const t = String(u || '').split('?')[0].split('/'); return t[t.length - 1] || '(Seite)'; };
  async function messen(tun, dauer) {
    const lf = [], lt = [];
    let o1 = null, o2 = null, bilder = 0, aus = false;
    try { o1 = new PerformanceObserver((l) => { lf.push(...l.getEntries()); }); o1.observe({type: 'long-animation-frame'}); } catch (e) { o1 = null; }
    try { o2 = new PerformanceObserver((l) => { lt.push(...l.getEntries()); }); o2.observe({type: 'longtask'}); } catch (e) { o2 = null; }
    await raf();
    (function zaehl() { if (aus) return; bilder += 1; requestAnimationFrame(zaehl); })();
    const t0 = performance.now();
    tun();
    const t1 = await raf();
    await pause(dauer);
    aus = true;
    for (const o of [o1, o2]) { if (o) { try { (o === o1 ? lf : lt).push(...o.takeRecords()); o.disconnect(); } catch (e) {} } }
    const f = lf.filter((e) => e.startTime + e.duration >= t0);
    const k = lt.filter((e) => e.startTime + e.duration >= t0);
    const sk = {};
    let block = 0, stil = 0, skript = 0, erzw = 0, ende = 0;
    for (const e of f) {
      block += e.blockingDuration || 0;
      if (e.styleAndLayoutStart) { stil += Math.max(0, e.startTime + e.duration - e.styleAndLayoutStart); }
      ende = Math.max(ende, e.startTime + e.duration - t0);
      for (const x of (e.scripts || [])) {
        const n = datei(x.sourceURL) + ' ' + (x.sourceFunctionName || '?') + ' [' + (x.invokerType || '') + ']';
        sk[n] = (sk[n] || 0) + x.duration;
        skript += x.duration;
        erzw += x.forcedStyleAndLayoutDuration || 0;
      }
    }
    const top = Object.keys(sk).sort((a, b) => sk[b] - sk[a]).slice(0, 6).map((n) => [n.slice(0, 90), Math.round(sk[n])]);
    return {erstes_bild_ms: Math.round(t1 - t0), lange_bilder_n: f.length,
      lange_bilder_ms: Math.round(f.reduce((a, e) => a + e.duration, 0)), blockiert_ms: Math.round(block),
      stil_layout_ms: Math.round(stil), skripte_ms: Math.round(skript), erzwungenes_layout_ms: Math.round(erzw),
      ruhig_ab_ms: Math.round(Math.max(ende, t1 - t0)), lange_aufgaben_ms: Math.round(k.reduce((a, e) => a + e.duration, 0)),
      bilder_s: Math.round(bilder * 1000 / Math.max(1, performance.now() - t0)), loaf: !!o1, top: top};
  }
  if (location.hash && location.hash.length > 1) { return JSON.stringify({hash: hash, fehler: 'schon ein Pop-up offen: ' + location.hash}); }
  const auf = await messen(() => {
    history.pushState(null, '', hash);
    window.dispatchEvent(new CustomEvent('location-changed', {detail: {replace: false}}));
  }, ms);
  const offen = location.hash === hash;
  await pause(800);
  let zu = null;
  if (offen) { zu = await messen(() => { history.back(); }, 1500); }
  return JSON.stringify({hash: hash, offen: offen, auf: auf, zu: zu, danach: location.hash || ''});
})(%s, %d)"""


def cpu_gruppe(pid, comm):
    if comm.startswith("chrom"):
        try:
            with open("/proc/%s/cmdline" % pid, "rb") as fh:
                args = fh.read().split(b"\0")
        except OSError:
            return "chromium"
        for a in args:
            if a.startswith(b"--type="):
                t = a[7:].decode(errors="replace")
                return {"renderer": "chromium_seiten", "gpu-process": "chromium_zeichnen"}.get(t, "chromium_rest")
        return "chromium_rest"
    for anfang, name in (("ffmpeg", "ffmpeg"), ("go2rtc", "go2rtc"), ("Xvfb", "xvfb"), ("pulseaudio", "ton"), ("python", "streamer")):
        if comm.startswith(anfang):
            return name
    return "sonst"


CPU_LETZT = {"t": 0.0, "proc": {}, "stat": None}


def cpu_info():
    """CPU je Prozessgruppe dieses Containers in % EINES Kerns seit dem letzten Aufruf; dazu die ganze VM in % ALLER Kerne
    und „steal“ (Zeit, in der die VM rechnen wollte, Proxmox ihr aber keinen Kern gab)."""
    now = time.monotonic()
    hz = os.sysconf("SC_CLK_TCK")
    proc = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open("/proc/%s/stat" % pid) as fh:
                txt = fh.read()
            r = txt.rfind(")")
            comm = txt[txt.find("(") + 1:r]
            f = txt[r + 2:].split()
            proc[pid] = (cpu_gruppe(pid, comm), int(f[11]) + int(f[12]))
        except (OSError, ValueError, IndexError):
            continue
    stat = None
    try:
        with open("/proc/stat") as fh:
            z = [int(x) for x in fh.readline().split()[1:9]]
        stat = (sum(z), z[3] + z[4], z[7])          # gesamt, idle+iowait, steal
    except (OSError, ValueError, IndexError):
        pass
    out = {}
    last = CPU_LETZT
    dt = now - last["t"] if last["t"] else 0
    if dt > 0.5:
        g = {}
        for pid, (grp, ticks) in proc.items():
            prev = last["proc"].get(pid)
            if prev and prev[0] == grp and ticks >= prev[1]:
                g[grp] = g.get(grp, 0) + ticks - prev[1]
        out = {k: round(v * 100.0 / hz / dt, 1) for k, v in sorted(g.items()) if v > 0}
        if stat and last["stat"] and stat[0] > last["stat"][0]:
            tot = stat[0] - last["stat"][0]
            out["vm_gesamt"] = round(100.0 * (tot - (stat[1] - last["stat"][1])) / tot, 1)
            out["vm_steal"] = round(100.0 * (stat[2] - last["stat"][2]) / tot, 1)
        out["kerne"] = os.cpu_count()
    CPU_LETZT.update(t=now, proc=proc, stat=stat)
    return out


def leistung_zusammen(roh):
    """Einträge der letzten 2 min zusammenfassen: je Art (zeiger, klick, taste) Anzahl, Median, 90 %, Höchstwert der Zeit
    Eingabe → nächstes Bild; dazu lange Aufgaben in ms je s."""
    jetzt = time.time()
    roh[:] = [x for x in roh if jetzt - x[0] <= 120]
    arten = {}
    lt_ms = lt_s = 0.0
    alle = {}
    for t, d in roh:
        for k, v in (d.get("alle") or {}).items():
            alle[k] = alle.get(k, 0) + int(v or 0)
        for e in d.get("ev", []):
            n = str(e[0])
            art = "taste" if n.startswith("key") else ("klick" if n in ("click", "pointerdown", "pointerup", "mousedown", "mouseup") else "zeiger")
            arten.setdefault(art, []).append((int(e[1]), int(e[2]), int(e[3])))
        lt_ms += d.get("lt_ms", 0)
        lt_s += d.get("s", 0)
    out = {}
    for art, l in arten.items():
        dur = sorted(x[0] for x in l)
        proc = sorted(x[2] for x in l)
        out[art] = {"n": len(dur), "median_ms": dur[len(dur) // 2], "p90_ms": dur[min(len(dur) - 1, int(len(dur) * 0.9))],
                    "max_ms": dur[-1], "verarbeitung_median_ms": proc[len(proc) // 2]}
    for k, v in alle.items():
        if v:
            out.setdefault(k, {"n": 0})["alle"] = v     # alle Eingaben; n = davon mit ≥ 16 ms bis zum Bild
    if lt_s > 0:
        out["lange_aufgaben_ms_s"] = round(lt_ms / lt_s, 1)
    return out


async def messwerte(app):
    """.35: alle 10 s CPU je Prozessgruppe und – solange jemand zuschaut – die Reaktion im sichtbaren Reiter abholen."""
    cdp, video = app["cdp"], app["video"]
    roh = []
    cpu_info()
    while True:
        await asyncio.sleep(10)
        try:
            app["cpu"] = cpu_info()
        except Exception as e:
            log.warning("CPU-Messung: %s", e)
        if not video.viewers or not cdp.sess:
            continue
        try:
            r = await cdp.call("Runtime.evaluate", {"expression": "window.__tvLeistung ? window.__tvLeistung() : ''",
                                                    "returnByValue": True}, sess=cdp.sess)
            v = (((r or {}).get("result") or {}).get("value")) or ""
            if v:
                d = json.loads(v)
                d["reiter"] = cdp.tab_name()
                roh.append((time.time(), d))
            app["leistung"] = leistung_zusammen(roh)
        except Exception as e:
            log.info("Leistung nicht lesbar: %s", e)


class Cdp:
    def __init__(self):
        self.out = asyncio.Queue()
        self.n = 0
        self.wait = {}
        self.ws = None
        self.sess = None
        self.target = None
        self.url = ""
        self.buttons = 0
        self.tabs = {}          # feste Reiter: „home“ (Home Assistant) und je Ziel aus LINKS (z. B. „loxone“) → targetId
        self.sessions = {}      # targetId → sessionId (alle Reiter bleiben verbunden)
        self.urls = {}          # targetId → aktuelle Adresse
        self.expect_new = 0     # gleich kommt ein selbst angelegter Reiter (nicht automatisch dorthin wechseln)
        self.parked = None      # gemerkte Adresse des HA-Reiters, solange er ruht
        self.feld = {"an": False}   # Textfeld mit Fokus im sichtbaren Reiter (.27) – für neu verbundene Empfangsseiten
        self.on_feld = None         # Rückruf: Textfeld auf/zu → an die Empfangsseiten
        self.on_hint = None         # Rückruf: kurzer Hinweis am Fernseher (.30)
        self.zugang_t = 0           # zuletzt ausgefüllt (.30, höchstens alle 5 s)
        self.zugang_hinweis = False # Hinweis „einmal anmelden“ schon gezeigt
        self.ruhig = CFG["ruhig"]   # .35: 0 normal, 1 weniger Bewegung, 2 auch ohne Unschärfe/Animationen
        self.popup_ergebnisse = []  # .36: Pop-up-Messungen (je Eintrag n, zeit, Ergebnis)
        self.popup_n = 0
        self.popup_laeuft = False

    async def run(self):
        while True:
            try:
                async with ClientSession() as s:
                    async with s.get("http://127.0.0.1:%d/json/version" % CFG["cdp_port"]) as r:
                        info = await r.json(content_type=None)
                    async with s.ws_connect(info["webSocketDebuggerUrl"], max_msg_size=0) as ws:
                        self.ws = ws
                        self.tabs, self.sessions, self.urls, self.expect_new, self.parked = {}, {}, {}, 0, None
                        writer = asyncio.ensure_future(self._writer(ws))
                        reader = asyncio.ensure_future(self._reader(ws))
                        await self.call("Target.setDiscoverTargets", {"discover": True})
                        await self.pick()
                        log.info("Chromium-Steuerung verbunden")
                        await reader
                        writer.cancel()
            except Exception as e:   # Chromium startet noch oder ist abgestürzt
                if self.ws:
                    log.warning("Chromium-Steuerung getrennt: %s", e)
            self.ws = self.sess = None
            for f in self.wait.values():
                if not f.done():
                    f.set_exception(ConnectionError("CDP getrennt"))
            self.wait = {}
            await asyncio.sleep(1)

    async def _writer(self, ws):
        while True:
            await ws.send_str(await self.out.get())

    async def _reader(self, ws):
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                break
            m = json.loads(msg.data)
            if "id" in m:
                f = self.wait.pop(m["id"], None)
                if f and not f.done():
                    f.set_result(m.get("result", {"error": m.get("error")}))
                continue
            meth, p = m.get("method"), m.get("params", {})
            if meth == "Target.targetCreated" and p["targetInfo"]["type"] == "page":
                ti = p["targetInfo"]
                self.urls[ti["targetId"]] = ti.get("url", "")
                if self.expect_new > 0:
                    self.expect_new -= 1                             # selbst angelegter Reiter – show() übernimmt
                else:
                    asyncio.ensure_future(self.attach(ti["targetId"]))   # von einer Seite geöffnetes Fenster → dorthin steuern
            elif meth == "Target.targetInfoChanged":
                ti = p["targetInfo"]
                self.urls[ti["targetId"]] = ti.get("url", "")
                if ti["targetId"] == self.target:
                    self.url = self.urls[ti["targetId"]]
            elif meth == "Target.targetDestroyed":
                self.forget(p.get("targetId"))
            elif meth == "Target.detachedFromTarget":
                self.forget(next((t for t, sid in self.sessions.items() if sid == p.get("sessionId")), None))
            elif meth == "Runtime.bindingCalled" and p.get("name") == "__tvTastatur":
                if m.get("sessionId") == self.sess:        # nur der sichtbare Reiter
                    try:
                        d = json.loads(p.get("payload") or "{}")
                    except ValueError:
                        d = {}
                    self.set_feld(d)
            elif meth == "Runtime.bindingCalled" and p.get("name") == "__tvWechsel":   # .37h
                if m.get("sessionId") == self.sess:
                    try:
                        d = json.loads(p.get("payload") or "{}")
                    except ValueError:
                        d = {}
                    if d.get("richtung") in (1, -1):    # .37j: reihum durch Home Assistant und alle LINKS (Loxone, später z. B. Frigate)
                        folge = ["home"] + list(CFG["links"])
                        jetzt = self.tab_name() or "home"
                        i = folge.index(jetzt) if jetzt in folge else 0
                        ziel = folge[(i + d["richtung"]) % len(folge)]
                        log.info("Moonlight: Taste Bild %s – %s", "auf" if d["richtung"] > 0 else "ab", ziel)
                        asyncio.ensure_future(self.command("startansicht" if ziel == "home" else "link:" + ziel))   # .37o: HA immer mit Startansicht
                    elif d.get("zurueck"):              # .40: Zurück-Taste aus Moonlight – geschützter Weg wie der Zurück-Knopf
                        log.info("Moonlight: Taste Zurück")
                        asyncio.ensure_future(self.back())
                    elif d.get("fernbedienung") in FERNBEDIENUNG:
                        name = FERNBEDIENUNG[d["fernbedienung"]]
                        log.info("Moonlight: Taste %s", name)
                        if name == "blue":      # wie im Browser: Home Assistant, ist man dort schon: Startseite
                            asyncio.ensure_future(self.command("home"))
                        elif name == "green" and CFG["links"]:    # erster zusätzlicher Reiter (z. B. Loxone)
                            asyncio.ensure_future(self.command("link:" + next(iter(CFG["links"]))))
                        asyncio.ensure_future(ha_taste(name))   # jede Taste auch als Ereignis tv_streamer_key in HA
                    elif d.get("taste"):
                        log.info("Moonlight: Taste %s (%s)", str(d.get("taste"))[:24], str(d.get("code") or "")[:24])
            elif meth == "Runtime.bindingCalled" and p.get("name") == "__tvZugang":
                asyncio.ensure_future(self.zugang(m.get("sessionId"), p.get("payload") or ""))
            elif meth == "Page.frameNavigated" and m.get("sessionId") and not (p.get("frame") or {}).get("parentId"):
                asyncio.ensure_future(self.bindings(m.get("sessionId")))
            elif meth == "Page.javascriptDialogOpening":   # Browser-Dialoge sind fernbedient nicht klickbar
                ok = p.get("type") in ("alert", "beforeunload")   # Rückfragen (confirm/prompt) lieber abbrechen
                log.info("Dialog %s „%s“ → %s", p.get("type"), str(p.get("message", ""))[:80], "OK" if ok else "Abbrechen")
                self.send("Page.handleJavaScriptDialog", {"accept": ok}, sess=m.get("sessionId"))

    def set_feld(self, d):
        """Textfeld im sichtbaren Reiter bekommt/verliert den Fokus → Empfangsseiten informieren (Inhalt nie ins Protokoll)."""
        d = {"an": bool(d.get("an")), "typ": str(d.get("typ") or "text")[:10], "titel": str(d.get("titel") or "")[:80],
             "wert": "" if d.get("typ") == "password" else str(d.get("wert") or "")[:500]}
        if d["an"] or self.feld.get("an"):
            log.info("Textfeld im Browser %s – Eingabefeld am Fernseher %s", ("„%s“ (%s)" % (d["titel"], d["typ"])) if d["an"] else "verlassen",
                     "an" if d["an"] else "aus")
        self.feld = d
        if self.on_feld:
            self.on_feld(d)

    async def bindings(self, sid):
        """Bindungen nach jedem Seitenwechsel neu setzen (.30): Ohne Runtime.enable übernimmt Chromium sie nicht in neue
        Seiten – lokal nachgewiesen (nach dem Laden einer neuen Seite fehlte __tvZugang); ebenso fehlte __tvTastatur nach dem
        Ruhen des HA-Reiters (leere Seite und zurück), dann kam am Fernseher kein Eingabefeld."""
        tid = next((t for t, s in self.sessions.items() if s == sid), None)
        names = ["__tvTastatur"]
        if CFG["moonlight"]:
            names.append("__tvWechsel")
        if CFG["zugang_reiter"] and tid and tid == self.tabs.get(CFG["zugang_reiter"]):
            names.append("__tvZugang")
        for n in names:
            try:
                await self.call("Runtime.addBinding", {"name": n}, sess=sid)
            except Exception:
                pass

    def hint(self, text):
        """Kurzer Hinweis unten auf dem Fernseher (.30), z. B. wenn eine Taste bewusst nichts tut."""
        log.info("Hinweis am Fernseher: %s", text)
        if self.on_hint:
            self.on_hint(text)

    async def target_url(self):
        """Adresse des sichtbaren Reiters, frisch von Chromium (die gemerkte kann veraltet oder leer sein)."""
        if not self.target:
            return ""
        try:
            info = await self.call("Target.getTargetInfo", {"targetId": self.target})
            url = ((info or {}).get("targetInfo") or {}).get("url", "")
        except Exception:
            url = ""
        if url:
            self.url = self.urls[self.target] = url
        return url or self.url

    def zugang_datei(self):
        return os.path.join(os.path.dirname(CFG["profile"].rstrip("/")) or "/data", "zugang-%s.json" % CFG["zugang_reiter"])

    def zugang_lesen(self):
        if not CFG["zugang_reiter"]:
            return None
        try:
            with open(self.zugang_datei(), encoding="utf-8") as fh:
                d = json.load(fh)
            return d if d.get("u") and d.get("p") else None
        except (OSError, ValueError):
            return None

    async def zugang(self, sid, payload):
        """Anmeldung im Loxone-Reiter (.30): nach erfolgreicher Anmeldung merken, auf der leeren Anmeldeseite ausfüllen.
        Nur im festen Reiter ZUGANG_REITER und nur auf dessen Adressen (LINKS bzw. ZUGANG_HOSTS). Benutzer und Kennwort
        liegen nur in der Datei im Volume (0600) – nie im Protokoll, nie in den Meldungen an HA, nie in /api/status."""
        name = CFG["zugang_reiter"]
        tid = self.tabs.get(name) if name else None
        try:
            d = json.loads(payload)
        except ValueError:
            return
        if not tid or self.sessions.get(tid) != sid:
            log.info("Loxone-Anmeldung: Meldung „%s“ aus einem anderen Reiter – nicht beachtet", str(d.get("art"))[:12])
            return
        try:
            info = await self.call("Target.getTargetInfo", {"targetId": tid})
            host = (urlsplit(((info or {}).get("targetInfo") or {}).get("url", "")).hostname or "").lower()
        except Exception:
            host = ""
        eigen = (urlsplit(CFG["links"].get(name, "")).hostname or "").lower()
        if not host or not (host == eigen or any(host.endswith(h) for h in CFG["zugang_hosts"])):
            log.info("Loxone-Anmeldung: Seite auf „%s“ gehört nicht zu Loxone – nicht beachtet", host[:60])
            return
        if d.get("art") == "angemeldet":
            u, p = str(d.get("u") or "")[:200], str(d.get("p") or "")[:200]
            alt = self.zugang_lesen()
            if not u or not p or (alt and alt.get("u") == u and alt.get("p") == p):
                return
            f = self.zugang_datei()
            try:
                fd = os.open(f + ".neu", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump({"u": u, "p": p, "gespeichert": time.strftime("%Y-%m-%d %H:%M")}, fh)
                os.replace(f + ".neu", f)
            except OSError as e:
                log.warning("Loxone-Anmeldung nicht gespeichert: %s", e.strerror or e)
                return
            log.info("Loxone-Anmeldung gespeichert – erscheint die Anmeldeseite wieder, füllt der Streamer sie aus")
            self.hint("%s-Anmeldung gespeichert" % name.capitalize())
        elif d.get("art") == "formular":
            z = self.zugang_lesen()
            if not z:
                if not self.zugang_hinweis:
                    self.zugang_hinweis = True
                    self.hint("Einmal bei %s anmelden – danach füllt der Streamer die Felder selbst aus" % name.capitalize())
                return
            if time.time() - self.zugang_t < 5:
                return
            self.zugang_t = time.time()
            try:
                r = await self.call("Runtime.evaluate", {"expression": FUELLEN_JS % json.dumps({"u": z["u"], "p": z["p"]}),
                                                         "returnByValue": True}, sess=sid)
                res = str((((r or {}).get("result") or {}).get("value")) or "?")
            except Exception as e:
                res = type(e).__name__
            log.info("Loxone-Anmeldeseite: gespeicherte Anmeldung eingetragen (%s)", res[:20])
            if res.endswith("p"):
                self.hint("Anmeldedaten eingetragen – bitte „Anmelden“ klicken")

    def forget(self, tid):
        if not tid:
            return
        self.sessions.pop(tid, None)
        self.urls.pop(tid, None)
        for name in [k for k, t in self.tabs.items() if t == tid]:
            del self.tabs[name]
            if name == "home":
                self.parked = None
        if tid == self.target:
            self.sess = self.target = None
            asyncio.ensure_future(self.pick())

    def send(self, method, params=None, session=True, sess=None):
        if not self.ws:
            return None
        self.n += 1
        m = {"id": self.n, "method": method, "params": params or {}}
        if sess or session:
            sid = sess or self.sess
            if not sid:
                return None
            m["sessionId"] = sid
        self.out.put_nowait(json.dumps(m))
        return self.n

    async def call(self, method, params=None, session=False, timeout=5, sess=None):
        i = self.send(method, params, session, sess)
        if i is None:
            return None
        f = asyncio.get_event_loop().create_future()
        self.wait[i] = f
        try:
            return await asyncio.wait_for(f, timeout)
        finally:
            self.wait.pop(i, None)

    async def pick(self):
        r = await self.call("Target.getTargets")
        pages = [t for t in (r or {}).get("targetInfos", []) if t["type"] == "page" and not t["url"].startswith("devtools:")]
        ids = [t["targetId"] for t in pages]
        for t in pages:
            self.urls.setdefault(t["targetId"], t["url"])
        if not ids:
            return
        if self.tabs.get("home") not in ids:
            self.tabs["home"] = ids[0]          # erster Reiter = Home Assistant (Startseite)
        await self.attach(self.target if self.target in ids else self.tabs["home"])

    async def attach(self, tid):
        """Reiter nach vorn holen; Zeiger und Tasten gehen ab jetzt dorthin."""
        sid = self.sessions.get(tid)
        if not sid:
            r = await self.call("Target.attachToTarget", {"targetId": tid, "flatten": True})
            sid = (r or {}).get("sessionId")
            if not sid:
                return False
            self.sessions[tid] = sid
            await self.call("Page.enable", None, sess=sid)   # für Dialog-Meldungen
            # keine Hinweistexte (.27): für jede künftige Seite dieses Reiters und für die schon geladene
            await self.call("Page.addScriptToEvaluateOnNewDocument", {"source": OHNE_HINWEIS_JS}, sess=sid)
            await self.call("Runtime.evaluate", {"expression": OHNE_HINWEIS_JS}, sess=sid)
            # Textfelder melden (.27): Bindung bleibt über Neuladen erhalten, das Skript kommt in jede neue Seite
            await self.call("Runtime.addBinding", {"name": "__tvTastatur"}, sess=sid)
            await self.call("Page.addScriptToEvaluateOnNewDocument", {"source": TASTATUR_JS}, sess=sid)
            await self.call("Runtime.evaluate", {"expression": TASTATUR_JS}, sess=sid)
            # .35: Reaktion messen (Event Timing) – in jeder künftigen Seite und in der schon geladenen
            await self.call("Page.addScriptToEvaluateOnNewDocument", {"source": PERF_JS}, sess=sid)
            await self.call("Runtime.evaluate", {"expression": PERF_JS}, sess=sid)
            if CFG["moonlight"]:   # .37h: Zeiger und Programm-Tasten für Moonlight
                await self.call("Runtime.addBinding", {"name": "__tvWechsel"}, sess=sid)
                await self.call("Page.addScriptToEvaluateOnNewDocument", {"source": MOONLIGHT_JS}, sess=sid)
                await self.call("Runtime.evaluate", {"expression": MOONLIGHT_JS}, sess=sid)
            await self.ruhig_setzen(sid)
            if CFG["zugang_reiter"] and tid == self.tabs.get(CFG["zugang_reiter"]):   # .30: nur im Loxone-Reiter
                await self.call("Runtime.addBinding", {"name": "__tvZugang"}, sess=sid)
                await self.call("Page.addScriptToEvaluateOnNewDocument", {"source": ZUGANG_JS}, sess=sid)
                await self.call("Runtime.evaluate", {"expression": ZUGANG_JS}, sess=sid)
        if sid != self.sess and self.feld.get("an"):
            self.set_feld({"an": False})            # anderer Reiter vorn → Eingabefeld am Fernseher schließen
        self.sess, self.target = sid, tid
        await self.call("Target.activateTarget", {"targetId": tid})
        if not self.urls.get(tid):
            info = await self.call("Target.getTargetInfo", {"targetId": tid})
            self.urls[tid] = ((info or {}).get("targetInfo") or {}).get("url", "")
        self.url = self.urls.get(tid, "")
        return True

    async def show(self, name, url):
        """Festen Reiter zeigen (beim ersten Mal anlegen). HA und Loxone bleiben beide geladen und angemeldet."""
        tid = self.tabs.get(name)
        if tid and tid in self.urls:
            await self.attach(tid)
            return
        self.expect_new += 1
        try:
            r = await self.call("Target.createTarget", {"url": url})
        finally:
            await asyncio.sleep(0.2)
            self.expect_new = 0
        tid = (r or {}).get("targetId")
        if tid:
            self.tabs[name] = tid
            await self.attach(tid)
            log.info("Reiter „%s“ angelegt: %s", name, url)

    def tab_name(self):
        return next((k for k, t in self.tabs.items() if t == self.target), "")

    async def ruhig_setzen(self, sid):
        """.35: Ruhig-Stufe in einem Reiter setzen (1: prefers-reduced-motion, 2: dazu ohne Unschärfe/Animationen)."""
        feat = [{"name": "prefers-reduced-motion", "value": "reduce" if self.ruhig >= 1 else ""}]
        await self.call("Emulation.setEmulatedMedia", {"features": feat}, sess=sid)
        if self.ruhig >= 2:
            if not getattr(self, "ruhig_ids", None):
                self.ruhig_ids = {}
            if sid not in self.ruhig_ids:
                r = await self.call("Page.addScriptToEvaluateOnNewDocument", {"source": RUHIG_JS}, sess=sid)
                self.ruhig_ids[sid] = (r or {}).get("identifier")
            await self.call("Runtime.evaluate", {"expression": RUHIG_JS}, sess=sid)
        elif getattr(self, "ruhig_ids", None) and self.ruhig_ids.get(sid):
            await self.call("Page.removeScriptToEvaluateOnNewDocument", {"identifier": self.ruhig_ids.pop(sid)}, sess=sid)

    async def popup_messen(self, hashes, ms):
        """.36: Raum-Pop-ups nacheinander öffnen, messen, schließen (nur HA-Reiter, nur Adressen #name)."""
        if self.popup_laeuft:
            log.info("Pop-up-Messung läuft schon")
            return
        self.popup_laeuft = True
        try:
            for h in hashes:
                if self.tab_name() != "home" or not self.sess:
                    log.info("Pop-up-Messung abgebrochen: HA-Reiter nicht vorn")
                    break
                url = await self.target_url()
                if not url.startswith(CFG["start_url"].split("/", 3)[0] + "//" + CFG["start_url"].split("/", 3)[2] + "/"):
                    log.info("Pop-up-Messung abgebrochen: keine HA-Seite (%s)", url[:60])
                    break
                r = await self.call("Runtime.evaluate", {"expression": POPUP_JS % (json.dumps(h), ms), "awaitPromise": True,
                                                         "returnByValue": True}, sess=self.sess, timeout=ms / 1000.0 + 15)
                v = (((r or {}).get("result") or {}).get("value")) or ""
                try:
                    d = json.loads(v) if v else {"hash": h, "fehler": "keine Antwort"}
                except ValueError:
                    d = {"hash": h, "fehler": "unlesbar"}
                self.popup_n += 1
                d.update(n=self.popup_n, zeit=time.strftime("%H:%M:%S"), ruhig=self.ruhig)
                self.popup_ergebnisse = (self.popup_ergebnisse + [d])[-40:]
                a = d.get("auf") or {}
                log.info("Pop-up %s: erstes Bild %s ms, lange Bilder %s ms, ruhig ab %s ms", h, a.get("erstes_bild_ms"),
                         a.get("lange_bilder_ms"), a.get("ruhig_ab_ms"))
                await asyncio.sleep(1.0)
        except Exception as e:
            log.warning("Pop-up-Messung: %s", e)
        finally:
            self.popup_laeuft = False

    async def probe(self, art, n, x, y):
        """.35: Testeingaben für die Reaktionsmessung (Event Timing misst sie wie echte)."""
        for _ in range(max(1, min(10, n))):
            if art == "maus":
                for px, py in ((x, y), (min(0.98, x + 0.15), y)):
                    self.input({"t": "m", "x": px, "y": py})
                    await asyncio.sleep(1.5)
            else:
                for key, code, vk in (("ArrowRight", "ArrowRight", 39), ("ArrowLeft", "ArrowLeft", 37)):
                    self.input({"t": "k", "d": 1, "key": key, "code": code, "vk": vk})
                    self.input({"t": "k", "d": 0, "key": key, "code": code, "vk": vk})
                    await asyncio.sleep(2.5)
        log.info("Probe „%s“ ×%d fertig", art, n)

    def xy(self, m):
        x = min(1.0, max(0.0, float(m.get("x", 0))))
        y = min(1.0, max(0.0, float(m.get("y", 0))))
        return x * CFG["width"] / CFG["zoom"], y * CFG["height"] / CFG["zoom"]

    def input(self, m):
        t = m.get("t")
        btn_names = ["left", "middle", "right"]
        if t in ("m", "d", "u", "w"):
            x, y = self.xy(m)
            if t == "m":
                self.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "buttons": self.buttons,
                                                       "button": "left" if self.buttons & 1 else "none"})
            elif t == "w":
                self.send("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": x, "y": y,
                                                       "deltaX": float(m.get("dx", 0)), "deltaY": float(m.get("dy", 0))})
            else:
                b = int(m.get("b", 0)) if int(m.get("b", 0)) in (0, 1, 2) else 0
                bit = (1, 4, 2)[b]
                self.buttons = (self.buttons | bit) if t == "d" else (self.buttons & ~bit)
                self.send("Input.dispatchMouseEvent", {"type": "mousePressed" if t == "d" else "mouseReleased",
                                                       "x": x, "y": y, "button": btn_names[b], "buttons": self.buttons, "clickCount": 1})
        elif t == "k":
            p = {"key": str(m.get("key", ""))[:32], "code": str(m.get("code", ""))[:32],
                 "windowsVirtualKeyCode": int(m.get("vk", 0)), "nativeVirtualKeyCode": int(m.get("vk", 0)),
                 "modifiers": int(m.get("mod", 0))}
            text = str(m.get("text", ""))[:4]
            if m.get("d"):
                p["type"] = "keyDown" if text else "rawKeyDown"
                if text:
                    p["text"] = p["unmodifiedText"] = text
            else:
                p["type"] = "keyUp"
            self.send("Input.dispatchKeyEvent", p)
        elif t == "txt":
            self.send("Input.insertText", {"text": str(m.get("s", ""))[:500]})
        elif t == "c":
            asyncio.ensure_future(self.command(str(m.get("c", "")), m))

    async def back(self):
        """Zurück wie im Browser (.28) – aber nie hinter die Startseite: dort bleibt die Taste ohne Wirkung, außer ein Pop-up
        (#raum) oder ein HA-Dialog ist offen (den schließt sie). Leere Seiten (about:blank vom Ruhen) und Fehlerseiten im
        Verlauf werden übersprungen. Im Loxone-Reiter (und in Fenstern, die eine Seite geöffnet hat) führt Zurück von der
        ersten Seite zu Home Assistant."""
        try:
            r = await self.call("Page.getNavigationHistory", None, session=True)
            o = await self.call("Runtime.evaluate", {"returnByValue": True, "expression":
                                "(function () { var s = history.state; return location.hash.length > 1 || !!(s && s.dialog && s.open); })()"},
                                session=True)
        except Exception:
            r = o = None
        if not isinstance(r, dict) or not r.get("entries"):
            log.info("Fernseher-Zurück: Verlauf nicht lesbar – Browser-Zurück")
            self.send("Runtime.evaluate", {"expression": "history.back()"})
            return
        entries, i = r["entries"], int(r.get("currentIndex", len(r["entries"]) - 1))
        cur = str(entries[i].get("url", "")) if 0 <= i < len(entries) else (self.url or "")
        offen = bool((((o or {}).get("result") or {}).get("value")))
        if offen and i > 0:                   # Pop-up/Dialog schließen
            self.send("Runtime.evaluate", {"expression": "history.back()"})
            return
        j = i - 1                             # vorheriger brauchbarer Eintrag
        while j >= 0 and (not str(entries[j].get("url", "")).startswith(("http://", "https://")) or entries[j].get("url") == cur):
            j -= 1
        if self.target and self.target == self.tabs.get("home"):
            s, u = urlsplit(CFG["start_url"]), urlsplit(cur)
            # Startseite ohne Zusatz in der Adresse (HA öffnet Dialoge auch als ?more-info-entity-id=…) → bleibt
            if (u.netloc, u.path.rstrip("/"), u.query, u.fragment) == (s.netloc, s.path.rstrip("/"), s.query, s.fragment):
                log.info("Fernseher-Zurück: schon auf der Startseite – bleibt")
                self.hint("Schon auf der Startseite")
                return
            ziel = urlsplit(str(entries[j].get("url", ""))) if j >= 0 else None
            if not ziel or ziel.netloc != s.netloc or ziel.path.startswith("/auth/"):
                log.info("Fernseher-Zurück: kein Eintrag davor – zur Startseite")
                self.navigate(CFG["start_url"])
                return
        elif j < 0:
            log.info("Fernseher-Zurück: erste Seite im Reiter „%s“ – zu Home Assistant", self.tab_name() or "Fenster")
            await self.show("home", CFG["start_url"])
            return
        if j == i - 1:
            self.send("Runtime.evaluate", {"expression": "history.back()"})
        else:
            log.info("Fernseher-Zurück: %d Einträge übersprungen (leere Seite, Fehlerseite oder dieselbe Adresse)", i - 1 - j)
            self.send("Page.navigateToHistoryEntry", {"entryId": entries[j]["id"]})

    async def command(self, c, m=None):
        if c == "back":
            await self.back()
        elif c == "forward":
            self.send("Runtime.evaluate", {"expression": "history.forward()"})
        elif c == "reload":
            name = self.tab_name()
            if name and name in CFG["kein_neuladen"]:   # .30: Loxone meldet beim Neuladen ab (Test 24.10. 02:17)
                self.hint("%s wird nicht neu geladen – das würde abmelden" % name.capitalize())
                return
            self.send("Page.reload", {"ignoreCache": False})
        elif c == "home":
            if self.target and self.target == self.tabs.get("home"):
                self.navigate(CFG["start_url"])          # schon im HA-Reiter → zur Startseite
            else:
                await self.show("home", CFG["start_url"])
        elif c.startswith("link:") and c[5:] in CFG["links"]:
            name = c[5:]
            if self.target and self.target == self.tabs.get(name):
                url = await self.target_url()      # .30: frisch nachsehen – nur eine leere oder Fehlerseite neu laden
                if not url or url.startswith(("about:", "chrome-error:")):
                    self.navigate(CFG["links"][name])
                else:
                    self.hint("%s ist schon offen" % name.capitalize())
            else:
                await self.show(name, CFG["links"][name])
        elif c == "loxone_zuruecksetzen" and "loxone" in CFG["links"]:   # .37h: Startraum/Ambient-Modus vergessen (Anmeldung bleibt gespeichert)
            u = CFG["links"]["loxone"]
            origin = "/".join(u.split("/")[:3])
            await self.call("Storage.clearDataForOrigin", {"origin": origin,
                            "storageTypes": "local_storage,indexeddb,cache_storage,service_workers,websql,file_systems"})
            log.info("Loxone: Speicher der Seite %s geleert (Startseite zurückgesetzt)", origin)
            tid = self.tabs.get("loxone")
            if tid and self.sessions.get(tid):
                self.send("Page.navigate", {"url": u}, sess=self.sessions[tid])
        elif c == "startansicht":                      # .37o: HA-Reiter nach vorn und zur Startansicht – ohne Neuladen (HA-interner Seitenwechsel)
            await self.show("home", CFG["start_url"])
            pfad = "/" + CFG["start_url"].split("/", 3)[3] if CFG["start_url"].count("/") >= 3 else "/"
            ziel = json.dumps(pfad)
            self.send("Runtime.evaluate", {"expression": "(() => { const p = %s; if (location.pathname + location.search + location.hash !== p) {"
                      " history.pushState(null, '', p); window.dispatchEvent(new CustomEvent('location-changed', {detail: {replace: false}})); } })()" % ziel})
        elif c == "zeige_home":                        # .32: HA-Reiter nach vorn, ohne neu zu laden (Empfangsseite beim Öffnen)
            if not (self.target and self.target == self.tabs.get("home")):
                log.info("Empfangsseite geöffnet – HA-Reiter nach vorn (war „%s“)", self.tab_name() or "?")
                await self.show("home", CFG["start_url"])
        elif c == "probe":                             # .35: Testeingaben für die Reaktionsmessung
            m = m or {}
            asyncio.ensure_future(self.probe(str(m.get("art", "pfeil")), int(m.get("n", 3)),
                                             float(m.get("x", 0.5)), float(m.get("y", 0.5))))
        elif c == "popup":                             # .36: Raum-Pop-ups öffnen und messen
            m = m or {}
            hs = [h.strip() for h in str(m.get("hash", "")).split(",")]
            hs = [h for h in hs if re.match(r"^#[a-z0-9_]{1,40}$", h)][:20]
            ms = max(1500, min(6000, int(m.get("ms", 3000))))
            if hs:
                asyncio.ensure_future(self.popup_messen(hs, ms))
        elif c == "ruhig":                             # .35: Ruhig-Stufe 0/1/2 in allen Reitern
            self.ruhig = max(0, min(2, int((m or {}).get("stufe", 0))))
            for sid in list(self.sessions.values()):
                await self.ruhig_setzen(sid)
            log.info("Ruhig-Stufe %d", self.ruhig)
        elif c == "zugang_vergessen":                  # .30: gespeicherte Loxone-Anmeldung löschen
            try:
                os.remove(self.zugang_datei())
                log.info("Loxone-Anmeldung gelöscht")
            except OSError:
                pass
        elif c in ("zoomin", "zoomout", "zoomreset"):   # echter Browser-Zoom (merkt sich Chromium je Seite)
            key = {"zoomin": "ctrl+plus", "zoomout": "ctrl+minus", "zoomreset": "ctrl+0"}[c]
            try:
                p = await asyncio.create_subprocess_exec("xdotool", "key", "--clearmodifiers", key,
                                                         env=dict(os.environ, DISPLAY=CFG["display"]))
                await p.wait()
            except FileNotFoundError:
                log.warning("xdotool fehlt – Zoom per Taste nicht möglich")

    def navigate(self, url):
        if self.target == self.tabs.get("home"):
            self.parked = None
        self.send("Page.navigate", {"url": url})

    async def rest(self, on):
        """HA-Reiter ruhen lassen (leere Seite, spart Rechenzeit), solange niemand zuschaut; beim nächsten Zuschauer neu laden.
        Der Loxone-Reiter bleibt geladen (sonst müsste man sich neu anmelden).
        Nicht Page.setWebLifecycleState „frozen“: danach zeigt Chromium die Seite nie wieder an (bleibt weiß, getestet 23.10.)."""
        tid = self.tabs.get("home")
        sid = self.sessions.get(tid)
        if not sid:
            return
        if on and not self.parked:
            url = self.urls.get(tid, "")
            if url and not url.startswith("about:"):
                self.parked = url
                self.send("Page.navigate", {"url": "about:blank"}, sess=sid)
                log.info("HA-Reiter ruht (niemand schaut zu): %s", url)
        elif not on and self.parked:
            url, self.parked = self.parked, None
            self.send("Page.navigate", {"url": url}, sess=sid)
            log.info("HA-Reiter wird wieder geladen: %s", url)


# ---------------------------------------------------------------- Video

class Viewer:
    def __init__(self, ws, ip, mode="mse"):
        self.ws, self.ip = ws, ip
        self.mode = mode           # mse: Bild über diesen WebSocket; webrtc: Bild über go2rtc, WebSocket nur für Aushandeln/Messwerte
        self.q = asyncio.Queue()   # Grenze prüft Video.broadcast (ohne Ton 180 Stücke ≈ 6 s, mit Ton 480)
        self.ready = False
        self.need_key = True
        self.stats = {}
        self.since = time.time()
        # .32 JPEG: höchstens jmax Bilder unterwegs; jede angezeigte meldet die Seite zurück („ja“)
        self.jev = asyncio.Event()           # neues Bild da oder Antwort gekommen
        self.jflight, self.jmax, self.jseq = 0, CFG["jpeg_vorrat"], 0
        self.jsent = collections.OrderedDict()   # Bildnummer → Aufnahmezeit (ms)
        self.jdelay, self.jcount, self.jbytes, self.jlate = None, 0, 0, 0


class Video:
    def __init__(self, cdp):
        self.cdp = cdp
        self.proc = None
        self.viewers = set()
        self.moonlight = False   # .37: läuft gerade ein Moonlight-Stream? (hält den HA-Reiter wach)
        self.init = None
        self.codec = None
        self.ts = 90000
        self.tracks = {}
        self.audio = False                 # .30: MSE-Strom mit Ton (wünscht der erste MSE-Zuschauer mit ?ton=1)
        self.audio_on = False              # läuft der Kodierer gerade mit Ton?
        self.t0 = 0
        self.init_evt = asyncio.Event()
        self.stop_task = None
        self.freeze_task = None
        self.count = [0, 0, time.time()]   # Bilder, Bytes, seit
        self.rate = {"fps": 0, "kbit_s": 0}
        self.last_ts_msg = 0
        self.fps = CFG["fps"]              # zum Ausprobieren per /api/cmd {"c": "fps", "fps": 60} änderbar (bis zum Neustart)

    def mse_viewers(self):
        return [v for v in self.viewers if v.mode == "mse"]

    def argv(self):
        f, g = self.fps, max(1, int(round(self.fps * CFG["gop"])))
        self.audio_on = self.audio and pulse_ready()
        src = ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-nostdin"] + (["-thread_queue_size", "64"] if self.audio_on else []) + [
               "-f", "x11grab", "-draw_mouse", "0", "-framerate", str(f),
               "-video_size", "%dx%d" % (CFG["width"], CFG["height"]), "-i", CFG["display"] + ".0+0,0"]
        aud = ["-an"]
        frag = ["-movflags", "empty_moov+default_base_moof+frag_every_frame+skip_trailer"]
        if self.audio_on:   # .30: Ton aus der Senke dazu (AAC) – Bild und Ton haben beide Uhrzeit-Stempel, bleiben also gleich
            src += ["-thread_queue_size", "512", "-f", "pulse", "-sample_rate", "48000", "-channels", "2",
                    "-fragment_size", "3840", "-i", "tv.monitor"]
            aud = ["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
                   "-af", "aresample=async=1000"]
            # Mit Ton nicht frag_every_frame: ffmpeg warnt dann bei jedem Tonstück („pts has no value“, lokal mit 6.1);
            # Stücke von 33 ms (ein Bild plus der Ton dazu) laufen ohne Warnung.
            frag = ["-movflags", "empty_moov+default_base_moof+skip_trailer", "-frag_duration", "33000"]
        if CFG["codec"] == "vp9":
            enc = ["-c:v", "libvpx-vp9", "-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1", "-lag-in-frames", "0",
                   "-b:v", CFG["bitrate"], "-g", str(g), "-pix_fmt", "yuv420p"]
        else:
            level = env("X264_LEVEL", "5.1" if CFG["width"] * CFG["height"] > 1920 * 1088 else "4.1")
            enc = ["-c:v", "libx264", "-preset", CFG["preset"], "-tune", "zerolatency", "-profile:v", "high", "-level:v", level,
                   "-pix_fmt", "yuv420p", "-g", str(g), "-keyint_min", str(g), "-sc_threshold", "0", "-bf", "0",
                   "-b:v", CFG["bitrate"], "-maxrate", CFG["bitrate"], "-bufsize", CFG["bitrate"]]
        # Gleichmäßige Zeitstempel (genau 1/FPS): x11grab stempelt nach Uhrzeit mit kleinen Schwankungen, daraus werden
        # Lücken im Puffer – der Fernseher-Browser (webOS) zerlegt den Puffer dann in viele Stücke und springt ständig.
        cfr = ["-fps_mode:v", "cfr", "-r:v", str(f)]
        out = ["-f", "mp4"] + frag + ["-flush_packets", "1", "pipe:1"]
        return src + cfr + enc + aud + out

    async def start(self):
        if self.proc:
            return
        if not await wait_for_x():
            log.error("kein virtueller Bildschirm – Video kann nicht starten")
            return
        self.init = None
        self.init_evt.clear()      # dasselbe Event-Objekt behalten: verbundene Fernseher warten schon darauf
        argv = self.argv()
        self.t0 = time.time()
        self.proc = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                                                         limit=1 << 22, env=dict(os.environ, **PULSE_ENV) if self.audio_on else None)
        CHILDREN.add(self.proc)
        log.info("Video-Kodierer gestartet (%s, %dx%d, %d B/s, %s%s)", CFG["codec"], CFG["width"], CFG["height"], self.fps, CFG["bitrate"],
                 ", mit Ton" if self.audio_on else "")
        asyncio.ensure_future(self._stderr(self.proc))
        asyncio.ensure_future(self._read(self.proc))

    async def _stderr(self, proc):
        async for line in proc.stderr:
            text = line.decode("utf-8", "replace").rstrip()
            if "Guessed Channel Layout" in text:      # harmlos: Ton-Eingang ohne Kanalbelegung (.30)
                continue
            log.warning("ffmpeg: %s", text)

    async def _read(self, proc):
        buf, init, frag = bytearray(), [], None
        stdout = proc.stdout
        try:
            while True:
                chunk = await stdout.read(1 << 16)
                if not chunk:
                    break
                buf += chunk
                while len(buf) >= 8:
                    size, typ = struct.unpack(">I4s", buf[:8])
                    if size == 1:
                        if len(buf) < 16:
                            break
                        size = struct.unpack(">Q", buf[8:16])[0]
                    if size < 8:
                        raise ValueError("kaputte MP4-Box")
                    if len(buf) < size:
                        break
                    box = bytes(buf[:size])
                    del buf[:size]
                    typ = typ.decode("latin1")
                    if typ == "ftyp":
                        init = [box]
                    elif typ == "moov":
                        self.init = b"".join(init + [box])
                        self.tracks = track_list(box)
                        self.codec, self.ts = codec_string(self.tracks), video_track(self.tracks).get("ts", 90000)
                        self.init_evt.set()
                        log.info("Videoformat %s", self.codec)
                    elif typ == "moof":
                        frag = [box]
                    elif typ == "mdat" and frag:
                        key, bmdt, vid = fragment_info(frag[0], self.tracks)
                        self.broadcast(frag[0] + box, key, bmdt, vid)
                        frag = None
        except Exception as e:
            log.error("Videostrom: %s", e)
        await proc.wait()
        CHILDREN.discard(proc)
        log.info("Video-Kodierer beendet (Code %s)", proc.returncode)
        if self.audio_on and self.init is None and time.time() - self.t0 < 15 and not STOPPING:
            self.audio = False         # Ton-Eingang geht nicht (Senke fehlt?) → ohne Ton weiter, statt gar kein Bild
            log.warning("Ton im MSE-Strom geht nicht – Kodierer läuft ohne Ton weiter")
        if self.proc is proc:
            self.proc = None
            self.init = None
            self.init_evt.clear()
            for v in self.mse_viewers():      # Fernseher verbinden sich neu und bekommen den neuen Anfang des Stroms
                asyncio.ensure_future(v.ws.close(code=1012, message=b"Kodierer neu gestartet"))

    def broadcast(self, data, key, bmdt, vid=True):
        c = self.count
        c[0] += 1 if vid else 0            # Bilder/s zählen nur Bildstücke (mit Ton kommen Tonstücke dazu)
        c[1] += len(data)
        now = time.time()
        if now - c[2] >= 2:
            self.rate = {"fps": round(c[0] / (now - c[2]), 1), "kbit_s": int(c[1] * 8 / 1000 / (now - c[2]))}
            self.count = [0, 0, now]
        stamp = None
        if bmdt is not None and now - self.last_ts_msg >= 1:   # Zeitmarke für die Verzögerungsmessung im Fernseher
            self.last_ts_msg = now
            stamp = json.dumps({"type": "ts", "m": bmdt / float(self.ts), "w": int(now * 1000)})
        for v in list(self.viewers):
            if v.mode != "mse" or not v.ready:
                continue
            if v.need_key:
                if not (vid and key):
                    continue
                v.need_key = False
            # Fernseher kommt nicht nach (~6 s Rückstand) → bis zum nächsten Schlüsselbild aussetzen
            if v.q.qsize() >= (480 if self.audio_on else 180) - 1:
                while not v.q.empty():
                    v.q.get_nowait()
                v.need_key = True
                v.stats["uebersprungen"] = v.stats.get("uebersprungen", 0) + 1
                continue
            v.q.put_nowait(data)
            if stamp:
                v.q.put_nowait(stamp)

    def add(self, v):
        self.viewers.add(v)
        if self.freeze_task:
            self.freeze_task.cancel()
            self.freeze_task = None
        asyncio.ensure_future(self.cdp.rest(False))
        if v.mode == "mse":
            if self.stop_task:
                self.stop_task.cancel()
                self.stop_task = None
            asyncio.ensure_future(self.start())

    def remove(self, v):
        self.viewers.discard(v)
        if not self.mse_viewers() and self.proc and (not self.stop_task or self.stop_task.done()):
            self.stop_task = asyncio.ensure_future(self._stop_later())
        if not self.viewers and CFG["freeze_after"] > 0 and (not self.freeze_task or self.freeze_task.done()):
            self.freeze_task = asyncio.ensure_future(self._freeze_later())

    async def _stop_later(self):
        await asyncio.sleep(CFG["idle_stop"])
        if not self.mse_viewers() and self.proc:
            log.info("niemand schaut per MSE zu – Kodierer aus")
            self.proc.terminate()

    def restart(self):
        """Kodierer mit neuen Einstellungen neu starten – verbundene Fernseher verbinden sich neu."""
        if self.proc:
            self.proc.terminate()

    async def _freeze_later(self):
        await asyncio.sleep(CFG["freeze_after"])
        while not self.viewers and not self.moonlight and not self.cdp.sess:   # Chromium startet noch / Moonlight-Stream
            await asyncio.sleep(5)
        if not self.viewers and not self.moonlight:
            await self.cdp.rest(True)


# ---------------------------------------------------------------- Moonlight / Sunshine (.37)

async def sunshine_ton_pruefen():
    """.37j: Tonzeilen aus Sunshines Protokoll 20 s nach dem Start nach HA melden (Fehlersuche „kein Ton“)."""
    await asyncio.sleep(20)
    try:
        with open(os.path.join(CFG["sunshine_dir"], ".config", "sunshine", "sunshine.log"), encoding="utf-8", errors="replace") as f:
            z = [l.strip() for l in f if re.search(r"(?i)audio|pulse|sink|mic", l)]
    except OSError:
        z = []
    for l in z[-8:] or ["keine Tonzeilen im Protokoll"]:
        log.warning("Sunshine-Ton: %s", l[:200])


def moonlight_apps():
    try:
        with open(os.path.join(CFG["sunshine_dir"], "app-ids.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def moonlight_app_merken(name, aid):
    a = moonlight_apps()
    if a.get(name) != aid:
        a[name] = aid
        with open(os.path.join(CFG["sunshine_dir"], "app-ids.json"), "w", encoding="utf-8") as f:
            json.dump(a, f)
        log.info("Moonlight: App „%s“ hat die ID %d", name, aid)


def moonlight_uuid():
    """Kennung dieses Sunshine (für den Direktstart von Moonlight per HA) – nur die ID, nie die Kopplungsdaten."""
    try:
        with open(os.path.join(CFG["sunshine_dir"], ".config", "sunshine", "sunshine_state.json"), encoding="utf-8") as f:
            st = json.load(f)
        return str((st.get("root") or st).get("uniqueid") or "")[:40]
    except (OSError, ValueError, AttributeError):
        return ""


def sunshine_einrichten():
    """Sunshine-Konfig und Prep-Skript im Volume anlegen (Konfig nur beim ersten Mal – spätere Änderungen in der Web-UI
    bleiben erhalten). Gibt (argv, env) zum Starten zurück oder None, wenn Sunshine nicht im Image liegt."""
    exe = CFG["sunshine_bin"]
    binr = os.path.join(os.path.dirname(exe), "usr", "bin", "sunshine")
    if not (os.path.exists(exe) or os.path.exists(binr)):
        log.warning("Moonlight: Sunshine nicht gefunden (%s) – übersprungen", exe)
        return None
    base = CFG["sunshine_dir"]
    cfgdir = os.path.join(base, ".config", "sunshine")
    os.makedirs(cfgdir, exist_ok=True)
    prep = os.path.join(base, "prep.py")
    # Prep-Skript hält den HA-Reiter wach, solange ein Moonlight-Stream läuft (Sunshine ruft es per global_prep_cmd auf)
    with open(prep, "w", encoding="utf-8") as f:
        f.write("import sys, json, urllib.request\n"
                "an = 1 if (len(sys.argv) > 1 and sys.argv[1] == '1') else 0\n"
                "r = urllib.request.Request('http://127.0.0.1:%d/api/cmd', data=json.dumps({'c': 'moonlight', 'an': an}).encode(),\n"
                "                           headers={'Content-Type': 'application/json'})\n"
                "try:\n    urllib.request.urlopen(r, timeout=5)\nexcept Exception:\n    pass\n" % CFG["port"])
    # .37g: eigene App-Liste statt Sunshine-Vorgabe („Low Res Desktop“ braucht xrandr, „Steam“ gibt es hier nicht):
    # Home Assistant und Loxone – Loxone schaltet beim Start den Streamer-Reiter um und beim Beenden zurück auf HA.
    cmd = os.path.join(base, "cmd.py")
    with open(cmd, "w", encoding="utf-8") as f:
        f.write("import os, sys, json, urllib.request\n"
                "d = {'c': sys.argv[1], 'app_id': os.environ.get('SUNSHINE_APP_ID', ''), 'app_name': os.environ.get('SUNSHINE_APP_NAME', '')}\n"
                "r = urllib.request.Request('http://127.0.0.1:%d/api/cmd', data=json.dumps(d).encode(),\n"
                "                           headers={'Content-Type': 'application/json'})\n"
                "try:\n    urllib.request.urlopen(r, timeout=5)\nexcept Exception:\n    pass\n" % CFG["port"])
    def bild(n):     # .37j: eigenes Logo (logo-<n>.png, optional) vor der schlichten Kachel
        eigen = os.path.join(cfgdir, "logo-%s.png" % n)
        return eigen if os.path.exists(eigen) else "desktop.png"   # sonst Sunshines Standardbild
    apps = {"env": {}, "apps": [
        {"name": "Home Assistant", "image-path": bild("ha"),
         "prep-cmd": [{"do": "python3 %s zeige_home" % cmd, "undo": ""}]},
    ]}
    for n in sorted(CFG["links"]):   # je zusätzlichem Reiter eine App (Name = Reitername, z. B. „Loxone“)
        apps["apps"].append({"name": n.replace("_", " ").title(), "image-path": bild(n),
                             "prep-cmd": [{"do": "python3 %s link:%s" % (cmd, n), "undo": "python3 %s zeige_home" % cmd}]})
    with open(os.path.join(cfgdir, "apps.json"), "w", encoding="utf-8") as f:
        json.dump(apps, f, indent=2)
    conf = os.path.join(cfgdir, "sunshine.conf")
    if not os.path.exists(conf):
        prepcmd = json.dumps([{"do": "python3 %s 1" % prep, "undo": "python3 %s 0" % prep, "elevated": "false"}])
        with open(conf, "w", encoding="utf-8") as f:
            f.write("capture = x11\nencoder = software\nsw_preset = superfast\nsw_tune = zerolatency\n"
                    "min_log_level = 2\norigin_web_ui_allowed = lan\nport = %d\n"
                    "csrf_allowed_origins = https://%s:%d,https://localhost:%d\n"
                    "file_apps = %s\n"
                    "global_prep_cmd = %s\n" % (CFG["sunshine_port"], CFG.get("public_ip") or "localhost",
                                                  CFG["sunshine_port"] + 1, CFG["sunshine_port"] + 1,
                                                  os.path.join(cfgdir, "apps.json"), prepcmd))
        log.info("Moonlight: Sunshine-Konfig angelegt (%s)", conf)
    # .37h: Einträge, die spätere Fassungen brauchen, in eine schon vorhandene Konfig nachtragen (Rest bleibt wie in der Web-UI)
    try:
        with open(conf, encoding="utf-8") as f:
            vorhanden = f.read()
        fehlt = []
        if CFG["audio"] and not re.search(r"(?m)^audio_sink\s*=", vorhanden):
            fehlt.append("audio_sink = tv")      # Ton aus der PulseAudio-Senke „tv“, in die Chromium spielt
        if not re.search(r"(?m)^csrf_allowed_origins\s*=", vorhanden):
            fehlt.append("csrf_allowed_origins = https://%s:%d,https://localhost:%d" % (CFG.get("public_ip") or "localhost",
                         CFG["sunshine_port"] + 1, CFG["sunshine_port"] + 1))
        if fehlt:
            with open(conf, "a", encoding="utf-8") as f:
                f.write(("" if vorhanden.endswith("\n") else "\n") + "\n".join(fehlt) + "\n")
            log.info("Moonlight: Sunshine-Konfig ergänzt (%s)", ", ".join(x.split(" ")[0] for x in fehlt))
    except OSError as e:
        log.warning("Moonlight: Sunshine-Konfig nicht lesbar: %s", e)
    env = dict({"HOME": base, "XDG_CONFIG_HOME": os.path.join(base, ".config")}, **(PULSE_ENV if CFG["audio"] else {}))   # DISPLAY setzt supervise selbst (doppelt = TypeError, .37e)
    return [exe, conf], env


# ---------------------------------------------------------------- JPEG (.32)

def jpeg_size(name):
    """„sd“ 960 / „hd“ 1280 / „fhd“ 1920 breit, sonst das volle Bild – nie größer als der Bildschirm, Höhe gerade, gleiches Format."""
    w = min({"sd": 960, "hd": 1280, "fhd": 1920}.get(name, CFG["width"]), CFG["width"])
    return w, int(round(CFG["height"] * float(w) / CFG["width"] / 2)) * 2


class JpegEncoder:
    """Bildweg JPEG (.32): Der Streamer greift den Bildschirm ab (x11grab), verkleinert ihn und kodiert jedes Bild als JPEG –
    in einem eigenen Thread (PyAV, die Arbeit machen swscale und mjpeg in C). Es geht nur ein Bild raus, wenn es sich vom
    zuletzt verschickten unterscheidet, und nur an Seiten, die bereit sind: Jede Seite hat höchstens JPEG_VORRAT Bilder
    unterwegs und meldet jedes angezeigte zurück („ja“). Kommt ein Fernseher nicht nach, bekommt er einfach das jeweils
    neueste Bild – weniger Bilder pro Sekunde, aber kein Rückstand. Kodiert wird nur, solange eine Seite auf ein Bild wartet.
    Ein Lauf hat eigene Signale (wie RtcEncoder): Ein auslaufender alter Lauf stört den neuen nicht."""

    def __init__(self, key, size, q, fps):
        self.key, self.size, self.q, self.fps = key, size, q, fps
        self.users = set()
        self.loop = None
        self.run = None
        self.want = threading.Event()        # mindestens eine Seite wartet auf ein Bild
        self.frame = None                    # (Nummer, Aufnahmezeit ms, JPEG)
        self.seq = 0
        self.error = None
        self.stop_task = None
        self.n = {"gegriffen": 0, "kodiert": 0, "neu": 0, "bytes": 0, "kodier_s": 0.0}
        self.rate = {}
        self._r0 = (time.time(), dict(self.n))

    def running(self):
        r = self.run
        return bool(r and r["thread"].is_alive() and not r["halt"].is_set())

    def start(self):
        if self.stop_task:
            self.stop_task.cancel()
            self.stop_task = None
        if self.running():
            return
        self.loop = asyncio.get_running_loop()
        prev = self.run
        r = {"halt": threading.Event(), "t0": time.time()}
        r["thread"] = threading.Thread(target=self._run, args=(r, prev), name="jpeg-" + self.key, daemon=True)
        self.run, self.error, self.frame = r, None, None
        r["thread"].start()

    def halt(self):
        if self.run:
            self.run["halt"].set()

    def join(self, v):
        self.users.add(v)
        self.start()
        self.update_want()

    def leave(self, v):
        self.users.discard(v)
        self.update_want()
        if self.users or (self.stop_task and not self.stop_task.done()):
            return

        async def later():
            await asyncio.sleep(CFG["idle_stop"])
            if not self.users:
                log.info("niemand schaut per JPEG zu (%s) – Kodierer aus", self.key)
                self.halt()
        self.stop_task = asyncio.ensure_future(later())

    def update_want(self):
        if any(u.jflight < u.jmax for u in self.users):
            self.want.set()
        else:
            self.want.clear()

    def publish(self, seq, t_ms, data):
        """Im Haupt-Thread (call_soon_threadsafe): neues Bild bereitlegen, wartende Seiten wecken."""
        self.frame = (seq, t_ms, data)
        for u in list(self.users):
            u.jev.set()

    def failed(self):
        """Kodierer ist mit Fehler stehen geblieben → Seiten verbinden sich neu (startet einen neuen Lauf)."""
        for u in list(self.users):
            asyncio.ensure_future(u.ws.close(code=1011, message=b"JPEG-Kodierer neu"))

    def _rates(self):
        now = time.time()
        t0, n0 = self._r0
        dt = now - t0
        if dt < 2:
            return
        d = {k: self.n[k] - n0.get(k, 0) for k in self.n}
        self.rate = {"gegriffen_s": round(d["gegriffen"] / dt, 1), "kodiert_s": round(d["kodiert"] / dt, 1),
                     "neu_s": round(d["neu"] / dt, 1),
                     "kb_bild": round(d["bytes"] / 1000.0 / d["neu"], 1) if d["neu"] else None,
                     "kodieren_ms": round(d["kodier_s"] * 1000 / d["kodiert"], 1) if d["kodiert"] else None}
        self._r0 = (now, dict(self.n))

    def _run(self, r, prev):
        if prev and prev["thread"].is_alive():
            prev["thread"].join(5)
        w, h = self.size
        scale = (w, h) != (CFG["width"], CFG["height"])
        inp, last, n = None, None, 0
        try:
            inp = av.open(CFG["display"] + ".0+0,0", format="x11grab",
                          options={"framerate": str(self.fps), "video_size": "%dx%d" % (CFG["width"], CFG["height"]), "draw_mouse": "0"})
            cc = av.CodecContext.create("mjpeg", "w")
            cc.width, cc.height, cc.pix_fmt = w, h, "yuvj420p"
            tb = Fraction(1, self.fps)
            cc.time_base = tb
            cc.bit_rate = 100000000              # ohne Wirkung: qmin = qmax hält die Qualität fest
            cc.options = {"qmin": str(self.q), "qmax": str(self.q)}
            log.info("JPEG-Kodierer %s: %dx%d, bis %d Bilder/s, Qualität %d", self.key, w, h, self.fps, self.q)
            for frame in inp.decode(video=0):
                if r["halt"].is_set():
                    break
                self.n["gegriffen"] += 1
                if self.n["gegriffen"] % 30 == 0:
                    self._rates()
                if not self.want.is_set():       # alle Seiten haben genug unterwegs → dieses Bild auslassen
                    continue
                t_ms = time.time() * 1000.0
                a = time.perf_counter()
                f = frame.reformat(width=w, height=h, format="yuvj420p", interpolation="BILINEAR" if scale else None)
                f.pts, f.time_base = n, tb         # eigene Zählung: x11grab stempelt in µs – umgerechnet wären es lauter gleiche Werte
                n += 1
                data = b"".join(bytes(p) for p in cc.encode(f))
                self.n["kodiert"] += 1
                self.n["kodier_s"] += time.perf_counter() - a
                if not data or data == last:     # nichts geändert → nichts schicken
                    continue
                last = data
                self.seq += 1
                self.n["neu"] += 1
                self.n["bytes"] += len(data)
                self.loop.call_soon_threadsafe(self.publish, self.seq, t_ms, data)
        except Exception as e:
            if not r["halt"].is_set():
                self.error = "%s: %s" % (type(e).__name__, str(e)[:200])
                log.warning("JPEG-Kodierer %s: %s", self.key, self.error)
                try:
                    self.loop.call_soon_threadsafe(self.failed)
                except Exception:
                    pass
        finally:
            r["halt"].set()
            try:
                if inp is not None:
                    inp.close()
            except Exception:
                pass
            log.info("JPEG-Kodierer %s beendet (%d Bilder kodiert, %d verschickt)", self.key, self.n["kodiert"], self.n["neu"])

    def info(self):
        return dict(self.rate, bild="%dx%d" % self.size, qualitaet=self.q, bilder_s_hoechstens=self.fps, laeuft=self.running(),
                    seiten=len(self.users), fehler=self.error)


class JpegPool:
    """Ein JPEG-Kodierer je Größe, Qualität und Bildrate (meist nur einer: der Fernseher dieses Streamers)."""

    def __init__(self):
        self.encoders = {}

    def get(self, name, q, fps):
        name = name if name in ("sd", "hd", "fhd") else "voll"
        key = "%s-q%d-%d" % (name, q, fps)
        if key not in self.encoders:
            self.encoders[key] = JpegEncoder(key, jpeg_size(name), q, fps)
        return self.encoders[key]

    def info(self):
        return {k: e.info() for k, e in self.encoders.items() if e.users or e.running()}


# ---------------------------------------------------------------- WebRTC (go2rtc)

def rate_bits(text):
    """„12M“, „800k“, „1000000“ → Bit/s."""
    t = str(text).strip().lower()
    mult = 1000000 if t.endswith("m") else (1000 if t.endswith("k") else 1)
    return int(float(t.rstrip("mk")) * mult)


class RtcEncoder:
    """Eigener Kodierer für den Bildweg WebRTC (PyAV): Bildschirm → H.264 baseline mit spaltenweiser Erneuerung →
    RTSP an go2rtc (go2rtc verteilt per WebRTC). Ein Schlüsselbild (IDR) gibt es nur beim Start und auf Abruf – wenn
    ein Fernseher einsteigt oder nach Paketverlust eines anfordert. So bleiben alle Bilder klein (kein Paket-Schwall)
    und trotzdem kann jeder jederzeit einsteigen. Läuft in einem eigenen Thread (die Arbeit machen x11grab, swscale
    und libx264 in C). Jeder Lauf hat eigene Signale: ein auslaufender alter Lauf stört den neuen nicht."""

    def __init__(self, name, size):
        self.name, self.size = name, size
        self.run = None                      # aktueller Lauf: {"halt", "ok", "thread"}
        self.key = threading.Event()         # Schlüsselbild anfordern (gilt für den laufenden Kodierer)
        self.users = set()
        self.stop_task = None
        self.error = None
        self.frames = 0
        self.keys = 0
        self.last_key = 0.0

    def running(self):
        r = self.run
        return bool(r and r["thread"].is_alive() and not r["halt"].is_set())

    def ready(self):
        r = self.run
        return bool(r and r["ok"].is_set() and not r["halt"].is_set())

    def start(self):
        if self.stop_task:
            self.stop_task.cancel()
            self.stop_task = None
        if self.running():
            return
        prev = self.run
        r = {"halt": threading.Event(), "ok": threading.Event(), "t0": time.time()}
        r["thread"] = threading.Thread(target=self._run, args=(r, prev), name="webrtc-" + self.name, daemon=True)
        self.run, self.error = r, None
        r["thread"].start()

    def halt(self):
        if self.run:
            self.run["halt"].set()

    def stop_later(self):
        async def later():
            await asyncio.sleep(CFG["idle_stop"])
            if not self.users:
                log.info("niemand schaut per WebRTC zu (%s) – Kodierer aus", self.name)
                self.halt()
        if not self.stop_task or self.stop_task.done():
            self.stop_task = asyncio.ensure_future(later())

    def want_key(self):
        """Schlüsselbild anfordern – höchstens alle 0,5 s (eines reicht für alle, die gerade eines brauchen)."""
        now = time.time()
        if now - self.last_key >= 0.5:
            self.last_key = now
            self.key.set()

    def _run(self, r, prev):
        if prev and prev["thread"].is_alive():
            prev["thread"].join(5)           # alter Lauf trennt sich erst von go2rtc
        w, h = self.size or (CFG["width"], CFG["height"])
        fps, rate = CFG["fps"], CFG["webrtc_bitrate"] or CFG["bitrate"]
        br = rate_bits(rate)
        inp = out = None
        frames = keys = 0
        try:
            from av.video.frame import PictureType
            pict_i = PictureType.I
        except Exception:
            pict_i = "I"
        try:
            inp = av.open(CFG["display"] + ".0+0,0", format="x11grab",
                          options={"framerate": str(fps), "video_size": "%dx%d" % (CFG["width"], CFG["height"]), "draw_mouse": "0"})
            out = av.open("rtsp://127.0.0.1:%d/%s" % (CFG["go2rtc_rtsp"], self.name), mode="w", format="rtsp",
                          options={"rtsp_transport": "tcp", "timeout": "5000000"})   # hängt go2rtc: nach 5 s Fehler statt warten
            st = out.add_stream("libx264", rate=fps)
            st.width, st.height, st.pix_fmt = w, h, "yuv420p"
            st.bit_rate = br
            opts = {
                "preset": CFG["preset"], "tune": "zerolatency", "profile": CFG["webrtc_profile"],
                "level": "5.1" if w * h > 1920 * 1088 else "4.1", "bf": "0",
                "maxrate": str(br), "bufsize": str(rate_bits(CFG["webrtc_bufsize"])), "forced-idr": "1",
            }
            if CFG["webrtc_refresh"]:
                opts.update({"g": str(fps), "intra-refresh": "1"})
            else:      # keine Schlüsselbilder von selbst (auch nicht bei Bildwechseln) – nur auf Abruf
                opts.update({"g": str(1 << 30), "sc_threshold": "0", "x264-params": "keyint=infinite:scenecut=0"})
            st.codec_context.options = opts
            tb = Fraction(1, fps)
            log.info("WebRTC-Kodierer %s: %dx%d, %d B/s, %s, Schlüsselbild auf Abruf%s", self.name, w, h, fps, rate,
                     ", spaltenweise Erneuerung" if CFG["webrtc_refresh"] else "")
            self.key.clear()
            for frame in inp.decode(video=0):
                if r["halt"].is_set():
                    break
                f = frame.reformat(width=w, height=h, format="yuv420p", interpolation="BICUBIC" if self.size else None)
                f.pts, f.time_base = frames, tb
                if frames == 0 or self.key.is_set():
                    self.key.clear()
                    f.pict_type = pict_i
                    keys += 1
                    self.keys += 1
                for pkt in st.encode(f):
                    out.mux(pkt)
                frames += 1
                self.frames += 1
                if frames == 3:
                    r["ok"].set()
        except Exception as e:
            if not r["halt"].is_set():
                self.error = "%s: %s" % (type(e).__name__, str(e)[:200])
                log.warning("WebRTC-Kodierer %s: %s", self.name, self.error)
        finally:
            r["halt"].set()
            for c in (inp, out):
                try:
                    if c is not None:
                        c.close()
                except Exception:
                    pass
            log.info("WebRTC-Kodierer %s beendet (%d Bilder, %d Schlüsselbilder)", self.name, frames, keys)


class WebRtc:
    """go2rtc als Unterprozess, verteilt das Bild per WebRTC. Schnittstelle nur als Unix-Socket-Datei: Seiten im
    Chromium (HA, Loxone) kommen nicht an sie heran. Quellen: „bild“ (volle Größe), „bild_fhd“ (1920 breit) und
    „bild_hd“ (1280 breit), soweit kleiner als das volle Bild. Kodierer: PyAV im Streamer (Schlüsselbild auf Abruf) oder – falls PyAV fehlt –
    ffmpeg über go2rtc „exec“ (Schlüsselbild alle 2 s)."""

    def __init__(self):
        self.enabled = CFG["webrtc_port"] > 0 and os.access(CFG["go2rtc"], os.X_OK)
        self.own = self.enabled and CFG["webrtc_encoder"] == "pyav" and av is not None
        self.sock = os.path.join(CFG["go2rtc_dir"], "go2rtc-%s.sock" % CFG["name"])
        self.conf = os.path.join(CFG["go2rtc_dir"], "go2rtc-%s.yaml" % CFG["name"])
        self.sources = {"bild": None}
        for name, width in (("bild_fhd", 1920), ("bild_hd", 1280)):     # kleinere Bilder für schwächere Fernseher (?webrtc=fhd|hd)
            if CFG["width"] > width:
                self.sources[name] = (width, int(round(CFG["height"] * float(width) / CFG["width"] / 2)) * 2)
        # .32: VP8-Quelle (Versuch Schlafzimmer) – immer über go2rtc exec (libvpx), startet nur auf Abruf
        self.vp8 = set()
        vw = {"hd": 1280, "fhd": 1920}.get(CFG["webrtc_vp8"])
        if vw:
            vw = min(vw, CFG["width"])
            self.sources["bild_vp8"] = (vw, int(round(CFG["height"] * float(vw) / CFG["width"] / 2)) * 2)
            self.vp8.add("bild_vp8")
        self.encoders = ({name: RtcEncoder(name, size) for name, size in self.sources.items() if name not in self.vp8}
                         if self.own else {})
        self.problem = None
        if CFG["webrtc_port"] > 0 and not self.enabled:
            log.warning("WebRTC: go2rtc fehlt (%s) – nur MSE", CFG["go2rtc"])
        elif self.enabled and not self.own:
            log.warning("WebRTC: %s – Kodierer über go2rtc exec (Schlüsselbild alle 2 s)",
                        "PyAV fehlt" if av is None else "WEBRTC_ENCODER=%s" % CFG["webrtc_encoder"])

    def encoder(self, size=None, vp8=False):
        """ffmpeg-Aufruf für go2rtc exec (Rückfall ohne PyAV; VP8-Quelle): Profil „baseline“, Ausgabe per RTSP an go2rtc."""
        f, g = CFG["fps"], max(1, int(round(CFG["fps"] * CFG["gop"])))
        w, h = size or (CFG["width"], CFG["height"])
        br = CFG["webrtc_vp8_bitrate"] if vp8 else (CFG["webrtc_bitrate"] or CFG["bitrate"])
        a = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
             "-f", "x11grab", "-draw_mouse", "0", "-framerate", str(f),
             "-video_size", "%dx%d" % (CFG["width"], CFG["height"]), "-i", CFG["display"] + ".0+0,0"]
        if size:
            a += ["-vf", "scale=%d:%d:flags=bicubic" % (w, h)]
        a += ["-fps_mode", "cfr", "-r", str(f)]
        if vp8 or env("WEBRTC_CODEC", "h264") == "vp8":    # VP8-Quelle (.32) bzw. Tests mit Browsern ohne H.264
            a += ["-c:v", "libvpx", "-deadline", "realtime", "-cpu-used", "8", "-lag-in-frames", "0", "-error-resilient", "1",
                  "-g", str(g), "-b:v", br, "-pix_fmt", "yuv420p"]
        else:
            a += ["-c:v", "libx264", "-preset", CFG["preset"], "-tune", "zerolatency",
                  "-profile:v", CFG["webrtc_profile"], "-level:v", "5.1" if w * h > 1920 * 1088 else "4.1",
                  "-pix_fmt", "yuv420p", "-g", str(g), "-bf", "0", "-b:v", br, "-maxrate", br, "-bufsize", CFG["webrtc_bufsize"]]
            # Spaltenweise Erneuerung statt großer Schlüsselbilder. Echte Schlüsselbilder (IDR) braucht der Empfänger zum
            # Einstieg und nach Paketverlust: in den ersten 2 s alle 9 Bilder, danach alle 2 s (go2rtc exec kann sie nicht
            # auf Abruf liefern). Durch -bufsize bleiben auch sie klein.
            a += ["-intra-refresh", "1", "-forced-idr", "1",
                  "-force_key_frames", "expr:lt(t,2.1)*eq(mod(n,9),0)+gte(t,2.1)*eq(mod(n,%d),0)" % (f * 2)]
        a += ["-an", "-rtsp_transport", "tcp", "-f", "rtsp", "{output}"]
        return "exec:" + " ".join(a)

    def stream_sources(self, size, vp8=False):
        """Quellen einer go2rtc-Quelle: Bild (eigener Kodierer liefert per RTSP – dann keine; VP8 immer exec) und mit AUDIO=1
        der Ton aus der PulseAudio-Senke als Opus (.30). go2rtc startet den Ton erst, wenn eine Empfangsseite ihn anfordert."""
        src = [self.encoder(size, vp8)] if (vp8 or not self.own) else []
        if CFG["audio"]:
            src.append("exec:ffmpeg -hide_banner -loglevel error -nostdin -thread_queue_size 512 -f pulse -sample_rate 48000 "
                       "-channels 2 -fragment_size 1920 -i tv.monitor -vn -c:a libopus -b:a %s -application lowdelay "
                       "-frame_duration 20 -f rtsp {output}" % CFG["audio_bitrate"])
        return src or None

    def argv(self):
        """Konfiguration schreiben (JSON ist gültiges YAML) und go2rtc-Aufruf liefern – je Start neu.
        Mit eigenem Kodierer sind die Quellen leer: der Streamer liefert das Bild per RTSP an go2rtc."""
        cands = ["%s:%d" % (CFG["public_ip"], CFG["webrtc_port"])] if CFG["public_ip"] else []
        conf = {
            "log": {"level": "warn", "output": "stderr", "format": "text"},
            "api": {"listen": "", "unix_listen": self.sock},
            "rtsp": {"listen": "127.0.0.1:%d" % CFG["go2rtc_rtsp"]},
            "srtp": {"listen": ""},
            "webrtc": {"listen": ":%d" % CFG["webrtc_listen"], "candidates": cands},
            "streams": {name: self.stream_sources(size, name in self.vp8) for name, size in self.sources.items()},
        }
        with open(self.conf, "w", encoding="utf-8") as fh:
            json.dump(conf, fh, indent=1)
        try:
            os.remove(self.sock)          # Rest nach Absturz
        except OSError:
            pass
        return [CFG["go2rtc"], "-config", self.conf]

    async def api(self, method, path, **kw):
        async with ClientSession(connector=UnixConnector(path=self.sock), timeout=ClientTimeout(total=15)) as s:
            async with s.request(method, "http://go2rtc" + path, **kw) as r:
                text = await r.text()
                if r.status >= 300:
                    raise RuntimeError("go2rtc HTTP %d: %s" % (r.status, text.strip()[:200]))
                return json.loads(text) if text.strip() else {}

    async def join(self, v, src):
        """Zuschauer an eine Quelle hängen; eigenen Kodierer starten und warten, bis go2rtc Bilder hat
        (go2rtc kann erst antworten, wenn die Quelle Bilder liefert). Startet go2rtc gerade erst, 3 Versuche."""
        old = getattr(v, "src", None)
        if old and old != src:
            self.leave(v)
        v.src = src
        enc = self.encoders.get(src)
        if not enc:
            return
        enc.users.add(v)
        tries = 0
        enc.start()
        t0 = time.time()
        while not enc.ready():
            if time.time() - t0 > 8:
                await self.fallback("liefert nach 8 s kein Bild")
                return
            if not enc.running():
                tries += 1
                if tries >= 3:
                    await self.fallback(enc.error or "startet nicht")
                    return
                await asyncio.sleep(0.7)
                enc.start()
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.2)        # go2rtc kennt jetzt die Beschreibung des Stroms

    async def fallback(self, reason):
        """Eigener Kodierer geht nicht → bis zum Neustart des Containers ffmpeg über go2rtc exec (Schlüsselbild alle 2 s).
        go2rtc startet dafür mit neuer Einstellung neu; die laufende Aushandlung wartet darauf."""
        if not self.own:
            return
        log.warning("WebRTC: eigener Kodierer geht nicht (%s) – weiter mit go2rtc exec", reason)
        self.own, self.problem = False, str(reason)[:200]
        for enc in self.encoders.values():
            enc.halt()
        self.encoders = {}
        p = RUNNING.get("go2rtc")
        if p and p.returncode is None:
            p.terminate()
        await asyncio.sleep(1.5)
        t0 = time.time()
        while time.time() - t0 < 10:
            try:
                await self.api("GET", "/api/streams")
                return
            except Exception:
                await asyncio.sleep(0.3)

    def leave(self, v):
        enc = self.encoders.get(getattr(v, "src", None))
        if enc and v in enc.users:
            enc.users.discard(v)
            if not enc.users:
                enc.stop_later()

    def key(self, v):
        """Schlüsselbild für die Quelle dieses Zuschauers (Einstieg, Paketverlust)."""
        enc = self.encoders.get(getattr(v, "src", None))
        if enc and enc.running():
            enc.want_key()
            return True
        return False

    async def check(self, ip, src, delay=5):
        """Fehlersuche: Schickt go2rtc dem Zuschauer einige Sekunden nach dem Aushandeln wirklich Bilder?
        (Fernseher meldeten 23.10. nach dem Neuverbinden „verbunden, aber keine Daten“.)"""
        await asyncio.sleep(delay)
        try:
            d = await self.api("GET", "/api/streams")
        except Exception as e:
            log.warning("WebRTC-Prüfung %s: go2rtc antwortet nicht (%s)", ip, e)
            return
        s = (d or {}).get(src) or {}
        prods = s.get("producers") or []
        alle = s.get("consumers") or []
        cons = [c for c in alle if str(c.get("remote_addr") or "").startswith(ip + ":")] or alle
        eingang = [int((p.get("bytes_recv") or 0) / 1000) for p in prods]
        if not cons:
            log.warning("WebRTC-Prüfung %s: go2rtc führt keinen Zuschauer (Quellen %s KB)", ip, eingang)
            return
        for c in cons:
            kb = int((c.get("bytes_send") or 0) / 1000)
            drops = sum((x or {}).get("drops", 0) for x in c.get("senders") or [])
            (log.info if kb > 0 and not drops else log.warning)(
                "WebRTC-Prüfung %s: nach %d s %d KB an %s geschickt, %d verworfen (Quellen %s KB)",
                ip, delay, kb, c.get("remote_addr"), drops, eingang)

    async def answer(self, offer, src):
        if not self.enabled:
            raise RuntimeError("WebRTC ist auf diesem Streamer nicht eingerichtet")
        if src not in self.sources:
            src = "bild"
        r = await self.api("POST", "/api/webrtc?src=" + src, json={"type": "offer", "sdp": offer})
        if not r.get("sdp"):
            raise RuntimeError("go2rtc: keine Antwort (%s)" % str(r)[:120])
        return r["sdp"]

    async def info(self):
        """Kurzfassung je Quelle: läuft der Kodierer, wie viele schauen zu (für /api/status)."""
        if not self.enabled:
            return {}
        try:
            d = await self.api("GET", "/api/streams")
        except Exception as e:
            return {"fehler": str(e)[:120]}
        out = {"kodierer_art": "eigener (Schlüsselbild auf Abruf)" if self.own else "go2rtc exec"}
        if self.problem:
            out["eigener_kodierer_problem"] = self.problem
        for name, s in (d or {}).items():
            prod = [p for p in (s or {}).get("producers") or [] if p.get("id") or p.get("bytes_recv") or p.get("medias")]
            cons = (s or {}).get("consumers") or []
            out[name] = {"kodierer": bool(prod), "zuschauer": len(cons)}
            if prod:          # was beim go2rtc ankommt (KB je Quelle – mehr als eine: alte Quelle hängt noch)
                out[name]["eingang_kb"] = [int((p.get("bytes_recv") or 0) / 1000) for p in prod]
            if cons:          # was go2rtc an wen schickt
                out[name]["ausgang"] = [{"an": c.get("remote_addr"), "kb": int((c.get("bytes_send") or 0) / 1000),
                                         "verworfen": sum((x or {}).get("drops", 0) for x in c.get("senders") or [])}
                                        for c in cons]
            enc = self.encoders.get(name)
            if enc:
                out[name].update(eigener_kodierer=enc.running(), bilder=enc.frames, schluesselbilder=enc.keys,
                                 zuschauer_streamer=len(enc.users), fehler=enc.error)
        return out


# ---------------------------------------------------------------- Web

def allowed(request):
    ip = (request.remote or "").split("%")[0]
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(a in n for n in NETS)


@web.middleware
async def guard(request, handler):
    if not allowed(request):
        log.warning("abgelehnt: %s %s", request.remote, request.path)
        raise web.HTTPForbidden(text="Dieses Gerät ist nicht freigegeben (ALLOW).")
    return await handler(request)


def sdp_cands(sdp, limit=4):
    """Kandidaten aus einer SDP kurz: „192.168.1.50:51234/udp host“."""
    out = []
    for line in str(sdp).splitlines():
        if line.startswith("a=candidate:"):
            p = line.split()
            if len(p) >= 8:
                out.append("%s:%s/%s %s" % (p[4], p[5], p[2].lower(), p[7]))
    return out[:limit]


def sdp_codecs(sdp):
    """Videoformate einer SDP kurz (Fehlersuche): H.264-Varianten als Nutzlasttyp:Profil/Paketierung, andere Formate nur
    mit Namen, dazu ssrc und Kopferweiterungen – z. B. „H264 102:42001f/1 125:42e01f/1; sonst VP8 VP9“."""
    rtpmap, fmtp, order, ssrc, ext = {}, {}, [], None, []
    for line in str(sdp).splitlines():
        line = line.strip()
        if line.startswith("m=video") and not order:
            order = line.split()[3:]
        elif line.startswith("a=rtpmap:"):
            pt, _, rest = line[9:].partition(" ")
            rtpmap.setdefault(pt, rest.split("/")[0])
        elif line.startswith("a=fmtp:"):
            pt, _, rest = line[7:].partition(" ")
            fmtp.setdefault(pt, dict(kv.strip().lower().split("=", 1) for kv in rest.split(";") if "=" in kv))
        elif line.startswith("a=ssrc:") and ssrc is None:
            ssrc = line[7:].split()[0]
        elif line.startswith("a=extmap:") and len(line.split()) > 1:
            uri = line.split()[1]
            ext.append("twcc" if "transport-wide-cc" in uri else uri.replace(":", "/").rstrip("/").split("/")[-1][:20])
    h264, other = [], []
    for pt in order:
        name = rtpmap.get(pt, "")
        if not name or name.lower() in ("rtx", "red", "ulpfec", "flexfec-03"):
            continue
        if name.upper() == "H264":
            f = fmtp.get(pt, {})
            h264.append("%s:%s/%s" % (pt, f.get("profile-level-id", "?"), f.get("packetization-mode", "0")))
        else:
            other.append(name)
    text = ("H264 " + " ".join(h264)) if h264 else "kein H264"
    if other:
        text += "; sonst " + " ".join(other)
    if ssrc:
        text += "; ssrc " + ssrc
    return text, ext


def page(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return fh.read()


def page_version(html=None):
    """Fassung für die Empfangsseite: FASSUNG plus Prüfsumme von client.html – ändert sich nur die Seite, lädt sie neu."""
    return "%s-%08x" % (FASSUNG, zlib.crc32((html if html is not None else page("client.html")).encode("utf-8")) & 0xffffffff)


async def index(request):
    rtc = request.app["webrtc"]
    cfg = {"name": CFG["name"], "w": CFG["width"], "h": CFG["height"], "zoom": CFG["zoom"], "links": sorted(CFG["links"].keys()),
           "video_tv": CFG["video_tv"], "video_pc": CFG["video_pc"], "webrtc": rtc.enabled, "quellen": sorted(rtc.sources),
           "webrtc_tv": CFG["webrtc_tv"], "ton": CFG["audio"], "jpeg": JPEG_OK, "jpeg_tv": CFG["jpeg_tv"],
           "fassung": ""}
    html = page("client.html")
    cfg["fassung"] = page_version(html)
    html = html.replace("/*CFG*/{}", json.dumps(cfg))
    return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})


async def clock(request):
    return web.Response(text=page("clock.html"), content_type="text/html", headers={"Cache-Control": "no-store"})


async def negotiate(ws, rtc, v, m):
    """WebRTC aushandeln: Angebot der Empfangsseite an go2rtc, Antwort zurück (alles über den Video-WebSocket).
    Mit eigenem Kodierer: erst Kodierer starten (go2rtc braucht Bilder), nach der Antwort Schlüsselbilder schicken –
    sobald die Verbindung steht, kann der Empfänger damit anfangen (vorher verwirft go2rtc die Pakete)."""
    q = str(m.get("quelle", "")).strip().lower()
    src = q if q.startswith("bild_") else "bild_" + q
    if src not in rtc.sources:
        src = "bild"
    offer = str(m.get("sdp", ""))
    try:
        await rtc.join(v, src)
        sdp = await rtc.answer(offer, src)
        v.stats["quelle"] = src
        await ws.send_str(json.dumps({"type": "answer", "sdp": sdp}))
        log.info("WebRTC ausgehandelt: %s (%s) – Angebot %s, Antwort %s", v.ip, src, sdp_cands(offer), sdp_cands(sdp, 2))
        oc, _ = sdp_codecs(offer)
        ac, ae = sdp_codecs(sdp)
        v.stats["sdp"] = "%s | %s" % (ac, ",".join(ae) or "-")
        log.info("WebRTC-Formate %s: Angebot %s | Antwort %s | Erweiterungen %s", v.ip, oc, ac, ",".join(ae) or "-")
        if rtc.own:
            loop = asyncio.get_running_loop()
            for d in (0.5, 1.2, 2.5):
                loop.call_later(d, rtc.key, v)
        asyncio.ensure_future(rtc.check(v.ip, src))
    except Exception as e:
        log.warning("WebRTC-Aushandlung mit %s fehlgeschlagen: %s", v.ip, e)
        try:
            await ws.send_str(json.dumps({"type": "error", "text": str(e)[:200]}))
        except Exception:
            pass


async def ws_video(request):
    # .34: ohne permessage-deflate – Video und JPEG sind schon komprimiert; der Fernseher musste bisher jedes Stück entpacken
    ws = web.WebSocketResponse(heartbeat=10, max_msg_size=1 << 16, compress=False)
    await ws.prepare(request)
    if not CFG["browser_bild"]:      # .37j: Bild für den Fernseher-Browser (MSE/WebRTC/JPEG) abgeschaltet – Moonlight übernimmt
        await ws.send_str(json.dumps({"type": "hint", "text": "Browser-Bild ist abgeschaltet (BROWSER_BILD=0) – bitte Moonlight nutzen"}))
        await ws.close()
        return ws
    video, rtc = request.app["video"], request.app["webrtc"]
    mode = request.query.get("mode")
    mode = mode if mode in ("webrtc", "jpeg") else "mse"
    if mode == "jpeg" and not JPEG_OK:        # ohne PyAV kein JPEG – die Seite sieht am „init“, dass es MSE wurde
        mode = "mse"
    if mode == "mse" and not video.mse_viewers():
        # Bildrate je Verbindung: ?fps=60 zum Ausprobieren, sonst FPS aus der Einstellung (gilt für alle MSE-Zuschauer)
        try:
            want = int(request.query.get("fps", CFG["fps"]))
        except ValueError:
            want = CFG["fps"]
        want = want if 10 <= want <= 60 else CFG["fps"]
        if want != video.fps:
            log.info("MSE-Bildrate %d → %d", video.fps, want)
            video.fps = want
            video.restart()
        ton = request.query.get("ton") == "1" and pulse_ready()   # .30: Ton im MSE-Strom (gilt für alle MSE-Zuschauer)
        if ton != video.audio:
            log.info("MSE-Strom %s Ton (erster Zuschauer %s)", "mit" if ton else "ohne", request.remote)
            video.audio = ton
            video.restart()
    v = Viewer(ws, request.remote, mode)
    video.add(v)
    log.info("Fernseher verbunden: %s per %s (%d zuschauend)", request.remote, mode.upper(), len(video.viewers))
    sender, enc = None, None
    try:
        if mode == "jpeg":
            def num(key, default, lo, hi):
                try:
                    x = int(request.query.get(key, default))
                except ValueError:
                    x = default
                return max(lo, min(hi, x))
            enc = request.app["jpeg"].get(str(request.query.get("jpeg", CFG["jpeg_tv"])).lower(),
                                          num("q", CFG["jpeg_q"], 2, 31), num("jfps", CFG["fps"], 5, 60))
            v.jmax = num("vorrat", CFG["jpeg_vorrat"], 1, 6)
            await ws.send_str(json.dumps({"type": "init", "mode": "jpeg", "w": enc.size[0], "h": enc.size[1], "q": enc.q,
                                          "fps": enc.fps, "vorrat": v.jmax, "fassung": page_version()}))
            v.stats["quelle"] = "jpeg " + enc.key
            enc.join(v)
            sender = asyncio.ensure_future(jpeg_send(ws, v, enc))
        elif mode == "webrtc":
            await ws.send_str(json.dumps({"type": "init", "mode": "webrtc", "webrtc": rtc.enabled, "schluesselbild": rtc.own,
                                          "w": CFG["width"], "h": CFG["height"], "fps": CFG["fps"], "fassung": page_version()}))
        else:
            await asyncio.wait_for(video.init_evt.wait(), 20)
            await ws.send_str(json.dumps({"type": "init", "mode": "mse", "codec": video.codec,
                                          "w": CFG["width"], "h": CFG["height"], "fps": video.fps, "fassung": page_version()}))
            await ws.send_bytes(video.init)
            v.ready = True

            async def send_loop():
                while True:
                    d = await v.q.get()
                    if isinstance(d, str):
                        await ws.send_str(d)
                    else:
                        await ws.send_bytes(d)
            sender = asyncio.ensure_future(send_loop())
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    m = json.loads(msg.data)
                except ValueError:
                    continue
                if m.get("type") == "stats":
                    v.stats.update({k: m[k] for k in m if k != "type"})
                elif m.get("type") == "offer" and mode == "webrtc":
                    asyncio.ensure_future(negotiate(ws, rtc, v, m))
                elif m.get("type") == "ja" and enc is not None:      # JPEG: Seite hat ein Bild angezeigt (z=1) oder ausgelassen
                    v.jflight = max(0, v.jflight - 1)
                    t = v.jsent.pop(m.get("n"), None)
                    if t is not None and m.get("z"):
                        d = time.time() * 1000.0 - t       # Aufnahme → angezeigt → Antwort zurück (alles auf der Uhr des Streamers)
                        v.jdelay = d if v.jdelay is None else v.jdelay * 0.8 + d * 0.2
                    enc.update_want()
                    v.jev.set()
                elif m.get("type") == "key" and mode == "webrtc":     # Empfänger braucht ein Schlüsselbild
                    if rtc.key(v):
                        v.stats["schluesselbild_abrufe"] = v.stats.get("schluesselbild_abrufe", 0) + 1
            elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                break
    except asyncio.TimeoutError:
        log.error("Video startet nicht (kein Bild vom Kodierer)")
    finally:
        if sender:
            sender.cancel()
        if enc is not None:
            enc.leave(v)
            log.info("JPEG-Zuschauer %s nach %d s weg: %d Bilder geschickt (%.1f MB), bis zur Anzeige zuletzt %s ms, ohne Antwort %d×",
                     request.remote, int(time.time() - v.since), v.jcount, v.jbytes / 1e6,
                     "?" if v.jdelay is None else int(v.jdelay), v.jlate)
        rtc.leave(v)
        video.remove(v)
        log.info("Fernseher getrennt: %s (%d zuschauend)", request.remote, len(video.viewers))
        if mode == "webrtc":    # Fehlersuche: was die Empfangsseite zuletzt gemeldet hat (Rückfall, Abbruch)
            keys = ("bilder", "bilder_s", "pakete", "paar_kb", "transport_kb", "paketverlust", "nack", "pli", "pc", "ice", "dtls",
                    "paar", "schluesselbild_anfragen", "letzter_rueckfall", "jitter_ms", "empfang", "chiffre", "spur", "sdp")
            log.info("WebRTC-Zuschauer %s nach %d s weg: %s", request.remote, int(time.time() - v.since),
                     json.dumps({k: v.stats[k] for k in keys if k in v.stats}, ensure_ascii=False))
    return ws


async def jpeg_send(ws, v, enc):
    """Bildweg JPEG: das jeweils neueste Bild schicken, sobald die Seite bereit ist (höchstens v.jmax unterwegs). Vor dem Bild
    12 Bytes: Aufnahmezeit (ms, Uhr des Streamers, double) und Bildnummer (uint32), beides big-endian."""
    last_info = 0.0
    while not ws.closed:
        fr = enc.frame
        if not (fr and fr[0] > v.jseq and v.jflight < v.jmax):
            v.jev.clear()
            try:
                await asyncio.wait_for(v.jev.wait(), 3)
            except asyncio.TimeoutError:
                if v.jflight >= v.jmax:          # 3 s keine Antwort der Seite → nicht ewig warten
                    v.jflight = 0
                    v.jlate += 1
                    enc.update_want()
            continue
        v.jseq = fr[0]
        v.jflight += 1
        v.jsent[fr[0]] = fr[1]
        while len(v.jsent) > 32:
            v.jsent.popitem(last=False)
        enc.update_want()
        try:
            await ws.send_bytes(struct.pack(">dI", fr[1], fr[0]) + fr[2])
            v.jcount += 1
            v.jbytes += len(fr[2])
            now = time.time()
            if v.jdelay is not None and now - last_info >= 1:   # gemessene Verzögerung für die Einblendung (?debug=1)
                last_info = now
                v.stats["jpeg_bis_anzeige_ms"] = int(v.jdelay)
                v.stats["jpeg_ohne_antwort"] = v.jlate
                await ws.send_str(json.dumps({"type": "jd", "ms": int(v.jdelay)}))
        except (ConnectionError, RuntimeError):      # Seite weg – ws_video räumt auf
            return


async def ws_input(request):
    ws = web.WebSocketResponse(heartbeat=10, max_msg_size=1 << 16)
    await ws.prepare(request)
    cdp = request.app["cdp"]
    request.app["eingaben"].add(ws)          # bekommt Meldungen „Textfeld auf/zu“ (.27)
    try:
        if cdp.feld.get("an"):
            await ws.send_str(json.dumps(dict(cdp.feld, type="tastatur")))
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    cdp.input(json.loads(msg.data))
                except (ValueError, TypeError, KeyError):
                    pass
            elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                break
    finally:
        request.app["eingaben"].discard(ws)
    return ws


def tell_inputs(app, d, typ="tastatur"):
    """An alle verbundenen Empfangsseiten (über ihren Eingabe-WebSocket): Textfeld auf/zu, seit .30 auch kurze Hinweise."""
    data = json.dumps(dict(d, type=typ))
    for ws in list(app["eingaben"]):
        if not ws.closed:
            asyncio.ensure_future(ws.send_str(data))


# ---------------------------------------------------------------- Seiten-Wächter (.23)

# Liest alle <video> der HA-Seite (auch in Shadow-DOMs): Bilder bisher, seit wann keins mehr dazukam, sichtbar oder nicht.
# Verdeckte Videos zählen nicht (ihre Uhr läuft erst ab dem Sichtbarwerden). Merkt sich je Video den Stand in window.__tvw.
SEITE_JS = r"""(() => {
  const now = Date.now();
  const W = window.__tvw || (window.__tvw = { m: new WeakMap(), n: 0, t0: now });
  const vids = [];
  const walk = (root) => { for (const e of root.querySelectorAll('*')) { if (e.localName === 'video') { vids.push(e); } if (e.shadowRoot) { walk(e.shadowRoot); } } };
  walk(document);
  const out = [];
  for (const v of vids) {
    const r = v.getBoundingClientRect();
    const shown = r.width > 60 && r.height > 40 && r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth &&
      v.getClientRects().length > 0 && getComputedStyle(v).visibility !== 'hidden';
    const q = v.getVideoPlaybackQuality ? v.getVideoPlaybackQuality().totalVideoFrames : 0;
    let s = W.m.get(v);
    if (!s) { s = { id: ++W.n, t0: now, f: q, ct: v.currentTime, tc: now, lief: false }; W.m.set(v, s); v.dataset.tvw = String(s.id); }
    if (q !== s.f || (!q && v.currentTime !== s.ct)) { s.f = q; s.ct = v.currentTime; s.tc = now; s.lief = true; }
    if (!shown) { s.tc = now; continue; }
    const host = v.getRootNode().host;
    out.push({ id: s.id, spieler: host ? host.localName : '', art: v.srcObject ? 'webrtc' : ((v.currentSrc || v.src) ? 'mse' : 'leer'),
      bilder: q, steht_s: Math.round((now - s.tc) / 1000), alter_s: Math.round((now - s.t0) / 1000), lief: s.lief,
      rs: v.readyState, pause: v.paused, w: Math.round(r.width), h: Math.round(r.height) });
  }
  const ha = document.querySelector('home-assistant'), hass = ha && ha.hass;
  return { videos: out, seite_s: Math.round((now - W.t0) / 1000), sprache: hass ? hass.language : null };
})()"""

# Kamera-Player (ha-web-rtc-player / ha-hls-player) aus der Seite nehmen und sofort wieder einhängen: Er räumt beim
# Herausnehmen seinen Stream ab und baut beim Einhängen einen neuen auf – wie beim Ein- und Ausblenden einer Karte.
NEU_JS = r"""((id) => {
  let hit = null;
  const walk = (root) => { for (const e of root.querySelectorAll('*')) { if (e.localName === 'video' && e.dataset.tvw === String(id)) { hit = e; } if (e.shadowRoot) { walk(e.shadowRoot); } } };
  walk(document);
  if (!hit) { return 'weg'; }
  const host = hit.getRootNode().host;
  if (!host || !host.parentNode) { return 'ohne Player'; }
  const p = host.parentNode, n = host.nextSibling;
  p.removeChild(host); p.insertBefore(host, n);
  const s = window.__tvw && window.__tvw.m.get(hit); if (s) { s.tc = Date.now(); }
  return host.localName;
})(%d)"""

# HA-Sprache wie im Profil umstellen (Ereignis „hass-language-select“ am home-assistant-Element; HA speichert die Wahl
# für den angemeldeten Benutzer)
SPRACHE_JS = r"""((lang) => {
  const ha = document.querySelector('home-assistant');
  if (!ha || !ha.hass) { return 'ohne HA'; }
  ha.dispatchEvent(new CustomEvent('hass-language-select', { detail: lang, bubbles: true, composed: true }));
  return 'gewählt';
})(%s)"""

WACHE = {"kameras": [], "player_neu": 0, "seite_neu": 0, "sprache": None}


async def watch_page(app):
    """Alle 10 s, solange jemand zuschaut und der HA-Reiter vorn ist: stehende Kamerabilder neu starten, HA-Sprache prüfen."""
    cdp, video = app["cdp"], app["video"]
    reloads = collections.deque(maxlen=3)
    restarted, last_age, lang_tries = {}, 0, 0
    while True:
        await asyncio.sleep(10)
        tid = cdp.tabs.get("home")
        sid = cdp.sessions.get(tid)
        if not sid or cdp.parked or cdp.target != tid or not video.viewers:
            continue
        try:
            r = await cdp.call("Runtime.evaluate", {"expression": SEITE_JS, "returnByValue": True}, sess=sid, timeout=5)
            d = (((r or {}).get("result") or {}).get("value"))
        except Exception:
            d = None
        if not isinstance(d, dict):
            continue
        if (d.get("seite_s") or 0) < last_age:      # Seite neu geladen → neue Nummern
            restarted = {}
        last_age = d.get("seite_s") or 0
        vids = d.get("videos") or []
        WACHE["kameras"] = [{k: x.get(k) for k in ("spieler", "art", "bilder", "steht_s", "w", "h")} for x in vids]
        WACHE["sprache"] = d.get("sprache")
        want = CFG["ha_sprache"]
        if want and d.get("sprache") and d["sprache"] != want and lang_tries < 3:
            lang_tries += 1
            try:
                res = await cdp.call("Runtime.evaluate", {"expression": SPRACHE_JS % json.dumps(want), "returnByValue": True},
                                     sess=sid, timeout=5)
            except Exception as e:
                res = e
            log.warning("HA-Sprache des angemeldeten Benutzers ist „%s“ → auf „%s“ gestellt (Versuch %d: %s)", d["sprache"], want,
                        lang_tries, (((res or {}).get("result") or {}).get("value")) if isinstance(res, dict) else res)
        now = time.time()
        for x in vids:
            if (x.get("steht_s") or 0) < 20 or (x.get("alter_s") or 0) < 25:
                continue
            last = restarted.get(x["id"], 0)
            if now - last > 60:
                restarted[x["id"]] = now
                try:
                    res = await cdp.call("Runtime.evaluate", {"expression": NEU_JS % int(x["id"]), "returnByValue": True},
                                         sess=sid, timeout=5)
                    res = ((res or {}).get("result") or {}).get("value")
                except Exception as e:
                    res = e
                WACHE["player_neu"] += 1
                log.warning("Kamerabild steht seit %d s (%s, %s, %d Bilder, %sx%s) → Player neu eingehängt: %s", x["steht_s"],
                            x.get("spieler"), x.get("art"), x.get("bilder") or 0, x.get("w"), x.get("h"), res)
            elif now - last > 25 and (not reloads or now - reloads[-1] > 600):
                reloads.append(now)
                WACHE["seite_neu"] += 1
                log.warning("Kamerabild steht weiter (%d s, %s) → HA-Seite wird neu geladen", x["steht_s"], x.get("spieler"))
                cdp.send("Page.reload", {"ignoreCache": False}, sess=sid)
                break


def mem_info():
    """Speicher der VM (der Container sieht /proc/meminfo der VM) und von Chromium (privater Speicher seiner Prozesse)."""
    d = {}
    try:
        with open("/proc/meminfo") as fh:
            m = {}
            for line in fh:
                k, _, rest = line.partition(":")
                if k in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
                    m[k] = int(rest.split()[0])
        d = {"frei_mb": m.get("MemAvailable", 0) // 1024, "gesamt_mb": m.get("MemTotal", 0) // 1024}
        if m.get("SwapTotal"):
            d["swap_belegt_mb"] = (m["SwapTotal"] - m.get("SwapFree", 0)) // 1024
    except (OSError, ValueError, IndexError):
        pass
    rss = 0
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open("/proc/%s/status" % pid) as fh:
                txt = fh.read()
        except OSError:
            continue
        if not txt.startswith("Name:\tchrom"):
            continue
        vals = dict(l.split(":", 1) for l in txt.splitlines() if l.startswith(("RssAnon:", "VmRSS:")))
        try:
            rss += int((vals.get("RssAnon") or vals.get("VmRSS") or "0 kB").split()[0])
        except ValueError:
            pass
    d["chromium_mb"] = rss // 1024
    try:
        d["last"] = round(os.getloadavg()[0], 1)
    except OSError:
        pass
    return d


def status_data(app):
    video, cdp = app["video"], app["cdp"]
    rtc_viewers = [v for v in video.viewers if v.mode == "webrtc"]
    jpeg_info = app["jpeg"].info()
    if video.proc:
        fps, kbit, fmt = video.rate["fps"], video.rate["kbit_s"], video.codec
    elif rtc_viewers:   # WebRTC: go2rtc kodiert – Bildrate und Datenrate meldet die Empfangsseite
        fps = rtc_viewers[0].stats.get("bilder_s") or 0
        kbit = int((rtc_viewers[0].stats.get("mbit_s") or 0) * 1000)
        fmt = "H.264 (WebRTC, %s, %s)" % (CFG["webrtc_profile"], "Schlüsselbild auf Abruf" if app["webrtc"].own else "go2rtc exec")
    elif jpeg_info:     # .32: JPEG – Bildrate = verschickte (geänderte) Bilder/s
        e = list(jpeg_info.values())[0]
        fps, kbit = e.get("neu_s") or 0, int((e.get("neu_s") or 0) * (e.get("kb_bild") or 0) * 8)
        fmt = "JPEG %s, Qualität %s" % (e["bild"], e["qualitaet"])
    else:
        fps, kbit, fmt = 0, 0, None
    return {
        "name": CFG["name"], "fassung": FASSUNG, "quelle": QUELLE, "url": cdp.url, "reiter": cdp.tab_name(), "reiter_alle": sorted(cdp.tabs), "steuerung": bool(cdp.sess),
        "ruht": bool(cdp.parked), "bild": "%dx%d (Zoom %s)" % (CFG["width"], CFG["height"], CFG["zoom"]),
        "kodierer": bool(video.proc) or bool(rtc_viewers) or bool(jpeg_info), "format": fmt, "bilder_s": fps, "kbit_s": kbit,
        "jpeg": jpeg_info,
        "zuschauer": [dict(v.stats, ip=v.ip, weg=v.mode, seit_s=int(time.time() - v.since)) for v in video.viewers],
        "seite": dict(WACHE), "speicher": mem_info(),
        "ton": {"an": CFG["audio"], "senke": pulse_ready(), "mse_mit_ton": bool(video.proc) and video.audio_on},
        "zugang_gespeichert": bool(cdp.zugang_lesen()),
        "cpu": app.get("cpu"), "leistung": app.get("leistung"), "ruhig": cdp.ruhig,
        "popup": cdp.popup_ergebnisse[-20:],
        "moonlight": {"an": CFG["moonlight"], "stream": getattr(video, "moonlight", False),
                      "uuid": moonlight_uuid() if CFG["moonlight"] else "", "apps": moonlight_apps() if CFG["moonlight"] else {}},
    }


async def status(request):
    d = status_data(request.app)
    d["webrtc"] = await request.app["webrtc"].info() if request.app["webrtc"].enabled else "aus"
    d["mse_bilder_s_einstellung"] = request.app["video"].fps
    return web.json_response(d)


# Tasten des angepassten Moonlight (Repo-Ordner moonlight/) → Namen des Ereignisses tv_streamer_key in Home Assistant
FERNBEDIENUNG = {"F13": "blue", "F14": "green", "F15": "play", "F16": "stop", "F17": "pause", "MediaPlayPause": "play", "MediaStop": "stop"}


async def ha_taste(name):
    """Eine Taste der Fernbedienung sofort an Home Assistant melden (die Integration feuert tv_streamer_key)."""
    if not CFG["ha_webhook"]:
        return
    try:
        async with ClientSession(timeout=ClientTimeout(total=5)) as s:
            async with s.post(CFG["ha_webhook"], json={"name": CFG["name"], "taste": name}) as r:
                if r.status >= 300:
                    log.warning("Taste an Home Assistant: HTTP %s", r.status)
    except Exception as e:
        log.warning("Taste an Home Assistant fehlgeschlagen: %s", e)


async def report(app):
    """Messwerte an Home Assistant melden (Webhook im Heimnetz): alle 30 s, solange ein Fernseher zuschaut,
    sofort, wenn sich etwas Grundlegendes ändert (Zuschauer, Kodierer an/aus, HA-Reiter ruht), und sonst alle 5 min
    ein Lebenszeichen – damit die Entitäten in HA nach einer verlorenen Meldung (z. B. HA-Neustart) wieder stimmen."""
    if not CFG["ha_webhook"]:
        return
    last, last_sent, seen = None, 0, 0
    popup_seen = 0
    rtc = app["webrtc"]
    async with ClientSession(timeout=ClientTimeout(total=5)) as s:
        while True:
            await asyncio.sleep(5)
            for enc in rtc.encoders.values():          # Wächter: läuft der eigene Kodierer, kommen auch Bilder?
                if enc.running() and enc.users and enc.frames == getattr(enc, "seen", -1) and time.time() - enc.run["t0"] > 8:
                    log.warning("WebRTC-Kodierer %s: seit 5 s kein neues Bild (bei %d)", enc.name, enc.frames)
                enc.seen = enc.frames
            d = status_data(app)
            neu = [x for x in app["cdp"].popup_ergebnisse if x.get("n", 0) > popup_seen]
            d["popup"] = neu
            if getattr(app["video"], "moonlight", False):   # .37h: Moonlight-Stream zählt für HA als Zuschauer „moonlight“
                d["zuschauer"] = list(d["zuschauer"]) + [{"ip": "moonlight"}]
            key = (len(d["zuschauer"]), d["kodierer"], d["ruht"], d["reiter"])
            alter = time.time() - last_sent
            if key == last and not (d["zuschauer"] and alter >= 30) and alter < 300 and RECENT.warn_seq <= seen and not neu:
                continue
            if neu:
                popup_seen = max(x.get("n", 0) for x in neu)
            last, last_sent = key, time.time()
            d["meldungen"] = RECENT.since(seen)
            seen = RECENT.seq
            if rtc.enabled and (d["zuschauer"] or d["meldungen"]):
                d["webrtc"] = await rtc.info()
            for z in d["zuschauer"]:
                z.pop("geraet", None)
                z.pop("browser", None)
            try:
                async with s.post(CFG["ha_webhook"], json=d) as r:
                    if r.status >= 300:
                        log.warning("Meldung an Home Assistant: HTTP %s", r.status)
            except Exception as e:
                log.warning("Meldung an Home Assistant fehlgeschlagen: %s", e)


async def command(request):
    try:
        m = await request.json()
    except ValueError:
        raise web.HTTPBadRequest(text="JSON erwartet")
    c = str(m.get("c", ""))
    if CFG["moonlight"] and str(m.get("app_id", "")).isdigit() and m.get("app_name"):   # .37j: Sunshine-App-IDs für den Direktstart
        moonlight_app_merken(str(m["app_name"])[:40], int(m["app_id"]))
    if c == "url" and str(m.get("url", "")).startswith(("http://", "https://")):
        request.app["cdp"].navigate(m["url"])
    elif c == "fps":    # Bildrate des MSE-Kodierers ausprobieren (bis zum nächsten Neustart des Containers)
        try:
            fps = int(m.get("fps", CFG["fps"]))
        except (TypeError, ValueError):
            raise web.HTTPBadRequest(text="fps: Zahl 10–60 erwartet")
        if not 10 <= fps <= 60:
            raise web.HTTPBadRequest(text="fps: Zahl 10–60 erwartet")
        video = request.app["video"]
        if fps != video.fps:
            log.info("MSE-Bildrate %d → %d (Kodierer startet neu)", video.fps, fps)
            video.fps = fps
            video.restart()
        return web.json_response({"ok": True, "fps": fps})
    elif c == "moonlight":    # .37: Sunshine meldet Stream-Start/-Ende (global_prep_cmd) – HA-Reiter wach halten
        video = request.app["video"]
        an = bool(m.get("an"))
        video.moonlight = an
        if an:
            if video.freeze_task and not video.freeze_task.done():
                video.freeze_task.cancel()
            await request.app["cdp"].rest(False)
            weg = time.time() - getattr(video, "moonlight_ende", 0)
            if weg > CFG["moonlight_startseite_s"]:   # .37n: nach längerer Pause wieder die HA-Startansicht (wie Loxone nach 5 min)
                await request.app["cdp"].command("startansicht")
                log.info("Moonlight-Stream an nach %d min – HA-Startansicht", int(weg // 60))
            log.info("Moonlight-Stream an – HA-Reiter bleibt wach")
        else:
            video.moonlight_ende = time.time()
            log.info("Moonlight-Stream aus")
            if not video.viewers and CFG["freeze_after"] > 0 and (not video.freeze_task or video.freeze_task.done()):
                video.freeze_task = asyncio.ensure_future(video._freeze_later())
        return web.json_response({"ok": True, "moonlight": an})
    else:
        await request.app["cdp"].command(c, m)
    return web.json_response({"ok": True})


async def shot(request):
    """Bildschirmfoto des virtuellen Bildschirms (Fehlersuche ohne Fernseher)."""
    p = await asyncio.create_subprocess_exec("ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "x11grab", "-draw_mouse", "0",
                                             "-video_size", "%dx%d" % (CFG["width"], CFG["height"]),
                                             "-i", CFG["display"] + ".0+0,0", "-frames:v", "1", "-f", "image2", "-c:v", "mjpeg",
                                             "-q:v", "3", "pipe:1", stdout=asyncio.subprocess.PIPE)
    data, _ = await p.communicate()
    return web.Response(body=data, content_type="image/jpeg", headers={"Cache-Control": "no-store"})


async def main():
    log.info("TV-Streamer „%s“: %dx%d, Zoom %s → Seite %dx%d Punkte, Start %s",
             CFG["name"], CFG["width"], CFG["height"], CFG["zoom"],
             round(CFG["width"] / CFG["zoom"]), round(CFG["height"] / CFG["zoom"]), CFG["start_url"])
    cdp = Cdp()
    video = Video(cdp)
    if CFG["freeze_after"] > 0:   # auch nach dem Start ruhen lassen, solange niemand zuschaut
        video.freeze_task = asyncio.ensure_future(video._freeze_later())
    asyncio.ensure_future(supervise("Xvfb", ["Xvfb", CFG["display"], "-screen", "0", "%dx%dx24" % (CFG["width"], CFG["height"]),
                                             "-nolisten", "tcp", "-ac", "-dpi", "96", "-noreset"]))   # .39: Tastenbelegung bleibt
    if not await wait_for_x():
        log.error("Xvfb startet nicht")
    else:
        await tasten_belegen()
    ton_env = {}
    if CFG["audio"]:          # .30: Senke vor Chromium starten – Chromium und die Ton-Kodierer finden sie über PULSE_SERVER
        if shutil.which("pulseaudio"):
            asyncio.ensure_future(supervise("PulseAudio", pulse_argv, extra_env=PULSE_ENV))
            for _ in range(50):
                if os.path.exists(PULSE_SOCK):
                    break
                await asyncio.sleep(0.1)
            log.info("Ton: PulseAudio-Senke „tv“ %s", "bereit" if os.path.exists(PULSE_SOCK) else "nicht erreichbar")
            ton_env = PULSE_ENV
        else:
            log.warning("Ton: pulseaudio fehlt im Image – weiter ohne Ton")
    chrome_env = dict(ton_env)
    if CFG["chromium_language"]:
        chrome_env["LANGUAGE"] = CFG["chromium_language"]
    asyncio.ensure_future(supervise("Chromium", chromium_argv, extra_env=chrome_env or None))
    asyncio.ensure_future(cdp.run())
    rtc = WebRtc()
    if rtc.enabled:
        asyncio.ensure_future(supervise("go2rtc", rtc.argv, echo=True, extra_env=ton_env or None))
        log.info("WebRTC über go2rtc: Port %d (im Container %d), Adresse %s", CFG["webrtc_port"], CFG["webrtc_listen"],
                 CFG["public_ip"] or "(nur Container-Adresse)")

    app = web.Application(middlewares=[guard])
    app["cdp"], app["video"], app["webrtc"] = cdp, video, rtc
    app["jpeg"] = JpegPool()
    app["eingaben"] = set()
    cdp.on_feld = lambda d: tell_inputs(app, d)
    cdp.on_hint = lambda t: tell_inputs(app, {"text": t}, "hinweis")
    app.router.add_get("/", index)
    app.router.add_get("/clock", clock)
    app.router.add_get("/ws/video", ws_video)
    app.router.add_get("/ws/input", ws_input)
    app.router.add_get("/api/status", status)
    app.router.add_post("/api/cmd", command)
    app.router.add_get("/api/shot.jpg", shot)
    asyncio.ensure_future(report(app))
    asyncio.ensure_future(messwerte(app))
    if CFG["seiten_waechter"]:
        asyncio.ensure_future(watch_page(app))
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", CFG["port"]).start()
    log.info("bereit: http://<diese-IP>:%d/", CFG["port"])
    if CFG["moonlight"]:
        sun = sunshine_einrichten()
        if sun:
            asyncio.ensure_future(supervise("Sunshine", sun[0], extra_env=sun[1]))
            asyncio.ensure_future(sunshine_ton_pruefen())
            log.info("Moonlight: Sunshine gestartet (Aufnahme %s, Software-x264); Web-UI https://<VM>:47990", CFG["display"])

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()
    global STOPPING
    STOPPING = True
    log.info("beende – Chromium, Xvfb und Kodierer werden geschlossen")
    for enc in rtc.encoders.values():
        enc.halt()
    for p in list(CHILDREN):
        if p.returncode is None:
            p.terminate()
    for _ in range(30):
        if all(p.returncode is not None for p in CHILDREN):
            break
        await asyncio.sleep(0.1)
    for p in list(CHILDREN):
        if p.returncode is None:
            p.kill()
    await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

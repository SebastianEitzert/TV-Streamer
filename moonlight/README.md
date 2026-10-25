# Moonlight for webOS – TV Streamer build

🇩🇪 Deutsche Kurzfassung unten.

A patched build of [Moonlight TV](https://github.com/mariotaku/moonlight-tv) (GPL-3.0) for LG webOS TVs. The changes are
small patches in [`patches/`](patches/) against the upstream release in [`UPSTREAM`](UPSTREAM); the GitHub Action
[`moonlight-webos.yml`](../.github/workflows/moonlight-webos.yml) builds the `.ipk`.

| Remote key | Official Moonlight | This build | TV Streamer does |
|---|---|---|---|
| Blue | ignored while streaming | sends **F13** | show Home Assistant (already there: start page); HA event `tv_streamer_key` = `blue` |
| Green | ignored while streaming | sends **F14** | show the first extra tab (e.g. Loxone) – selectable in the general settings; event `green` |
| Play | ignored | sends **F15** (Sunshine on Linux drops media keys) | event `play` (use it in an automation, e.g. start the music) |
| Pause | ignored | sends **F17** | event `pause` |
| Stop | ignored | sends **F16** | event `stop` |
| Yellow | right click only if a click in Moonlight's own UI came first, else a menu key Sunshine drops | always a **right click** | floor plan: music on/off over a room, twice: room off |
| Arrow keys | pointer disappears until the remote is shaken | pointer switched back on when webOS hides it | arrows go to the page (e.g. floor switch) |

The app id stays `com.limelight.webos`, so it installs **over** the official app; host pairings and settings stay.
In the TV's app list it is called **Moonlight TVS** – that is how you see the patched build is installed.

**After installing, switch the TV off at the mains (or restart it).** If Moonlight was still loaded in the background,
webOS keeps running the old version until then.

## Install
1. Download `com.limelight.webos_<version>-tvstreamer_arm.ipk` from the
   [releases](https://github.com/SebastianEitzert/TV-Streamer/releases) (or from the latest workflow run's artifact).
2. webOS Dev Manager → **Apps → Install** → select the file (TV must be on and in developer mode).

## Automation example
```yaml
triggers:
  - trigger: event
    event_type: tv_streamer_key
    event_data: {streamer: schlafzimmer, key: pause}
actions:
  - action: media_player.media_pause
    target: {entity_id: media_player.bedroom_speaker}
```

## Build yourself
Run the workflow (*Actions → Moonlight for webOS → Run workflow*), or locally with the
[webOS NDK](https://github.com/openlgtv/buildroot-nc4): clone the upstream tag with submodules, `git apply` the patches,
then `TOOLCHAIN_FILE=… ./scripts/webos/easy_build.sh -DCMAKE_BUILD_TYPE=Release`.

The patches are offered upstream as well; if they are merged, this build is no longer needed.

---

## Deutsch (Kurzfassung)
Angepasste Fassung von Moonlight TV für LG webOS. **Blau** und **Grün** gehen an den Streamer (Home Assistant bzw. erster
zusätzlicher Reiter), **Wiedergabe/Pause** und **Stopp** lösen in Home Assistant das Ereignis `tv_streamer_key` aus, und der
**Zeiger** ist nach den Pfeiltasten sofort wieder da, ohne die Fernbedienung zu schütteln. Installation über die offizielle
App mit dem webOS Dev Manager (*Apps → Installieren*, Fernseher an und im Entwicklermodus) – Kopplung und Einstellungen bleiben.
In der App-Liste heißt sie dann **Moonlight TVS**. **Danach den Fernseher einmal vom Strom nehmen** (oder neu starten) –
sonst läuft ein im Hintergrund geladenes altes Moonlight weiter.

"""Show the dashboard (or an extra tab) on the TV: wake it if needed, then open Moonlight or the TV browser."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.const import ATTR_COMMAND, ATTR_ENTITY_ID
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    CMD_START_VIEW,
    CONF_MEDIA_PLAYER,
    CONF_NAME,
    CONF_VIDEO_PATH,
    CONF_WAKE,
    DOMAIN,
    MOONLIGHT_APP,
    TV_OFF_STATES,
    VIDEO_MOONLIGHT,
    WAKE_SETTLE,
    WAKE_TIMEOUT,
)

if TYPE_CHECKING:
    from .coordinator import StreamerCoordinator

_LOGGER = logging.getLogger(__name__)

# Sunshine app that belongs to the Home Assistant tab (server.py creates it under this name)
HOME_APP = "Home Assistant"


def check_can_show(hass: HomeAssistant, coordinator: StreamerCoordinator) -> None:
    """Raise before starting if the TV cannot be reached at all."""
    streamer = coordinator.streamer
    tv = streamer.get(CONF_MEDIA_PLAYER)
    if not tv:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="no_tv", translation_placeholders={"name": streamer[CONF_NAME]}
        )
    if _is_off(hass, tv) and not streamer.get(CONF_WAKE):
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="tv_off", translation_placeholders={"name": streamer[CONF_NAME]}
        )


async def async_show_on_tv(hass: HomeAssistant, coordinator: StreamerCoordinator, link: str | None) -> None:
    """Wake the TV if needed and show the start view (link=None) or an extra tab."""
    streamer = coordinator.streamer
    tv: str = streamer[CONF_MEDIA_PLAYER]
    command = f"link:{link}" if link else CMD_START_VIEW

    if _is_off(hass, tv):
        await _async_wake(hass, streamer[CONF_WAKE])
        if not await _async_wait_on(hass, tv):
            _LOGGER.warning("%s did not switch on within %s s", tv, WAKE_TIMEOUT)
            return
        await asyncio.sleep(WAKE_SETTLE)

    # Bring the right tab to the front first, so Moonlight or the browser opens on it.
    await _async_command(coordinator, command)

    if not _is_webos(hass, tv):
        return  # no app control for other TVs – the streamer has switched, that is all we can do
    if streamer.get(CONF_VIDEO_PATH) == VIDEO_MOONLIGHT:
        await _async_launch_moonlight(hass, coordinator, tv, link)
    else:
        url = coordinator.base_url + "/" + ("?reiter=bleiben" if link else "")
        await _async_webos(hass, tv, "system.launcher/open", {"target": url})


async def _async_launch_moonlight(
    hass: HomeAssistant, coordinator: StreamerCoordinator, tv: str, link: str | None
) -> None:
    """Start Moonlight directly with the streamer's Sunshine host and the matching app."""
    try:
        status = await coordinator._async_update_data()  # fresh uuid and app ids
    except UpdateFailed as err:
        _LOGGER.warning("Streamer status not available, starting Moonlight without host: %s", err)
        status = coordinator.data or {}
    moonlight = status.get("moonlight") or {}
    if moonlight.get("stream"):
        return  # Moonlight is already showing the streamer – switching the tab was enough
    uuid = moonlight.get("uuid") or ""
    apps = {str(k).lower(): v for k, v in (moonlight.get("apps") or {}).items()}
    app_id = int(apps.get((link or HOME_APP).lower(), 0) or 0)
    params: dict[str, Any] = {}
    if uuid:
        params["host_uuid"] = uuid
        if app_id:
            params["host_app_id"] = app_id
    await _async_webos(hass, tv, "system.launcher/launch", {"id": MOONLIGHT_APP, "params": params})
    if not app_id:
        # Moonlight opens the host list only; switch the tab again once the stream runs.
        await asyncio.sleep(10)
        await _async_command(coordinator, f"link:{link}" if link else "zeige_home")


async def _async_wake(hass: HomeAssistant, entity_id: str) -> None:
    domain = entity_id.split(".", 1)[0]
    service = {"button": "press", "input_button": "press"}.get(domain, "turn_on")
    await hass.services.async_call(domain, service, {ATTR_ENTITY_ID: entity_id}, blocking=True)


async def _async_wait_on(hass: HomeAssistant, entity_id: str) -> bool:
    """Wait until the media player reports itself on."""
    done = asyncio.Event()

    @callback
    def _changed(event: Event[EventStateChangedData]) -> None:
        if not _is_off(hass, entity_id):
            done.set()

    unsub = async_track_state_change_event(hass, [entity_id], _changed)
    try:
        if not _is_off(hass, entity_id):
            return True
        async with asyncio.timeout(WAKE_TIMEOUT):
            await done.wait()
        return True
    except TimeoutError:
        return False
    finally:
        unsub()


async def _async_command(coordinator: StreamerCoordinator, command: str) -> None:
    try:
        await coordinator.async_command(command)
    except UpdateFailed as err:
        _LOGGER.warning("%s", err)


async def _async_webos(hass: HomeAssistant, tv: str, command: str, payload: dict[str, Any]) -> None:
    await hass.services.async_call(
        "webostv", "command", {ATTR_ENTITY_ID: tv, ATTR_COMMAND: command, "payload": payload}, blocking=True
    )


def _is_off(hass: HomeAssistant, entity_id: str) -> bool:
    state = hass.states.get(entity_id)
    return state is None or state.state in TV_OFF_STATES


def _is_webos(hass: HomeAssistant, entity_id: str) -> bool:
    entry = er.async_get(hass).async_get(entity_id)
    return entry is not None and entry.platform == "webostv"

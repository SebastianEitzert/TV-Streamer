"""TV Streamer: Home Assistant dashboards streamed to TVs from a VM (MSE, WebRTC or Moonlight)."""

from __future__ import annotations

import logging
from datetime import time
from typing import Any

from aiohttp import web
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .api import async_register_views
from .compose import compose_version, render_compose
from .const import (
    CONF_HA_URL,
    CONF_ID,
    CONF_LG_RENEW_TIME,
    CONF_STREAMERS,
    CONF_WEBHOOK_ID,
    DEFAULT_LG_RENEW_TIME,
    DOMAIN,
    EVENT_KEY,
)
from .coordinator import StreamerCoordinator, TvStreamerData
from .streamer_files import files_manifest, load_streamer_files

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]

type TvStreamerConfigEntry = ConfigEntry[TvStreamerData]


async def async_setup_entry(hass: HomeAssistant, entry: TvStreamerConfigEntry) -> bool:
    """Set up the streamers of one VM."""
    webhook_url = entry.data[CONF_HA_URL].rstrip("/") + webhook.async_generate_path(entry.data[CONF_WEBHOOK_ID])
    compose_text = render_compose(entry.data, dict(entry.options), webhook_url)
    files = await hass.async_add_executor_job(load_streamer_files)
    manifest = files_manifest(files)
    data = TvStreamerData(
        compose_text=compose_text,
        compose_version=compose_version(compose_text + manifest),
        files=files,
        files_manifest=manifest,
    )

    for streamer in entry.options.get(CONF_STREAMERS, []):
        coordinator = StreamerCoordinator(hass, entry, streamer)
        # A streamer that is off must not block the setup – entities just show "unavailable".
        await coordinator.async_refresh()
        data.coordinators[streamer[CONF_ID]] = coordinator
    entry.runtime_data = data

    async_register_views(hass)
    webhook.async_register(
        hass, DOMAIN, f"TV Streamer {entry.title}", entry.data[CONF_WEBHOOK_ID], _handle_webhook, local_only=True
    )
    entry.async_on_unload(lambda: webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID]))

    lg = [c for c in data.coordinators.values() if c.lg_token]
    if lg:
        renew_at = dt_util.parse_time(entry.options.get(CONF_LG_RENEW_TIME) or DEFAULT_LG_RENEW_TIME) or time(4, 17)

        async def _renew_all(_now: Any) -> None:
            for coordinator in lg:
                await coordinator.async_lg_renew()

        entry.async_on_unload(
            async_track_time_change(hass, _renew_all, hour=renew_at.hour, minute=renew_at.minute, second=renew_at.second)
        )
        for coordinator in lg:
            entry.async_create_background_task(hass, coordinator.async_lg_check(), f"{DOMAIN} lg check")

    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TvStreamerConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: TvStreamerConfigEntry) -> None:
    """Options changed: rebuild compose file and entities (the VM picks the new file up within 5 minutes)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _handle_webhook(hass: HomeAssistant, webhook_id: str, request: web.Request) -> web.Response:
    """Status report from server.py (HA_WEBHOOK)."""
    try:
        payload = await request.json()
    except ValueError:
        return web.Response(status=400)
    _push(hass, webhook_id, payload if isinstance(payload, dict) else {})
    return web.Response(status=200)


@callback
def _push(hass: HomeAssistant, webhook_id: str, payload: dict[str, Any]) -> None:
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        if entry.data.get(CONF_WEBHOOK_ID) != webhook_id:
            continue
        coordinator = entry.runtime_data.coordinators.get(str(payload.get("name", "")))
        if coordinator and "taste" in payload:
            # A remote key from the patched Moonlight app – fire an event for automations, no status update.
            hass.bus.async_fire(
                EVENT_KEY,
                {"streamer": coordinator.streamer[CONF_ID], "key": str(payload["taste"])[:24], "entry_id": entry.entry_id},
            )
        elif coordinator:
            coordinator.async_push(payload)
        else:
            _LOGGER.debug("Report from unknown streamer %s", payload.get("name"))

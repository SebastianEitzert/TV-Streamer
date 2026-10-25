"""Runtime data: status of each streamer and the LG developer mode sessions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from aiohttp import ClientError, ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .compose import http_port
from .const import (
    CONF_HOST,
    CONF_ID,
    CONF_INDEX,
    CONF_LG_TOKEN,
    CONF_NAME,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
)
from .lg import LgError, async_check, async_renew

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = ClientTimeout(total=8)


class StreamerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls GET /api/status of one streamer; the webhook pushes in between."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, streamer: dict[str, Any]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {streamer[CONF_NAME]}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.streamer = streamer
        self.base_url = f"http://{entry.data[CONF_HOST]}:{http_port(streamer[CONF_INDEX])}"
        self.session = async_get_clientsession(hass)
        self.lg = LgSession()

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            async with self.session.get(f"{self.base_url}/api/status", timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                return await resp.json()
        except (ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"{self.streamer[CONF_NAME]} not reachable: {err}") from err

    @callback
    def async_push(self, payload: dict[str, Any]) -> None:
        """Merge a webhook report into the last status."""
        self.async_set_updated_data({**(self.data or {}), **payload})

    async def async_command(self, command: str, **extra: Any) -> None:
        """Send a command to server.py (POST /api/cmd)."""
        try:
            async with self.session.post(
                f"{self.base_url}/api/cmd", json={"c": command, **extra}, timeout=_TIMEOUT
            ) as resp:
                resp.raise_for_status()
        except (ClientError, TimeoutError) as err:
            raise UpdateFailed(f"{self.streamer[CONF_NAME]}: command {command} failed: {err}") from err

    # LG developer mode ------------------------------------------------------------

    @property
    def lg_token(self) -> str:
        return self.streamer.get(CONF_LG_TOKEN) or ""

    async def async_lg_renew(self) -> bool:
        """Renew the developer mode session, update sensors and the repair issue."""
        if not self.lg_token:
            return False
        lg = self.lg
        lg.last_attempt = dt_util.utcnow()
        try:
            result = await async_renew(self.session, self.lg_token)
        except LgError as err:
            lg.ok, lg.message = False, str(err)
        else:
            lg.ok, lg.message = result.ok, result.message
        if lg.ok:
            lg.last_renewal = lg.last_attempt
            await self.async_lg_check()
            ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
        else:
            _LOGGER.warning("LG developer mode for %s not renewed: %s", self.streamer[CONF_NAME], lg.message)
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self.issue_id,
                is_fixable=True,
                is_persistent=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="lg_renew_failed",
                translation_placeholders={"name": self.streamer[CONF_NAME], "message": lg.message[:200]},
                data={"entry_id": self.config_entry.entry_id, "streamer_id": self.streamer[CONF_ID]},
            )
        self.async_update_listeners()
        return lg.ok

    async def async_lg_check(self) -> None:
        """Read the remaining session time."""
        if not self.lg_token:
            return
        try:
            result = await async_check(self.session, self.lg_token)
        except LgError as err:
            _LOGGER.debug("LG check for %s failed: %s", self.streamer[CONF_NAME], err)
            return
        if result.ok and result.remaining is not None:
            self.lg.expires = dt_util.utcnow() + result.remaining
            self.async_update_listeners()

    @property
    def issue_id(self) -> str:
        return f"lg_renew_failed_{self.config_entry.entry_id}_{self.streamer[CONF_ID]}"


@dataclass
class LgSession:
    """Last known state of the developer mode session."""

    ok: bool | None = None
    message: str = ""
    last_attempt: datetime | None = None
    last_renewal: datetime | None = None
    expires: datetime | None = None


@dataclass
class TvStreamerData:
    """Stored in entry.runtime_data."""

    compose_text: str
    compose_version: str
    coordinators: dict[str, StreamerCoordinator] = field(default_factory=dict)

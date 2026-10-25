"""Diagnostics without tokens."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import TvStreamerConfigEntry
from .const import CONF_LG_TOKEN, CONF_VM_TOKEN, CONF_WEBHOOK_ID

TO_REDACT = {CONF_LG_TOKEN, CONF_VM_TOKEN, CONF_WEBHOOK_ID}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: TvStreamerConfigEntry) -> dict[str, Any]:
    data = entry.runtime_data
    return async_redact_data(
        {
            "data": dict(entry.data),
            "options": dict(entry.options),
            "compose_version": data.compose_version,
            "status": {sid: c.data for sid, c in data.coordinators.items()},
            "lg": {
                sid: {"ok": c.lg.ok, "message": c.lg.message, "expires": str(c.lg.expires)}
                for sid, c in data.coordinators.items()
                if c.lg_token
            },
        },
        TO_REDACT,
    )

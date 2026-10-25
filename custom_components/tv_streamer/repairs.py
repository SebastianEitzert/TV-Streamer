"""Repair flow: enter a new LG developer mode session token after a failed renewal."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .config_flow import PASSWORD
from .const import CONF_ID, CONF_LG_TOKEN, CONF_NAME, CONF_STREAMERS
from .lg import LgError, async_renew, token_from_input


class LgTokenRepairFlow(RepairsFlow):
    """Ask for a new token, renew once with it and store it."""

    def __init__(self, entry_id: str, streamer_id: str) -> None:
        self._entry_id = entry_id
        self._streamer_id = streamer_id

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="entry_removed")
        streamers = [dict(s) for s in entry.options.get(CONF_STREAMERS, [])]
        streamer = next((s for s in streamers if s[CONF_ID] == self._streamer_id), None)
        if streamer is None:
            return self.async_abort(reason="entry_removed")
        errors: dict[str, str] = {}
        if user_input is not None:
            token = token_from_input(user_input[CONF_LG_TOKEN])
            try:
                ok = bool(token) and (await async_renew(async_get_clientsession(self.hass), token)).ok
            except LgError:
                errors["base"] = "lg_unreachable"
            else:
                if ok:
                    streamer[CONF_LG_TOKEN] = token
                    streamers = [streamer if s[CONF_ID] == self._streamer_id else s for s in streamers]
                    self.hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_STREAMERS: streamers})
                    return self.async_create_entry(data={})
                errors[CONF_LG_TOKEN] = "lg_token_invalid"
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_LG_TOKEN): PASSWORD}),
            description_placeholders={"name": streamer[CONF_NAME]},
            errors=errors,
        )


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, str | int | float | None] | None
) -> RepairsFlow:
    assert data is not None
    return LgTokenRepairFlow(str(data["entry_id"]), str(data["streamer_id"]))


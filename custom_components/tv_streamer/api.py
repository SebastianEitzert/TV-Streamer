"""Endpoints the streamer VM uses to fetch its configuration.

The VM has no Home Assistant user. It authenticates with the per-entry VM token
(Authorization: Bearer …), which is created in the config flow and shown only in
the "VM setup" step of the options.
"""

from __future__ import annotations

import hmac
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import (
    API_COMPOSE,
    API_FILE,
    API_FILES,
    API_UPDATE_SCRIPT,
    API_VERSION,
    CONF_HA_URL,
    CONF_VM_TOKEN,
    DOMAIN,
)

UPDATE_SCRIPT = Path(__file__).parent / "vm_update.sh"


def _entry(hass: HomeAssistant, request: web.Request, entry_id: str):
    """Return the config entry if the request carries its VM token, else raise."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN or getattr(entry, "runtime_data", None) is None:
        raise web.HTTPNotFound
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not token or not hmac.compare_digest(token, entry.data[CONF_VM_TOKEN]):
        raise web.HTTPUnauthorized
    return entry


class _VmView(HomeAssistantView):
    requires_auth = False  # checked with the VM token instead

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass


class VersionView(_VmView):
    """Short hash of the current compose file."""

    url = API_VERSION
    name = "api:tv_streamer:version"

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        entry = _entry(self.hass, request, entry_id)
        return web.Response(text=entry.runtime_data.compose_version + "\n", headers={"Cache-Control": "no-store"})


class ComposeView(_VmView):
    """The generated docker-compose.yml."""

    url = API_COMPOSE
    name = "api:tv_streamer:compose"

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        entry = _entry(self.hass, request, entry_id)
        return web.Response(
            text=entry.runtime_data.compose_text, content_type="text/yaml", headers={"Cache-Control": "no-store"}
        )


class UpdateScriptView(_VmView):
    """The VM update script with this entry's address and token filled in."""

    url = API_UPDATE_SCRIPT
    name = "api:tv_streamer:update_script"

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        entry = _entry(self.hass, request, entry_id)
        script = await self.hass.async_add_executor_job(UPDATE_SCRIPT.read_text)
        script = (
            script.replace("__HA_URL__", entry.data[CONF_HA_URL].rstrip("/"))
            .replace("__ENTRY_ID__", entry.entry_id)
            .replace("__VM_TOKEN__", entry.data[CONF_VM_TOKEN])
        )
        return web.Response(text=script, content_type="text/x-shellscript", headers={"Cache-Control": "no-store"})


class FilesView(_VmView):
    """Manifest of the streamer image files (`sha256  name` per line)."""

    url = API_FILES
    name = "api:tv_streamer:files"

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        entry = _entry(self.hass, request, entry_id)
        return web.Response(text=entry.runtime_data.files_manifest, headers={"Cache-Control": "no-store"})


class FileView(_VmView):
    """One file of the streamer image."""

    url = API_FILE
    name = "api:tv_streamer:file"

    async def get(self, request: web.Request, entry_id: str, name: str) -> web.Response:
        entry = _entry(self.hass, request, entry_id)
        data = entry.runtime_data.files.get(name)
        if data is None:
            raise web.HTTPNotFound
        return web.Response(body=data, content_type="application/octet-stream", headers={"Cache-Control": "no-store"})


def async_register_views(hass: HomeAssistant) -> None:
    """Register the views once per Home Assistant run."""
    if hass.data.get(f"{DOMAIN}_views"):
        return
    hass.data[f"{DOMAIN}_views"] = True
    for view in (VersionView(hass), ComposeView(hass), UpdateScriptView(hass), FilesView(hass), FileView(hass)):
        hass.http.register_view(view)

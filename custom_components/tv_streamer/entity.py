"""Base entity: one device per streamer."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ID, CONF_NAME, CONF_TV_TYPE, DOMAIN
from .coordinator import StreamerCoordinator


def device_identifier(entry_id: str, streamer_id: str) -> tuple[str, str]:
    return (DOMAIN, f"{entry_id}_{streamer_id}")


class TvStreamerEntity(CoordinatorEntity[StreamerCoordinator]):
    """Entity of one streamer."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: StreamerCoordinator, key: str) -> None:
        super().__init__(coordinator)
        streamer = coordinator.streamer
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{streamer[CONF_ID]}_{key}"
        self._attr_translation_key = key
        version = (coordinator.data or {}).get("fassung")
        self._attr_device_info = DeviceInfo(
            identifiers={device_identifier(entry_id, streamer[CONF_ID])},
            name=f"TV Streamer {streamer[CONF_NAME]}",
            manufacturer="TV Streamer",
            model=streamer.get(CONF_TV_TYPE),
            sw_version=str(version) if version else None,
            configuration_url=coordinator.base_url + "/",
        )

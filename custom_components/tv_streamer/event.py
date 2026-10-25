"""Event entity per streamer: remote keys sent by the patched Moonlight app (blue, green, play/pause, stop)."""

from __future__ import annotations

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TvStreamerConfigEntry
from .const import CONF_ID, REMOTE_KEYS, SIGNAL_KEY
from .coordinator import StreamerCoordinator
from .entity import TvStreamerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: TvStreamerConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(RemoteKeyEvent(c) for c in entry.runtime_data.coordinators.values())


class RemoteKeyEvent(TvStreamerEntity, EventEntity):
    """Last remote key pressed in the patched Moonlight app."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = REMOTE_KEYS

    def __init__(self, coordinator: StreamerCoordinator) -> None:
        super().__init__(coordinator, "remote")

    @property
    def available(self) -> bool:
        return True  # keys come by webhook; an unreachable status poll does not matter

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        signal = SIGNAL_KEY.format(self.coordinator.config_entry.entry_id, self.coordinator.streamer[CONF_ID])
        self.async_on_remove(async_dispatcher_connect(self.hass, signal, self._key))

    @callback
    def _key(self, key: str) -> None:
        if key in REMOTE_KEYS:
            self._trigger_event(key)
            self.async_write_ha_state()

"""Binary sensors: reachable and Moonlight stream running."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TvStreamerConfigEntry
from .const import CONF_VIDEO_PATH, VIDEO_MOONLIGHT
from .coordinator import StreamerCoordinator
from .entity import TvStreamerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: TvStreamerConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    entities: list[BinarySensorEntity] = []
    for coordinator in entry.runtime_data.coordinators.values():
        entities.append(ReachableSensor(coordinator))
        if coordinator.streamer.get(CONF_VIDEO_PATH) == VIDEO_MOONLIGHT:
            entities.append(MoonlightSensor(coordinator))
    async_add_entities(entities)


class ReachableSensor(TvStreamerEntity, BinarySensorEntity):
    """Streamer answers on its web port."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: StreamerCoordinator) -> None:
        super().__init__(coordinator, "reachable")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success


class MoonlightSensor(TvStreamerEntity, BinarySensorEntity):
    """A Moonlight client is streaming."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: StreamerCoordinator) -> None:
        super().__init__(coordinator, "moonlight_stream")

    @property
    def is_on(self) -> bool:
        moonlight = (self.coordinator.data or {}).get("moonlight")
        return bool(isinstance(moonlight, dict) and moonlight.get("stream"))

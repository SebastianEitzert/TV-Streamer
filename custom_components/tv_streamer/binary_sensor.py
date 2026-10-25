"""Binary sensors: reachable, Moonlight stream running, streamer shown on its TV."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import TvStreamerConfigEntry
from .const import CONF_MEDIA_PLAYER, CONF_VIDEO_PATH, VIDEO_MOONLIGHT
from .coordinator import StreamerCoordinator
from .entity import TvStreamerEntity
from .show import shown_on_tv


async def async_setup_entry(
    hass: HomeAssistant, entry: TvStreamerConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    entities: list[BinarySensorEntity] = []
    for coordinator in entry.runtime_data.coordinators.values():
        entities.append(ReachableSensor(coordinator))
        if coordinator.streamer.get(CONF_VIDEO_PATH) == VIDEO_MOONLIGHT:
            entities.append(MoonlightSensor(coordinator))
        if coordinator.streamer.get(CONF_MEDIA_PLAYER):
            entities.append(OnTvSensor(coordinator))
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


class OnTvSensor(TvStreamerEntity, BinarySensorEntity):
    """The streamer's own TV shows the streamer right now – not some other browser or Moonlight device."""

    def __init__(self, coordinator: StreamerCoordinator) -> None:
        super().__init__(coordinator, "on_tv")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return shown_on_tv(self.hass, self.coordinator)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # follow the TV's app switches right away, not only the streamer's status reports
        self.async_on_remove(
            async_track_state_change_event(self.hass, [self.coordinator.streamer[CONF_MEDIA_PLAYER]], self._tv_changed)
        )

    @callback
    def _tv_changed(self, event: Event[EventStateChangedData]) -> None:
        self.async_write_ha_state()

"""Sensors: state, measurements and LG developer mode."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfDataRate, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TvStreamerConfigEntry
from .const import CONF_ID, CONF_MEDIA_PLAYER, CONF_VIDEO_PATH, DOMAIN, VIDEO_MOONLIGHT
from .coordinator import StreamerCoordinator
from .entity import TvStreamerEntity

# Measured by the receiving page in the TV browser – MSE and WebRTC only. With Moonlight, Sunshine encodes and reports nothing.
BROWSER_ONLY = {"latency", "frame_rate", "data_rate"}

STATE_SHOWING = "showing"
STATE_RESTING = "resting"
STATE_READY = "ready"


def _viewers(data: dict[str, Any]) -> list[dict[str, Any]]:
    viewers = list(data.get("zuschauer") or [])
    moonlight = data.get("moonlight")
    if isinstance(moonlight, dict) and moonlight.get("stream") and not any(v.get("ip") == "moonlight" for v in viewers):
        viewers.append({"ip": "moonlight"})
    return viewers


def _first(data: dict[str, Any], key: str) -> Any:
    viewers = data.get("zuschauer") or [{}]
    value = viewers[0].get(key)
    return value if isinstance(value, (int, float)) else None


def _state(data: dict[str, Any]) -> str:
    if _viewers(data):
        return STATE_SHOWING
    return STATE_RESTING if data.get("ruht") else STATE_READY


@dataclass(frozen=True, kw_only=True)
class StatusSensorDescription(SensorEntityDescription):
    value: Callable[[dict[str, Any]], Any]


STATUS_SENSORS = (
    StatusSensorDescription(
        key="state",
        device_class=SensorDeviceClass.ENUM,
        options=[STATE_SHOWING, STATE_RESTING, STATE_READY],
        value=_state,
    ),
    StatusSensorDescription(
        key="viewers", state_class=SensorStateClass.MEASUREMENT, value=lambda d: len(_viewers(d))
    ),
    StatusSensorDescription(
        key="latency",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: _first(d, "verzoegerung_ms"),
    ),
    StatusSensorDescription(
        key="frame_rate",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: _first(d, "bilder_s") or d.get("bilder_s"),
    ),
    StatusSensorDescription(
        key="data_rate",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value=lambda d: _first(d, "mbit_s") if _first(d, "mbit_s") is not None else (d.get("kbit_s") or 0) / 1000,
    ),
    StatusSensorDescription(
        key="tab", entity_category=EntityCategory.DIAGNOSTIC, value=lambda d: d.get("reiter")
    ),
    StatusSensorDescription(
        key="version", entity_category=EntityCategory.DIAGNOSTIC, value=lambda d: d.get("fassung")
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: TvStreamerConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    entities: list[SensorEntity] = []
    registry = er.async_get(hass)
    for coordinator in entry.runtime_data.coordinators.values():
        moonlight = coordinator.streamer.get(CONF_VIDEO_PATH) == VIDEO_MOONLIGHT
        for d in STATUS_SENSORS:
            if moonlight and d.key in BROWSER_ONLY:
                # remove a sensor left over from MSE/WebRTC instead of keeping it empty forever
                unique_id = f"{entry.entry_id}_{coordinator.streamer[CONF_ID]}_{d.key}"
                if entity_id := registry.async_get_entity_id("sensor", DOMAIN, unique_id):
                    registry.async_remove(entity_id)
                continue
            entities.append(StatusSensor(coordinator, d))
        if coordinator.lg_token:
            entities += [LgExpiresSensor(coordinator), LgLastRenewalSensor(coordinator)]
    async_add_entities(entities)


class StatusSensor(TvStreamerEntity, SensorEntity):
    """Value from /api/status or the webhook report."""

    entity_description: StatusSensorDescription

    def __init__(self, coordinator: StreamerCoordinator, description: StatusSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "state":
            return None
        data = self.coordinator.data or {}
        return {
            "viewers": [v.get("ip") for v in _viewers(data)],
            "video_path": self.coordinator.streamer.get(CONF_VIDEO_PATH),
            "format": data.get("format"),
            "tv": self.coordinator.streamer.get(CONF_MEDIA_PLAYER),
        }


class LgExpiresSensor(TvStreamerEntity, SensorEntity):
    """When the LG developer mode session ends without renewal."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: StreamerCoordinator) -> None:
        super().__init__(coordinator, "lg_devmode_expires")

    @property
    def available(self) -> bool:
        return True  # comes from developer.lge.com, not from the streamer

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.lg.expires


class LgLastRenewalSensor(TvStreamerEntity, RestoreSensor):
    """Last successful renewal; restored after a restart."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: StreamerCoordinator) -> None:
        super().__init__(coordinator, "lg_devmode_last_renewal")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.coordinator.lg.last_renewal is None and (last := await self.async_get_last_sensor_data()):
            if isinstance(last.native_value, datetime):
                self.coordinator.lg.last_renewal = last.native_value

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.lg.last_renewal

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        lg = self.coordinator.lg
        return {"last_attempt": lg.last_attempt, "last_result": lg.message or None, "ok": lg.ok}

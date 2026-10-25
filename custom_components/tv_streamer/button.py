"""Buttons: start view, reload, back, extra tabs and LG renewal."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import slugify

from . import TvStreamerConfigEntry
from .const import CMD_BACK, CMD_RELOAD, CMD_START_VIEW, CONF_LINKS, CONF_NAME, DOMAIN
from .coordinator import StreamerCoordinator
from .entity import TvStreamerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: TvStreamerConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    entities: list[ButtonEntity] = []
    for coordinator in entry.runtime_data.coordinators.values():
        entities += [
            CommandButton(coordinator, "start_view", CMD_START_VIEW),
            CommandButton(coordinator, "reload", CMD_RELOAD),
            CommandButton(coordinator, "back", CMD_BACK),
        ]
        for link in entry.options.get(CONF_LINKS, []):
            entities.append(LinkButton(coordinator, link[CONF_NAME]))
        if coordinator.lg_token:
            entities.append(LgRenewButton(coordinator))
    async_add_entities(entities)


class CommandButton(TvStreamerEntity, ButtonEntity):
    """Sends one command to the streamer."""

    def __init__(self, coordinator: StreamerCoordinator, key: str, command: str) -> None:
        super().__init__(coordinator, key)
        self._command = command

    async def async_press(self) -> None:
        try:
            await self.coordinator.async_command(self._command)
        except UpdateFailed as err:
            raise HomeAssistantError(str(err)) from err


class LinkButton(CommandButton):
    """Brings an extra tab (e.g. Loxone) to the front."""

    def __init__(self, coordinator: StreamerCoordinator, link: str) -> None:
        super().__init__(coordinator, f"link_{slugify(link)}", f"link:{link}")
        self._attr_translation_key = "link"
        self._attr_translation_placeholders = {"link": link}


class LgRenewButton(TvStreamerEntity, ButtonEntity):
    """Renew the LG developer mode now."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StreamerCoordinator) -> None:
        super().__init__(coordinator, "lg_devmode_renew")

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        if not await self.coordinator.async_lg_renew():
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="lg_renew_failed",
                translation_placeholders={"name": self.coordinator.streamer[CONF_NAME]},
            )

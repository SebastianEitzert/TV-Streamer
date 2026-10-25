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
from .const import CMD_BACK, CMD_RELOAD, CMD_START_VIEW, CONF_LINKS, CONF_MEDIA_PLAYER, CONF_NAME, DOMAIN
from .coordinator import StreamerCoordinator
from .entity import TvStreamerEntity
from .show import async_show_on_tv, check_can_show


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
        if coordinator.streamer.get(CONF_MEDIA_PLAYER):
            entities.append(ShowOnTvButton(coordinator, None))
            entities += [ShowOnTvButton(coordinator, link[CONF_NAME]) for link in entry.options.get(CONF_LINKS, [])]
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
        self._attr_translation_placeholders = {"link": link.replace("_", " ").title()}


class ShowOnTvButton(TvStreamerEntity, ButtonEntity):
    """Switch the TV on if needed and show the start view or an extra tab there."""

    def __init__(self, coordinator: StreamerCoordinator, link: str | None) -> None:
        super().__init__(coordinator, f"show_link_on_tv_{slugify(link)}" if link else "show_on_tv")
        self._link = link
        if link:
            self._attr_translation_key = "show_link_on_tv"
            self._attr_translation_placeholders = {"link": link.replace("_", " ").title()}

    async def async_press(self) -> None:
        check_can_show(self.hass, self.coordinator)
        # Waking the TV can take a minute and a half – do not block the button press.
        self.coordinator.config_entry.async_create_background_task(
            self.hass, async_show_on_tv(self.hass, self.coordinator, self._link), f"{DOMAIN} show on tv"
        )


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

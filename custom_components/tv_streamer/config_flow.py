"""Config flow (VM address) and options flow (streamers, tabs, settings, VM setup)."""

from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.util import slugify
from yarl import URL

from .const import (
    API_UPDATE_SCRIPT,
    CONF_AREA,
    CONF_AUDIO,
    CONF_BITRATE,
    CONF_FREEZE_AFTER,
    CONF_GREEN_TAB,
    CONF_HA_URL,
    CONF_HEIGHT,
    CONF_HOME_AFTER,
    CONF_HOST,
    CONF_ID,
    CONF_IMAGE,
    CONF_INDEX,
    CONF_LG_RENEW_TIME,
    CONF_LG_TOKEN,
    CONF_LINKS,
    CONF_MEDIA_PLAYER,
    CONF_NAME,
    CONF_NO_RELOAD,
    CONF_RASTER_THREADS,
    CONF_REMEMBER_LOGIN,
    CONF_START_URL,
    CONF_STREAMERS,
    CONF_TIMEZONE,
    CONF_TV_TYPE,
    CONF_URL,
    CONF_VIDEO_PATH,
    CONF_VM_TOKEN,
    CONF_WAKE,
    CONF_WEBHOOK_ID,
    CONF_WIDTH,
    CONF_ZOOM,
    DEFAULT_FREEZE_AFTER,
    DEFAULT_HOME_AFTER,
    DEFAULT_IMAGE,
    DEFAULT_LG_RENEW_TIME,
    DEFAULT_RASTER_THREADS,
    DOMAIN,
    GREEN_FIRST,
    GREEN_NONE,
    LG_TV_TYPES,
    MAX_STREAMERS,
    TV_OTHER,
    TV_PRESETS,
    TV_TYPES,
    VIDEO_PATHS,
    WAKE_DOMAINS,
)
from .lg import LgError, async_check, token_from_input

TEXT = selector.TextSelector()
PASSWORD = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))


def _number(minimum: float, maximum: float, step: float = 1, unit: str | None = None) -> selector.NumberSelector:
    config = selector.NumberSelectorConfig(min=minimum, max=maximum, step=step, mode=selector.NumberSelectorMode.BOX)
    if unit:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


def _select(options: list[str], key: str) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=options, translation_key=key, mode=selector.SelectSelectorMode.DROPDOWN)
    )


def _default_ha_url(hass: HomeAssistant) -> str:
    try:
        return get_url(hass, allow_external=False, allow_ip=True)
    except NoURLAvailableError:
        return "http://homeassistant.local:8123"


def normalize_url(value: str, base: str | None = None) -> str | None:
    """Accept `192.168.1.160`, `loxone.local/app`, `/tv-dashboard/home` (with base) or a full URL; None if unusable."""
    value = (value or "").strip()
    if not value:
        return None
    if value.startswith("/") and base:
        return base.rstrip("/") + value
    if "://" not in value:
        value = "http://" + value
    try:
        url = URL(value)
    except ValueError:
        return None
    if url.scheme not in ("http", "https") or not url.host:
        return None
    text = str(url)
    return text if url.raw_path not in ("", "/") or text.endswith("/") else text + "/"


def _is_webostv(hass: HomeAssistant, entity_id: str) -> bool:
    entry = er.async_get(hass).async_get(entity_id)
    return entry is not None and entry.platform == "webostv"


def default_options(hass: HomeAssistant, ha_url: str) -> dict[str, Any]:
    return {
        CONF_STREAMERS: [],
        CONF_LINKS: [],
        CONF_START_URL: ha_url.rstrip("/") + "/lovelace/0",
        CONF_FREEZE_AFTER: DEFAULT_FREEZE_AFTER,
        CONF_HOME_AFTER: DEFAULT_HOME_AFTER,
        CONF_RASTER_THREADS: DEFAULT_RASTER_THREADS,
        CONF_AUDIO: True,
        CONF_LG_RENEW_TIME: DEFAULT_LG_RENEW_TIME,
        CONF_IMAGE: DEFAULT_IMAGE,
        CONF_TIMEZONE: hass.config.time_zone,
    }


def _vm_schema(host: str = "", ha_url: str = "") -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=host): TEXT,
            vol.Required(CONF_HA_URL, default=ha_url): TEXT,
        }
    )


def _streamer_schema(values: dict[str, Any]) -> vol.Schema:
    """Form for one streamer, pre-filled with values (existing streamer or preset of the TV type)."""

    def sv(key: str) -> dict[str, Any]:
        return {"suggested_value": values.get(key)} if values.get(key) not in (None, "") else {}

    return vol.Schema(
        {
            vol.Required(CONF_NAME, description=sv(CONF_NAME)): TEXT,
            vol.Optional(CONF_AREA, description=sv(CONF_AREA)): selector.AreaSelector(),
            vol.Optional(CONF_MEDIA_PLAYER, description=sv(CONF_MEDIA_PLAYER)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="media_player")
            ),
            vol.Optional(CONF_WAKE, description=sv(CONF_WAKE)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=WAKE_DOMAINS)
            ),
            vol.Required(CONF_TV_TYPE, default=values.get(CONF_TV_TYPE, TV_OTHER)): _select(TV_TYPES, CONF_TV_TYPE),
            vol.Required(CONF_VIDEO_PATH, default=values[CONF_VIDEO_PATH]): _select(VIDEO_PATHS, CONF_VIDEO_PATH),
            vol.Required(CONF_WIDTH, default=values[CONF_WIDTH]): _number(640, 3840, 1, "px"),
            vol.Required(CONF_HEIGHT, default=values[CONF_HEIGHT]): _number(360, 2160, 1, "px"),
            vol.Required(CONF_ZOOM, default=values[CONF_ZOOM]): _number(0.5, 4, 0.01),
            vol.Required(CONF_BITRATE, default=values[CONF_BITRATE]): _number(1, 50, 1, "Mbit/s"),
            vol.Optional(CONF_LG_TOKEN, description=sv(CONF_LG_TOKEN)): PASSWORD,
        }
    )


async def validate_lg_token(hass: HomeAssistant, value: str) -> tuple[str, str | None]:
    """Return (token, error key). An unreachable LG server is not an error – only a clear rejection is."""
    token = token_from_input(value)
    if not token:
        return "", ("lg_token_invalid" if value else None)
    try:
        result = await async_check(async_get_clientsession(hass), token)
    except LgError:
        return token, None
    return token, (None if result.ok else "lg_token_invalid")


class TvStreamerConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry per streamer VM."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TvStreamerOptionsFlow:
        return TvStreamerOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            ha_url = (normalize_url(user_input[CONF_HA_URL]) or "").rstrip("/")
            if not ha_url:
                errors[CONF_HA_URL] = "invalid_url"
                return self.async_show_form(step_id="user", data_schema=_vm_schema(host, user_input[CONF_HA_URL]), errors=errors)
            await self.async_set_unique_id(host.lower())
            self._abort_if_unique_id_configured()
            self._data = {
                CONF_HOST: host,
                CONF_HA_URL: ha_url,
                CONF_VM_TOKEN: secrets.token_urlsafe(32),
                CONF_WEBHOOK_ID: webhook.async_generate_id(),
            }
            return self.async_create_entry(
                title=f"TV Streamer {host}",
                data=self._data,
                options=default_options(self.hass, self._data[CONF_HA_URL]),
            )
        return self.async_show_form(step_id="user", data_schema=_vm_schema(ha_url=_default_ha_url(self.hass)))

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            return self.async_update_reload_and_abort(
                entry,
                data_updates={
                    CONF_HOST: user_input[CONF_HOST].strip(),
                    CONF_HA_URL: (normalize_url(user_input[CONF_HA_URL]) or entry.data[CONF_HA_URL]).rstrip("/"),
                },
            )
        return self.async_show_form(
            step_id="reconfigure", data_schema=_vm_schema(entry.data[CONF_HOST], entry.data[CONF_HA_URL])
        )


class TvStreamerOptionsFlow(OptionsFlow):
    """Streamers, extra tabs, general settings and the VM setup command."""

    def __init__(self) -> None:
        self._options: dict[str, Any] = {}
        self._edit_id: str | None = None
        self._preset: dict[str, Any] = {}
        self._edit_link: str | None = None

    @property
    def _streamers(self) -> list[dict[str, Any]]:
        return self._options[CONF_STREAMERS]

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not self._options:
            self._options = {
                **default_options(self.hass, self.config_entry.data[CONF_HA_URL]),
                **self.config_entry.options,
            }
            self._options[CONF_STREAMERS] = [dict(s) for s in self._options[CONF_STREAMERS]]
            self._options[CONF_LINKS] = [dict(link) for link in self._options[CONF_LINKS]]
        menu = ["add_streamer"]
        if self._streamers:
            menu += ["edit_streamer", "remove_streamer"]
        menu += ["add_link"]
        if self._options[CONF_LINKS]:
            menu += ["edit_link", "remove_link"]
        menu += ["settings", "vm_setup"]
        return self.async_show_menu(
            step_id="init",
            menu_options=menu,
            description_placeholders={
                "streamers": ", ".join(s[CONF_NAME] for s in self._streamers) or "–",
                "links": ", ".join(link[CONF_NAME] for link in self._options[CONF_LINKS]) or "–",
            },
        )

    def _save(self) -> ConfigFlowResult:
        """Every finished change is stored at once (the integration reloads, the VM follows within 5 minutes)."""
        return self.async_create_entry(data=self._options)

    # Streamers ----------------------------------------------------------------------

    async def async_step_add_streamer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 1: name and TV type – the type fills in the confirmed settings."""
        errors: dict[str, str] = {}
        if len(self._streamers) >= MAX_STREAMERS:
            return self.async_abort(reason="too_many_streamers")
        if user_input is not None:
            if self._id_taken(slugify(user_input[CONF_NAME])):
                errors[CONF_NAME] = "name_taken"
            else:
                self._edit_id = None
                self._preset = {**TV_PRESETS[user_input[CONF_TV_TYPE]], **user_input}
                return await self.async_step_streamer()
        return self.async_show_form(
            step_id="add_streamer",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): TEXT,
                    vol.Required(CONF_TV_TYPE, default=TV_OTHER): _select(TV_TYPES, CONF_TV_TYPE),
                }
            ),
            errors=errors,
        )

    async def async_step_edit_streamer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._edit_id = user_input[CONF_ID]
            self._preset = dict(self._find(self._edit_id))
            return await self.async_step_streamer()
        return self.async_show_form(step_id="edit_streamer", data_schema=self._choose_streamer_schema())

    async def async_step_streamer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 2: all settings of one streamer."""
        errors: dict[str, str] = {}
        if user_input is not None:
            values = {**self._preset, **user_input}
            for key in (CONF_AREA, CONF_MEDIA_PLAYER, CONF_WAKE, CONF_LG_TOKEN):
                if key not in user_input:
                    values.pop(key, None)
            new_id = self._edit_id or slugify(values[CONF_NAME])
            if not new_id or (self._edit_id is None and self._id_taken(new_id)):
                errors[CONF_NAME] = "name_taken"
            tv = values.get(CONF_MEDIA_PLAYER)
            if tv and values[CONF_TV_TYPE] in LG_TV_TYPES and not _is_webostv(self.hass, tv):
                # e.g. the Music Assistant speaker of the TV – it has a similar name but cannot start apps
                errors[CONF_MEDIA_PLAYER] = "not_webostv"
            token = values.get(CONF_LG_TOKEN, "")
            if token and values[CONF_TV_TYPE] not in LG_TV_TYPES:
                errors[CONF_LG_TOKEN] = "lg_token_not_lg"
            elif token and token != self._preset.get(CONF_LG_TOKEN):
                values[CONF_LG_TOKEN], error = await validate_lg_token(self.hass, token)
                if error:
                    errors[CONF_LG_TOKEN] = error
            if not errors:
                values[CONF_WIDTH], values[CONF_HEIGHT] = int(values[CONF_WIDTH]), int(values[CONF_HEIGHT])
                values[CONF_BITRATE] = int(values[CONF_BITRATE])
                values[CONF_ZOOM] = round(float(values[CONF_ZOOM]), 2)
                if not values.get(CONF_LG_TOKEN):
                    values.pop(CONF_LG_TOKEN, None)
                if self._edit_id is None:
                    values[CONF_ID] = new_id
                    values[CONF_INDEX] = self._free_index()
                    self._streamers.append(values)
                else:
                    self._streamers[self._streamers.index(self._find(self._edit_id))] = values
                return self._save()
        return self.async_show_form(
            step_id="streamer",
            data_schema=_streamer_schema(self._preset if user_input is None else {**self._preset, **user_input}),
            errors=errors,
        )

    async def async_step_remove_streamer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._streamers.remove(self._find(user_input[CONF_ID]))
            return self._save()
        return self.async_show_form(step_id="remove_streamer", data_schema=self._choose_streamer_schema())

    def _choose_streamer_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[selector.SelectOptionDict(value=s[CONF_ID], label=s[CONF_NAME]) for s in self._streamers]
                    )
                )
            }
        )

    def _find(self, streamer_id: str) -> dict[str, Any]:
        return next(s for s in self._streamers if s[CONF_ID] == streamer_id)

    def _id_taken(self, streamer_id: str) -> bool:
        return any(s[CONF_ID] == streamer_id for s in self._streamers)

    def _free_index(self) -> int:
        used = {s[CONF_INDEX] for s in self._streamers}
        return next(i for i in range(MAX_STREAMERS) if i not in used)

    # Extra tabs -----------------------------------------------------------------------

    async def async_step_add_link(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            name = slugify(user_input[CONF_NAME])
            url = normalize_url(user_input[CONF_URL])
            if not name or any(link[CONF_NAME] == name for link in self._options[CONF_LINKS]):
                errors[CONF_NAME] = "name_taken"
            elif url is None:
                errors[CONF_URL] = "invalid_url"
            else:
                self._options[CONF_LINKS].append({CONF_NAME: name})
                return self._store_link(name, url, user_input)
        return self.async_show_form(
            step_id="add_link",
            data_schema=vol.Schema({vol.Required(CONF_NAME): TEXT, **self._link_fields({})}),
            errors=errors,
        )

    async def async_step_edit_link(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._edit_link = user_input[CONF_NAME]
            return await self.async_step_link()
        return self.async_show_form(step_id="edit_link", data_schema=self._choose_link_schema())

    async def async_step_link(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Address and options of one tab; the name stays, buttons, entity ids and the Moonlight app hang on it."""
        errors: dict[str, str] = {}
        link = self._find_link(self._edit_link)
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            if url is None:
                errors[CONF_URL] = "invalid_url"
            else:
                return self._store_link(link[CONF_NAME], url, user_input)
        return self.async_show_form(
            step_id="link",
            data_schema=vol.Schema(self._link_fields(link if user_input is None else {**link, **user_input})),
            description_placeholders={"name": link[CONF_NAME]},
            errors=errors,
        )

    @staticmethod
    def _link_fields(values: dict[str, Any]) -> dict:
        return {
            vol.Required(CONF_URL, default=values.get(CONF_URL, vol.UNDEFINED)): TEXT,
            vol.Required(CONF_REMEMBER_LOGIN, default=values.get(CONF_REMEMBER_LOGIN, False)): selector.BooleanSelector(),
            vol.Required(CONF_NO_RELOAD, default=values.get(CONF_NO_RELOAD, False)): selector.BooleanSelector(),
        }

    def _store_link(self, name: str, url: str, user_input: dict[str, Any]) -> ConfigFlowResult:
        if user_input[CONF_REMEMBER_LOGIN]:  # server.py fills in the login of one tab only
            for link in self._options[CONF_LINKS]:
                link[CONF_REMEMBER_LOGIN] = False
        self._find_link(name).update(
            {
                CONF_URL: url,
                CONF_REMEMBER_LOGIN: user_input[CONF_REMEMBER_LOGIN],
                CONF_NO_RELOAD: user_input[CONF_NO_RELOAD],
            }
        )
        return self._save()

    def _find_link(self, name: str | None) -> dict[str, Any]:
        return next(link for link in self._options[CONF_LINKS] if link[CONF_NAME] == name)

    def _choose_link_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_NAME): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=[link[CONF_NAME] for link in self._options[CONF_LINKS]])
                )
            }
        )

    async def async_step_remove_link(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._options[CONF_LINKS] = [
                link for link in self._options[CONF_LINKS] if link[CONF_NAME] != user_input[CONF_NAME]
            ]
            return self._save()
        return self.async_show_form(step_id="remove_link", data_schema=self._choose_link_schema())

    # General settings --------------------------------------------------------------------

    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            for key in (CONF_FREEZE_AFTER, CONF_HOME_AFTER, CONF_RASTER_THREADS):
                user_input[key] = int(user_input[key])
            start_url = normalize_url(user_input[CONF_START_URL], self.config_entry.data[CONF_HA_URL])
            if start_url is None:
                errors[CONF_START_URL] = "invalid_url"
            else:
                user_input[CONF_START_URL] = start_url
                self._options.update(user_input)
                return self._save()
        o = self._options
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_START_URL, default=o[CONF_START_URL]): TEXT,
                    vol.Required(CONF_FREEZE_AFTER, default=o[CONF_FREEZE_AFTER]): _number(0, 3600, 1, "s"),
                    vol.Required(CONF_HOME_AFTER, default=o[CONF_HOME_AFTER]): _number(0, 3600, 1, "s"),
                    vol.Required(CONF_RASTER_THREADS, default=o[CONF_RASTER_THREADS]): _number(1, 4),
                    vol.Required(CONF_GREEN_TAB, default=self._green_default()): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=GREEN_FIRST, label=GREEN_FIRST),
                                selector.SelectOptionDict(value=GREEN_NONE, label=GREEN_NONE),
                                *(
                                    selector.SelectOptionDict(value=n, label=n.replace("_", " ").title())
                                    for n in (link[CONF_NAME] for link in o[CONF_LINKS])
                                ),
                            ],
                            translation_key=CONF_GREEN_TAB,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_AUDIO, default=o[CONF_AUDIO]): selector.BooleanSelector(),
                    vol.Required(CONF_LG_RENEW_TIME, default=o[CONF_LG_RENEW_TIME]): selector.TimeSelector(),
                    vol.Required(CONF_IMAGE, default=o[CONF_IMAGE]): TEXT,
                    vol.Required(CONF_TIMEZONE, default=o[CONF_TIMEZONE]): TEXT,
                }
            ),
            errors=errors,
        )

    def _green_default(self) -> str:
        choice = self._options.get(CONF_GREEN_TAB, GREEN_FIRST)
        names = [link[CONF_NAME] for link in self._options[CONF_LINKS]]
        return choice if choice in (GREEN_FIRST, GREEN_NONE, *names) else GREEN_FIRST

    # VM setup ----------------------------------------------------------------------

    async def async_step_vm_setup(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the one-time command for the VM (contains the VM token)."""
        if user_input is not None:
            return await self.async_step_init()
        entry = self.config_entry
        url = entry.data[CONF_HA_URL] + API_UPDATE_SCRIPT.format(entry_id=entry.entry_id)
        command = f'curl -fsSL -H "Authorization: Bearer {entry.data[CONF_VM_TOKEN]}" {url} | sh -s -- install'
        return self.async_show_form(
            step_id="vm_setup", data_schema=vol.Schema({}), description_placeholders={"command": command}
        )

"""Fixtures."""

import pytest
from homeassistant.const import CONF_NAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tv_streamer.config_flow import default_options
from custom_components.tv_streamer.const import (
    CONF_BITRATE,
    CONF_HA_URL,
    CONF_HEIGHT,
    CONF_HOST,
    CONF_ID,
    CONF_INDEX,
    CONF_LG_TOKEN,
    CONF_LINKS,
    CONF_NO_RELOAD,
    CONF_REMEMBER_LOGIN,
    CONF_STREAMERS,
    CONF_TV_TYPE,
    CONF_URL,
    CONF_VIDEO_PATH,
    CONF_VM_TOKEN,
    CONF_WEBHOOK_ID,
    CONF_WIDTH,
    CONF_ZOOM,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


DATA = {
    CONF_HOST: "192.168.1.42",
    CONF_HA_URL: "http://192.168.1.10:8123",
    CONF_VM_TOKEN: "vm-secret",
    CONF_WEBHOOK_ID: "hook123",
}

BEDROOM = {
    CONF_ID: "bedroom",
    CONF_NAME: "Bedroom",
    CONF_INDEX: 0,
    CONF_TV_TYPE: "lg_webos4",
    CONF_VIDEO_PATH: "moonlight",
    CONF_WIDTH: 1920,
    CONF_HEIGHT: 1080,
    CONF_ZOOM: 1.25,
    CONF_BITRATE: 12,
    CONF_LG_TOKEN: "lg-secret",
}
LIVING = {
    CONF_ID: "living_room",
    CONF_NAME: "Living room",
    CONF_INDEX: 1,
    CONF_TV_TYPE: "other",
    CONF_VIDEO_PATH: "webrtc",
    CONF_WIDTH: 2560,
    CONF_HEIGHT: 1440,
    CONF_ZOOM: 1.67,
    CONF_BITRATE: 16,
}
LOXONE = {CONF_NAME: "loxone", CONF_URL: "http://192.168.1.160/", CONF_REMEMBER_LOGIN: True, CONF_NO_RELOAD: True}


@pytest.fixture
def entry(hass):
    options = default_options(hass, DATA[CONF_HA_URL])
    options[CONF_STREAMERS] = [BEDROOM, LIVING]
    options[CONF_LINKS] = [LOXONE]
    e = MockConfigEntry(domain=DOMAIN, data=DATA, options=options, unique_id=DATA[CONF_HOST], title="TV Streamer")
    e.add_to_hass(hass)
    return e

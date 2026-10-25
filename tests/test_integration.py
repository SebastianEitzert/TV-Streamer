"""Tests: compose file, VM endpoints, webhook, LG renewal, config and options flow."""

from http import HTTPStatus

import yaml
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir

from custom_components.tv_streamer.compose import build_compose
from custom_components.tv_streamer.const import (
    CONF_HA_URL,
    CONF_HOST,
    CONF_STREAMERS,
    CONF_VM_TOKEN,
    DOMAIN,
    LG_CHECK_URL,
    LG_RENEW_URL,
)
from custom_components.tv_streamer.lg import token_from_input

from .conftest import DATA

STATUS = {"name": "bedroom", "fassung": "2026-10-25.37o", "zuschauer": [], "ruht": True, "reiter": "ha"}
LG_OK = '{"result":"success","errorCode":"200","errorMsg":"Session Time : 999:12:30"}'
LG_FAIL = '{"result":"fail","errorCode":"401","errorMsg":"Invalid session token"}'


def _mock_streamers(aioclient_mock):
    aioclient_mock.get("http://192.168.1.42:8091/api/status", json=STATUS)
    aioclient_mock.get("http://192.168.1.42:8092/api/status", json={**STATUS, "name": "living_room"})
    aioclient_mock.post("http://192.168.1.42:8091/api/cmd", json={"ok": True})


def test_compose(hass: HomeAssistant, entry) -> None:
    compose = build_compose(entry.data, dict(entry.options), "http://ha/api/webhook/x")
    bedroom, living = compose["services"]["bedroom"], compose["services"]["living_room"]
    assert bedroom["ports"] == ["8091:8090", "47984-47990:47984-47990", "48010:48010", "47998-48000:47998-48000/udp"]
    assert bedroom["environment"]["MOONLIGHT"] == "1"
    assert bedroom["environment"]["BROWSER_BILD"] == "0"
    assert bedroom["environment"]["SUNSHINE_PORT"] == "47989"
    assert living["ports"] == ["8092:8090", "8556:8556/udp", "8556:8556/tcp"]
    assert living["environment"]["WEBRTC_PORT"] == "8556"
    assert living["environment"]["VIDEO_TV"] == "webrtc"
    assert living["environment"]["BITRATE"] == "16M"
    env = bedroom["environment"]
    assert env["LINKS"] == '{"loxone": "http://192.168.1.160/"}'
    assert env["KEIN_NEULADEN"] == "loxone" and env["ZUGANG_REITER"] == "loxone"
    assert env["CHROMIUM_FLAGS"] == "--num-raster-threads=4"
    assert "lg-secret" not in yaml.safe_dump(compose)
    assert compose["volumes"] == {"tv-bedroom": None, "tv-living_room": None}


def test_token_from_input() -> None:
    assert token_from_input(f"{LG_RENEW_URL}?sessionToken=abc123") == "abc123"
    assert token_from_input(" abc123 ") == "abc123"
    assert token_from_input("https://example.com/") == ""


async def test_setup_endpoints_webhook(hass: HomeAssistant, entry, aioclient_mock, hass_client_no_auth) -> None:
    _mock_streamers(aioclient_mock)
    aioclient_mock.get(LG_CHECK_URL, text=LG_OK)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.tv_streamer_bedroom_state").state == "resting"
    assert hass.states.get("binary_sensor.tv_streamer_bedroom_reachable").state == "on"
    assert hass.states.get("sensor.tv_streamer_bedroom_developer_mode_expires").state not in ("unknown", "unavailable")
    assert hass.states.get("button.tv_streamer_bedroom_show_loxone") is not None
    assert hass.states.get("sensor.tv_streamer_living_room_developer_mode_expires") is None

    client = await hass_client_no_auth()
    base = f"/api/tv_streamer/{entry.entry_id}"
    assert (await client.get(f"{base}/version")).status == HTTPStatus.UNAUTHORIZED
    bad = {"Authorization": "Bearer wrong"}
    assert (await client.get(f"{base}/docker-compose.yml", headers=bad)).status == HTTPStatus.UNAUTHORIZED
    auth = {"Authorization": f"Bearer {DATA[CONF_VM_TOKEN]}"}
    version = (await (await client.get(f"{base}/version", headers=auth)).text()).strip()
    assert version == entry.runtime_data.compose_version
    compose = yaml.safe_load(await (await client.get(f"{base}/docker-compose.yml", headers=auth)).text())
    assert compose["services"]["bedroom"]["environment"]["HA_WEBHOOK"] == "http://192.168.1.10:8123/api/webhook/hook123"
    script = await (await client.get(f"{base}/update.sh", headers=auth)).text()
    assert 'HA_TOKEN="vm-secret"' in script and f'ENTRY_ID="{entry.entry_id}"' in script

    resp = await client.post(
        "/api/webhook/hook123",
        json={"name": "bedroom", "zuschauer": [{"ip": "1.2.3.4", "verzoegerung_ms": 42, "bilder_s": 30, "mbit_s": 5.5}]},
    )
    assert resp.status == HTTPStatus.OK
    await hass.async_block_till_done()
    assert hass.states.get("sensor.tv_streamer_bedroom_state").state == "showing"
    assert hass.states.get("sensor.tv_streamer_bedroom_latency").state == "42"
    assert hass.states.get("sensor.tv_streamer_bedroom_data_rate").state == "5.5"

    await hass.services.async_call(
        "button", "press", {"entity_id": "button.tv_streamer_bedroom_start_view"}, blocking=True
    )
    assert aioclient_mock.mock_calls[-1][2] == {"c": "startansicht"}


async def test_lg_renew_failure_creates_issue(hass: HomeAssistant, entry, aioclient_mock) -> None:
    _mock_streamers(aioclient_mock)
    aioclient_mock.get(LG_CHECK_URL, text=LG_OK)
    aioclient_mock.get(LG_RENEW_URL, text=LG_FAIL)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data.coordinators["bedroom"]
    assert await coordinator.async_lg_renew() is False
    issue = ir.async_get(hass).async_get_issue(DOMAIN, coordinator.issue_id)
    assert issue is not None and issue.is_fixable
    assert "lg-secret" not in coordinator.lg.message

    aioclient_mock.clear_requests()
    _mock_streamers(aioclient_mock)
    aioclient_mock.get(LG_CHECK_URL, text=LG_OK)
    aioclient_mock.get(LG_RENEW_URL, text=LG_OK)
    assert await coordinator.async_lg_renew() is True
    assert ir.async_get(hass).async_get_issue(DOMAIN, coordinator.issue_id) is None
    state = hass.states.get("sensor.tv_streamer_bedroom_developer_mode_last_renewal")
    assert state.state not in ("unknown", "unavailable")


async def test_config_and_options_flow(hass: HomeAssistant, aioclient_mock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.5", CONF_HA_URL: "http://10.0.0.2:8123/"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.data[CONF_HA_URL] == "http://10.0.0.2:8123"
    assert len(entry.data[CONF_VM_TOKEN]) > 30
    await hass.async_block_till_done()

    aioclient_mock.get("http://10.0.0.5:8091/api/status", json={**STATUS, "name": "kitchen"})
    aioclient_mock.get(LG_CHECK_URL, text=LG_OK)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert flow["type"] is FlowResultType.MENU
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "add_streamer"})
    flow = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"name": "Kitchen", "tv_type": "lg_webos5"}
    )
    assert flow["step_id"] == "streamer"
    flow = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        {
            "name": "Kitchen",
            "tv_type": "lg_webos5",
            "video_path": "moonlight",
            "width": 2560,
            "height": 1440,
            "zoom": 1.67,
            "bitrate": 16,
            "lg_session_token": f"{LG_RENEW_URL}?sessionToken=tok",
        },
    )
    assert flow["type"] is FlowResultType.MENU
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "vm_setup"})
    assert "Bearer " in flow["description_placeholders"]["command"]
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {})
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "save"})
    assert flow["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    streamer = entry.options[CONF_STREAMERS][0]
    assert streamer["id"] == "kitchen" and streamer["index"] == 0 and streamer["lg_session_token"] == "tok"
    assert hass.states.get("sensor.tv_streamer_kitchen_state") is not None

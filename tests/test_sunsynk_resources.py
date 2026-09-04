"""Resource parsing.

Every model reads the API payload defensively: an upstream field rename or a
null reading must degrade to None, never KeyError in the middle of a poll.
"""
import datetime

import pytest
import pytest_asyncio

from mock_api_server import ACCESS_TOKEN, MockResponse, MockSunsynkApi
from sunsynk.battery import Battery
from sunsynk.client import SunsynkApiError, SunsynkClient
from sunsynk.grid import Grid
from sunsynk.input import Input
from sunsynk.inverter import Inverter
from sunsynk.output import Output
from sunsynk.plant import Plant
from sunsynk.resource import Resource, to_datetime, to_float, to_isoformat

BASE_URL = "https://api.test.invalid"

ALL_MODELS = [Battery, Grid, Input, Inverter, Output, Plant]


@pytest.fixture
def api():
    return MockSunsynkApi()


@pytest_asyncio.fixture
async def client(api):
    client = SunsynkClient("user", "pass", BASE_URL)
    client.session = api
    await client.login()
    return client


# -- coercion helpers ------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("12.5", 12.5),
        (12.5, 12.5),
        (12, 12.0),
        (None, None),
        ("", None),
        ("not-a-number", None),
        ([], None),
    ],
)
def test_to_float(value, expected):
    assert to_float(value) == expected


def test_to_float_uses_the_default_for_unusable_values():
    assert to_float(None, 0.0) == 0.0
    assert to_float("nonsense", 0.0) == 0.0
    assert to_float("3", 0.0) == 3.0


def test_to_datetime():
    assert to_datetime("2026-01-02T03:04:05Z", "%Y-%m-%dT%H:%M:%SZ") == datetime.datetime(
        2026, 1, 2, 3, 4, 5
    )
    assert to_datetime(None, "%Y-%m-%dT%H:%M:%SZ") is None
    assert to_datetime("", "%Y-%m-%dT%H:%M:%SZ") is None
    assert to_datetime("not a date", "%Y-%m-%dT%H:%M:%SZ") is None
    assert to_datetime(42, "%Y-%m-%dT%H:%M:%SZ") is None


def test_to_isoformat():
    assert to_isoformat("2024-05-06T07:08:09") == datetime.datetime(2024, 5, 6, 7, 8, 9)
    assert to_isoformat(None) is None
    assert to_isoformat("nope") is None


def test_resource_repr_lists_attributes():
    battery = Battery({"soc": "64.0"})
    assert "soc=64.0" in repr(battery)
    assert "Battery" in repr(battery)
    assert isinstance(battery, Resource)


# -- empty payloads --------------------------------------------------------


@pytest.mark.parametrize("model", ALL_MODELS)
def test_models_tolerate_an_empty_payload(model):
    """An upstream field rename must not raise; the reading is simply absent."""
    instance = model({})
    assert isinstance(instance, Resource)


def test_grid_without_vip_has_no_readings():
    grid = Grid({"pac": 0})
    assert grid.vip == []
    assert grid.get_voltage() is None
    assert grid.get_current() is None
    assert grid.get_power() is None


def test_grid_handles_a_null_vip_list():
    grid = Grid({"vip": None})
    assert grid.vip == []


def test_input_without_strings_has_no_readings():
    data = Input({})
    assert data.pv_iv == []
    assert data.get_power() == 0.0
    assert data.get_voltage() is None


def test_inverter_without_nested_objects():
    inverter = Inverter({"sn": "SN"})
    assert inverter.version is None
    assert inverter.plant is None
    assert inverter.gateway is None


# -- parsing via the client ------------------------------------------------


@pytest.mark.asyncio
async def test_get_plants(client):
    plants = await client.get_plants()

    assert len(plants) == 1
    plant = plants[0]
    assert plant.id == 42
    assert plant.name == "Home"
    assert plant.generation_today == "5.6"
    assert plant.updated_at == datetime.datetime(2026, 1, 2, 3, 4, 5)
    assert plant.created_at == datetime.datetime(2024, 5, 6, 7, 8, 9)


@pytest.mark.asyncio
async def test_get_inverters(client):
    inverters = await client.get_inverters()

    assert len(inverters) == 1
    inverter = inverters[0]
    assert inverter.sn == "SN-TEST-1"
    assert inverter.version.soft_ver == "4.5.6"
    assert inverter.plant.id == 42
    assert inverter.gateway.gsn == "GSN-1"
    assert inverter.updated_at == datetime.datetime(2026, 1, 2, 3, 4, 5)


@pytest.mark.asyncio
async def test_get_inverter_realtime_battery(client):
    battery = await client.get_inverter_realtime_battery("SN-TEST-1")

    assert battery.soc == "64.0"
    assert battery.get_power() == -450.0
    assert battery.get_voltage() == 52.4
    assert battery.get_current() == -8.6


@pytest.mark.asyncio
async def test_get_inverter_realtime_grid(client):
    grid = await client.get_inverter_realtime_grid("SN-TEST-1")

    assert grid.status == 1
    assert grid.get_voltage() == 230.1
    assert grid.get_current() == 2.5
    assert grid.get_power() == 575.0
    assert grid.fac == "49.98"


@pytest.mark.asyncio
async def test_get_inverter_realtime_input_sums_strings(client):
    data = await client.get_inverter_realtime_input("SN-TEST-1")

    assert len(data.pv_iv) == 2
    assert data.get_power() == 1606.0
    assert data.get_voltage() == 315.0
    assert data.pv_iv[0].time == datetime.datetime(2026, 1, 2, 3, 4, 5)


@pytest.mark.asyncio
async def test_get_inverter_realtime_output(client):
    output = await client.get_inverter_realtime_output("SN-TEST-1")

    assert output.pac == 812
    assert output.p_inv == 812
    assert output.vip[0].voltage == 230.5


@pytest.mark.asyncio
async def test_requests_carry_the_bearer_token(client, api):
    await client.get_plants()

    assert api.last()["headers"]["Authorization"] == f"Bearer {ACCESS_TOKEN}"


@pytest.mark.asyncio
async def test_a_401_refreshes_the_token_and_retries(client, api):
    """An expired token inside the login-throttle window must stay recoverable."""
    original = api.request
    attempts = {"n": 0}

    async def unauthorised_once(**kwargs):
        if "/api/v1/plants" in kwargs["url"]:
            attempts["n"] += 1
            if attempts["n"] == 1:
                return MockResponse(status=401, text="token expired")
        return await original(**kwargs)

    api.request = unauthorised_once

    plants = await client.get_plants()

    assert len(plants) == 1
    assert attempts["n"] == 2
    # Two token requests: the fixture's login, plus the forced refresh.
    assert api.paths().count("/oauth/token/new") == 2


@pytest.mark.asyncio
async def test_a_persistent_error_status_raises(client, api):
    api.set_status("GET", "/api/v1/inverters", 500)

    with pytest.raises(SunsynkApiError) as error:
        await client.get_inverters()

    assert error.value.status_code == 500
    assert error.value.response_body

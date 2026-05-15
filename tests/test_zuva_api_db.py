import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import zuva_api.db as db_module


def test_get_influx_client_uses_module_config(monkeypatch):
    captured = {}

    class FakeInfluxClient:
        def __init__(self, url, token, org):
            captured["url"] = url
            captured["token"] = token
            captured["org"] = org

    monkeypatch.setattr(db_module, "InfluxDBClient", FakeInfluxClient)
    monkeypatch.setattr(db_module, "INFLUXDB_URL", "http://x")
    monkeypatch.setattr(db_module, "INFLUXDB_TOKEN", "t")
    monkeypatch.setattr(db_module, "INFLUXDB_ORG", "o")

    _ = db_module.get_influx_client()

    assert captured == {"url": "http://x", "token": "t", "org": "o"}


def test_get_write_api_calls_client_write_api(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.called = False

        def write_api(self, write_options=None):
            self.called = True
            return "WRITE"

    client = FakeClient()
    result = db_module.get_write_api(client)

    assert client.called is True
    assert result == "WRITE"


def test_get_query_api_calls_client_query_api():
    class FakeClient:
        def query_api(self):
            return "QUERY"

    client = FakeClient()
    result = db_module.get_query_api(client)

    assert result == "QUERY"

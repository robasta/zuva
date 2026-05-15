#!/usr/bin/env bash
set -e

if ! ./venv/bin/python -c "import pytest, pytest_asyncio, pytest_cov" >/dev/null 2>&1; then
  ./venv/bin/pip install pytest pytest-asyncio pytest-cov
fi

if ! ./venv/bin/python -c "import influxdb_client" >/dev/null 2>&1; then
  ./venv/bin/pip install influxdb-client
fi

# API tests import FastAPI/Pydantic and use TestClient backed by httpx.
if ! ./venv/bin/python -c "import fastapi, pydantic, httpx" >/dev/null 2>&1; then
  ./venv/bin/pip install fastapi pydantic httpx
fi

PYTHONPATH=. ./venv/bin/pytest \
  --cov=zuva \
  --cov=zuva_api \
  --cov-report=term-missing \
  tests/test_alert_monitor.py \
  tests/test_alert_logic.py \
  tests/test_notification_sender.py \
  tests/test_telemetry_collector.py \
  tests/test_client_network_errors.py \
  tests/test_zuva_api_models.py \
  tests/test_zuva_api_db.py \
  tests/test_zuva_api_notification_service.py \
  tests/test_zuva_api_main.py

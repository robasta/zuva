#!/usr/bin/env bash
set -e

if [ ! -x ./venv/bin/pytest ]; then
  ./venv/bin/pip install pytest pytest-asyncio pytest-cov
fi

if ! ./venv/bin/python -c "import influxdb_client" >/dev/null 2>&1; then
  ./venv/bin/pip install influxdb-client
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

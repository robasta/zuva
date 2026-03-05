#!/usr/bin/env bash
set -e

if [ ! -x ./venv/bin/pytest ]; then
  ./venv/bin/pip install pytest pytest-asyncio
fi

if ! ./venv/bin/python -c "import influxdb_client" >/dev/null 2>&1; then
  ./venv/bin/pip install influxdb-client
fi

PYTHONPATH=. ./venv/bin/pytest -q tests/test_alert_monitor.py tests/test_client_network_errors.py

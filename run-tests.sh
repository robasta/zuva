#!/usr/bin/env bash
set -e

if [ ! -x ./venv/bin/pytest ]; then
  ./venv/bin/pip install pytest pytest-asyncio
fi

PYTHONPATH=. ./venv/bin/pytest -q tests/test_alert_monitor.py tests/test_client_network_errors.py

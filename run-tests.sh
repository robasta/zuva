#!/usr/bin/env bash
# Runs the whole suite with coverage over all three packages.
#
#   ./run-tests.sh                       # everything
#   ./run-tests.sh tests/test_alert_logic.py
#   ./run-tests.sh -k grid_outage
set -e

if [ ! -x ./venv/bin/python ]; then
  echo "No virtualenv found. Run ./scripts/setup.sh first." >&2
  exit 1
fi

# One check for the whole dev set instead of a chain of per-package installs.
if ! ./venv/bin/python -c "import pytest, pytest_asyncio, pytest_cov, fastapi, pydantic, httpx" >/dev/null 2>&1; then
  ./venv/bin/pip install -q -r requirements-dev.txt
fi

# Test discovery comes from pytest.ini (testpaths + pythonpath), so new test
# files are picked up without editing this script.
exec ./venv/bin/pytest \
  --cov=sunsynk \
  --cov=zuva \
  --cov=zuva_api \
  --cov-report=term-missing \
  --cov-fail-under=85 \
  "$@"

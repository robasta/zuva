#!/usr/bin/env bash
set -e
python3 -m pip install --user virtualenv
python3 -m venv venv
./venv/bin/pip install --upgrade pip
# requirements-dev.txt pulls in requirements.txt plus pytest and pylint, so one
# install covers ./run-tests.sh and ./scripts/run-pylint.sh.
./venv/bin/pip install -r requirements-dev.txt

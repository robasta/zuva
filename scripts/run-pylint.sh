#!/usr/bin/env bash
set -e

if [ ! -x ./venv/bin/pylint ]; then
	./venv/bin/pip install pylint
fi

./venv/bin/pylint --exit-zero sunsynk

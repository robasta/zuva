#!/usr/bin/env bash
# Lints all three deployable packages. Fails the build on real findings, so a
# regression cannot be merged behind a passing-but-ignored lint step.
set -e

cd "$(dirname "$0")/.."

if [ ! -x ./venv/bin/pylint ]; then
	./venv/bin/pip install -q -r requirements-dev.txt
fi

exec ./venv/bin/pylint sunsynk zuva zuva_api "$@"

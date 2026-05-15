#!/bin/bash
if [ "$EUID" -ne 0 ]; then
    if ! pipenv --venv &>/dev/null; then
        echo "Pipenv virtualenv not found, installing dependencies..."
        pipenv install
    fi
    VENV="$(pipenv --venv)"
    exec sudo env VENV="$VENV" PYTHON="$VENV/bin/python3" HOME="$HOME" "$0" "$@"
fi

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="${PYTHON:-$(which python3)}"

$PYTHON "$REPO/experiments/traffic-capture/capture.py"

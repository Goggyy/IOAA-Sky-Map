#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "Installing dependencies..."
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
elif ! .venv/bin/python -c "import PyQt6, numpy, pandas, matplotlib, astropy, skyfield, timezonefinder" >/dev/null 2>&1; then
    echo "Installing updated dependencies..."
    .venv/bin/python -m pip install -r requirements.txt
fi

exec .venv/bin/python main.py

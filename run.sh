#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
if [ ! -x .venv/bin/python ]; then
  echo "Virtual environment missing. Create it with: python3 -m venv .venv" >&2
  exit 1
fi
exec .venv/bin/python app.py

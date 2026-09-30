#!/usr/bin/env bash
# LingoBuddy — one-command start
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
exec .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"

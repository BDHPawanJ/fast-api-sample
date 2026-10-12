#!/bin/sh
# Dev server: uvicorn with auto-reload, always running under debugpy so an
# editor can attach at any time (see .vscode/launch.json).
#
# DEBUGPY_WAIT=1 blocks startup until a debugger attaches, for breakpoints in
# startup code (lifespan, settings).
set -e

wait_flag=""
if [ "${DEBUGPY_WAIT:-0}" = "1" ]; then
    wait_flag="--wait-for-client"
fi

exec python -Xfrozen_modules=off -m debugpy --listen 0.0.0.0:5678 $wait_flag \
    -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app

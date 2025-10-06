#!/usr/bin/env bash
set -euo pipefail
export FLASK_SECRET_KEY="${FLASK_SECRET_KEY:-change-me}"
export PORT=8000
exec python -m backend.main

#!/usr/bin/env bash
set -euo pipefail
exec uvicorn backend.lm_core.api:app --host 0.0.0.0 --port 9001
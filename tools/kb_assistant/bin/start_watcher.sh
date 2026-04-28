#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
exec python3 voice_record_pipeline.py --watch "$@"

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
exec python3 kb_assistant_api.py --host 127.0.0.1 --port 8765

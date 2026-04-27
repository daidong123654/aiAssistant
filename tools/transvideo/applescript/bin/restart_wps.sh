#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config.sh
source "$SCRIPT_DIR/../config.sh"

for name in "${WPS_KILL_NAMES[@]}"; do
  killall "$name" >/dev/null 2>&1 || true
done

sleep 3


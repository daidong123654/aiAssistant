#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config.sh
source "$SCRIPT_DIR/../config.sh"

mkdir -p "$INPUT_DIR" "$PROCESSING_DIR"

for src in "$PROCESSING_DIR"/*; do
  [[ -f "$src" ]] || continue
  dest="$INPUT_DIR/$(basename "$src")"
  mv "$src" "$dest"
  echo "$dest"
done


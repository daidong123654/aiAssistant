#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config.sh
source "$SCRIPT_DIR/../config.sh"

mkdir -p "$INPUT_DIR"

if [[ "$#" -lt 1 ]]; then
  echo "usage: $0 /path/to/audio-or-video [...]" >&2
  exit 64
fi

for src in "$@"; do
  if [[ ! -f "$src" ]]; then
    echo "not a file: $src" >&2
    exit 66
  fi

  base="$(basename "$src")"
  stem="${base%.*}"
  ext="${base##*.}"
  stamp="$(date +%Y%m%d-%H%M%S)"
  dest="$INPUT_DIR/${stem}.${stamp}.$ext"

  cp -p "$src" "$dest"
  echo "$dest"
done


#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config.sh
source "$SCRIPT_DIR/../config.sh"

mkdir -p "$INPUT_DIR" "$PROCESSING_DIR" "$OUTPUT_DIR" "$FAILED_DIR" "$LOG_DIR" "$RUN_DIR"
touch "$LOG_DIR/worker.log"

echo "initialized:"
echo "  input:      $INPUT_DIR"
echo "  processing: $PROCESSING_DIR"
echo "  output:     $OUTPUT_DIR"
echo "  failed:     $FAILED_DIR"
echo "  logs:       $LOG_DIR"


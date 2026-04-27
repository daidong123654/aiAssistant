#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config.sh
source "$SCRIPT_DIR/../config.sh"

LOCK_DIR="$RUN_DIR/worker.lock"
JOBS_DONE_FILE="$RUN_DIR/jobs_done"

log() {
  mkdir -p "$LOG_DIR"
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_DIR/worker.log"
}

cleanup_lock() {
  if [[ -f "$LOCK_DIR/pid" ]] && [[ "$(cat "$LOCK_DIR/pid")" == "$$" ]]; then
    rm -f "$LOCK_DIR/pid"
    rmdir "$LOCK_DIR" >/dev/null 2>&1 || true
  fi
}

acquire_lock() {
  mkdir -p "$RUN_DIR"
  while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    if [[ -f "$LOCK_DIR/pid" ]]; then
      local existing_pid
      existing_pid="$(cat "$LOCK_DIR/pid")"
      if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" >/dev/null 2>&1; then
        echo "another worker is already running: pid=$existing_pid" >&2
        exit 75
      fi
    fi
    rm -rf "$LOCK_DIR"
  done
  printf '%s\n' "$$" > "$LOCK_DIR/pid"
  trap cleanup_lock EXIT INT TERM
}

ensure_dirs() {
  mkdir -p "$INPUT_DIR" "$PROCESSING_DIR" "$OUTPUT_DIR" "$FAILED_DIR" "$LOG_DIR" "$RUN_DIR"
  [[ -f "$JOBS_DONE_FILE" ]] || printf '0\n' > "$JOBS_DONE_FILE"
}

is_supported_file() {
  local path="$1"
  local ext="${path##*.}"
  ext="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
  [[ " $SUPPORTED_EXTENSIONS " == *" $ext "* ]]
}

next_job() {
  local file
  while IFS= read -r -d '' file; do
    if is_supported_file "$file"; then
      printf '%s\n' "$file"
      return 0
    fi
  done < <(find "$INPUT_DIR" -maxdepth 1 -type f -print0)
  return 1
}

snapshot_exports() {
  local snapshot="$1"
  : > "$snapshot"
  local dir
  for dir in "${EXPORT_WATCH_DIRS[@]}"; do
    [[ -d "$dir" ]] || continue
    find "$dir" -maxdepth 1 -type f \( -iname '*.txt' -o -iname '*.srt' \) -print >> "$snapshot"
  done
}

find_new_export() {
  local before="$1"
  local started_at="$2"
  local candidate dir

  for dir in "${EXPORT_WATCH_DIRS[@]}"; do
    [[ -d "$dir" ]] || continue
    while IFS= read -r candidate; do
      [[ -f "$candidate" ]] || continue
      if grep -Fxq "$candidate" "$before"; then
        continue
      fi
      if [[ "$candidate" -nt "$started_at" ]]; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done < <(find "$dir" -maxdepth 1 -type f \( -iname '*.txt' -o -iname '*.srt' \) -print)
  done

  return 1
}

kill_wps() {
  local name
  for name in "${WPS_KILL_NAMES[@]}"; do
    killall "$name" >/dev/null 2>&1 || true
  done
}

run_with_timeout() {
  local timeout_seconds="$1"
  local output_file="$2"
  shift 2

  "$@" > "$output_file" 2>&1 &
  local cmd_pid="$!"
  local deadline=$(( $(date +%s) + timeout_seconds ))

  while kill -0 "$cmd_pid" >/dev/null 2>&1; do
    if (( $(date +%s) >= deadline )); then
      kill "$cmd_pid" >/dev/null 2>&1 || true
      sleep 1
      kill -9 "$cmd_pid" >/dev/null 2>&1 || true
      wait "$cmd_pid" >/dev/null 2>&1 || true
      return 124
    fi
    sleep 1
  done

  wait "$cmd_pid"
}

log_script_output() {
  local label="$1"
  local output_file="$2"

  if [[ -s "$output_file" ]]; then
    while IFS= read -r line; do
      log "$label: $line"
    done < "$output_file"
  fi
}

maybe_restart_wps() {
  local done_count
  done_count="$(cat "$JOBS_DONE_FILE")"
  if (( RESTART_WPS_EVERY_JOBS > 0 && done_count > 0 && done_count % RESTART_WPS_EVERY_JOBS == 0 )); then
    log "restart WPS after $done_count jobs"
    "$SCRIPT_DIR/restart_wps.sh"
  fi
}

collect_export() {
  local exported="$1"
  local job="$2"
  local ext base dest

  ext="${exported##*.}"
  base="$(basename "$job")"
  base="${base%.*}"
  dest="$OUTPUT_DIR/$base.$ext"

  if [[ "$exported" == "$dest" ]]; then
    printf '%s\n' "$dest"
    return 0
  fi

  mv "$exported" "$dest"
  printf '%s\n' "$dest"
}

process_job() {
  local src="$1"
  local base job before started_at exported dest deadline now script_log next_heartbeat remaining

  base="$(basename "$src")"
  job="$PROCESSING_DIR/$base"
  mv "$src" "$job"

  before="$RUN_DIR/export-before.$$"
  started_at="$RUN_DIR/job-started.$$"
  script_log="$RUN_DIR/osascript.$$"
  touch "$started_at"
  snapshot_exports "$before"

  log "start: $job"

  log "trigger quick action"
  if ! run_with_timeout "$TRIGGER_TIMEOUT_SECONDS" "$script_log" osascript "$TRIGGER_SCPT" "$job" "$QUICK_ACTION_KEY"; then
    log_script_output "trigger" "$script_log"
    log "trigger failed: $job"
    mv "$job" "$FAILED_DIR/$base"
    rm -f "$before" "$started_at" "$script_log"
    return 1
  fi
  log_script_output "trigger" "$script_log"

  log "click start/export"
  if ! run_with_timeout "$EXPORT_TIMEOUT_SECONDS" "$script_log" osascript "$EXPORT_SCPT" "$START_CLICK_DELAY_SECONDS" "$EXPORT_CLICK_DELAY_SECONDS"; then
    log_script_output "export" "$script_log"
    log "export ui step failed or timed out, continue watching output"
  else
    log_script_output "export" "$script_log"
    log "export ui step done"
  fi

  deadline=$(( $(date +%s) + TRANSCRIBE_TIMEOUT_SECONDS ))
  next_heartbeat=$(( $(date +%s) + WATCH_HEARTBEAT_SECONDS ))
  log "watch output for ${TRANSCRIBE_TIMEOUT_SECONDS}s"
  while true; do
    if exported="$(find_new_export "$before" "$started_at")"; then
      dest="$(collect_export "$exported" "$job")"
      rm -f "$job" "$before" "$started_at" "$script_log"
      printf '%s\n' "$(( $(cat "$JOBS_DONE_FILE") + 1 ))" > "$JOBS_DONE_FILE"
      log "success: $dest"
      maybe_restart_wps
      return 0
    fi

    now="$(date +%s)"
    if (( WATCH_HEARTBEAT_SECONDS > 0 && now >= next_heartbeat )); then
      remaining=$(( deadline - now ))
      (( remaining < 0 )) && remaining=0
      log "still watching output, ${remaining}s remaining"
      next_heartbeat=$(( now + WATCH_HEARTBEAT_SECONDS ))
    fi

    if (( now >= deadline )); then
      log "timeout: $job"
      kill_wps
      mv "$job" "$FAILED_DIR/$base"
      rm -f "$before" "$started_at" "$script_log"
      return 124
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done
}

run_once() {
  local job
  if job="$(next_job)"; then
    process_job "$job"
  else
    return 1
  fi
}

main() {
  local mode="${1:-}"

  ensure_dirs
  acquire_lock

  if [[ "$mode" == "--daemon" ]]; then
    log "daemon started"
    while true; do
      run_once || sleep "$DAEMON_SLEEP_SECONDS"
    done
  else
    run_once || log "no job"
  fi
}

main "$@"

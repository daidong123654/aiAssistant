#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import datetime as dt
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import urllib.parse

import n8n_notify
import openclaw_message
import voice_record_pipeline


WORK_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_SCRIPT = Path(__file__).resolve().parent / "voice_record_pipeline.py"
AUDIO_JOB_ROOT = WORK_ROOT / "data" / "jobs" / "audio"


def now_iso():
    return dt.datetime.now().isoformat(timespec="seconds")


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json_body(handler):
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def write_json_file(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def today_ymd():
    return dt.datetime.now().strftime("%Y%m%d")


def ensure_safe_audio_path(audio_path):
    path = Path(audio_path).expanduser().resolve()
    work_root = WORK_ROOT.resolve()
    try:
        path.relative_to(work_root)
    except ValueError as exc:
        raise ValueError(f"audio_path 必须位于 {work_root} 下：{path}") from exc
    if not path.exists():
        raise FileNotFoundError(f"音频文件不存在：{path}")
    if not path.is_file():
        raise ValueError(f"audio_path 不是文件：{path}")
    if path.suffix.lower() not in voice_record_pipeline.AUDIO_SUFFIXES:
        raise ValueError(f"不支持的音频格式：{path.suffix}")
    return path


def build_job_id(audio_path, payload):
    explicit_key = payload.get("idempotency_key") or payload.get("message_id")
    if explicit_key:
        return hashlib.sha256(f"idempotency:{explicit_key}".encode("utf-8")).hexdigest()[:20]
    stat = audio_path.stat()
    material = "|".join(
        [
            str(explicit_key or ""),
            str(audio_path),
            str(stat.st_size),
            str(int(stat.st_mtime)),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def job_paths(job_id, date=None):
    job_dir = AUDIO_JOB_ROOT / (date or today_ymd()) / job_id
    return {
        "dir": job_dir,
        "state": job_dir / "job.json",
        "stdout": job_dir / "stdout.log",
        "stderr": job_dir / "stderr.log",
    }


def find_job_state(job_id):
    for state_path in sorted(AUDIO_JOB_ROOT.glob(f"*/{job_id}/job.json")):
        return state_path
    return None


def process_is_running(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def refresh_job_state(state_path):
    state = read_json_file(state_path)
    if state.get("status") == "running" and not process_is_running(state.get("pid")):
        state["status"] = "unknown"
        state["updated_at"] = now_iso()
        state["message"] = "API 重启或子进程已退出；最终结果以 notifications/status.json 为准。"
        write_json_file(state_path, state)
    return state


def mark_job_finished(state_path, return_code):
    state = read_json_file(state_path)
    state["return_code"] = return_code
    state["updated_at"] = now_iso()
    state["status"] = "completed" if return_code == 0 else "failed"
    write_json_file(state_path, state)


def wait_and_mark(process, state_path):
    return_code = process.wait()
    mark_job_finished(state_path, return_code)


def submit_audio_job(payload):
    explicit_key = payload.get("idempotency_key") or payload.get("message_id")
    if explicit_key:
        job_id = hashlib.sha256(f"idempotency:{explicit_key}".encode("utf-8")).hexdigest()[:20]
        existing_state_path = find_job_state(job_id)
        if existing_state_path:
            state = refresh_job_state(existing_state_path)
            state["deduplicated"] = True
            return state

    audio_path = ensure_safe_audio_path(payload.get("audio_path") or payload.get("save_path") or "")
    job_id = build_job_id(audio_path, payload)
    existing_state_path = find_job_state(job_id)
    if existing_state_path:
        state = refresh_job_state(existing_state_path)
        if state.get("status") in {"running", "completed"}:
            state["deduplicated"] = True
            return state

    paths = job_paths(job_id, payload.get("date"))
    paths["dir"].mkdir(parents=True, exist_ok=True)
    lock_path = paths["dir"] / "job.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(lock_fd, now_iso().encode("utf-8"))
        os.close(lock_fd)
    except FileExistsError:
        if paths["state"].exists():
            state = refresh_job_state(paths["state"])
            state["deduplicated"] = True
            return state
        raise RuntimeError(f"job 正在提交中：{job_id}")

    stdout = paths["stdout"].open("ab")
    stderr = paths["stderr"].open("ab")
    command = [
        sys.executable,
        str(PIPELINE_SCRIPT),
        str(audio_path),
    ]
    process = subprocess.Popen(
        command,
        cwd=str(PIPELINE_SCRIPT.parent),
        stdout=stdout,
        stderr=stderr,
        close_fds=True,
    )
    stdout.close()
    stderr.close()
    state = {
        "job_id": job_id,
        "status": "running",
        "pid": process.pid,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audio_path": str(audio_path),
        "command": command,
        "stdout": str(paths["stdout"]),
        "stderr": str(paths["stderr"]),
        "message_id": payload.get("message_id"),
        "from_user": payload.get("from_user"),
    }
    write_json_file(paths["state"], state)
    thread = threading.Thread(target=wait_and_mark, args=(process, paths["state"]), daemon=True)
    thread.start()
    return state


class Handler(BaseHTTPRequestHandler):
    inbox_root = WORK_ROOT / "data" / "src" / "media"
    output_root = WORK_ROOT / "data" / "dst"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/health":
            json_response(self, 200, {"ok": True})
            return
        if parsed.path.startswith("/audio/jobs/"):
            job_id = parsed.path.rstrip("/").split("/")[-1]
            state_path = find_job_state(job_id)
            if not state_path:
                json_response(self, 404, {"error": f"job not found: {job_id}"})
                return
            json_response(self, 200, refresh_job_state(state_path))
            return
        if parsed.path == "/notifications":
            date = query.get("date", [n8n_notify.today_ymd()])[0]
            include_failed = query.get("include_failed", ["0"])[0] in {"1", "true", "yes"}
            limit = int(query.get("limit", ["20"])[0])
            payload = n8n_notify.list_pending(
                self.output_root,
                date,
                include_failed=include_failed,
                limit=limit,
            )
            json_response(self, 200, payload)
            return
        json_response(self, 404, {"error": f"not found: {parsed.path}"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path == "/openclaw/normalize":
                payload = read_json_body(self)
                result = openclaw_message.normalize(payload, self.inbox_root)
                result["container_save_path"] = result["save_path"].replace(
                    str(WORK_ROOT),
                    "/work",
                    1,
                )
                json_response(self, 200, result)
                return
            if parsed.path == "/audio/jobs":
                payload = read_json_body(self)
                result = submit_audio_job(payload)
                status_code = 200 if result.get("deduplicated") else 202
                json_response(self, status_code, result)
                return
            if parsed.path == "/notifications/mark":
                payload = read_json_body(self)
                metadata = payload.get("metadata_file") or payload.get("metadata")
                if not metadata:
                    json_response(self, 400, {"error": "missing metadata_file"})
                    return
                marker = n8n_notify.mark_notified(Path(metadata))
                json_response(self, 200, marker)
                return
            json_response(self, 404, {"error": f"not found: {parsed.path}"})
        except (FileNotFoundError, ValueError) as exc:
            json_response(self, 400, {"error": str(exc)})
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})


def parse_args():
    parser = argparse.ArgumentParser(description="本地知识库助手 API，供 n8n 调用。")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--inbox-root", default=str(WORK_ROOT / "data" / "src" / "media"), type=Path)
    parser.add_argument("--output-root", default=str(WORK_ROOT / "data" / "dst"), type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    Handler.inbox_root = args.inbox_root.expanduser().resolve()
    Handler.output_root = args.output_root.expanduser().resolve()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"kb_assistant_api listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

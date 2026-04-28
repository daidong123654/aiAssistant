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
AUDIO_CONFIRM_ROOT = WORK_ROOT / "data" / "jobs" / "audio_confirmations"


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


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_job_id(audio_path, payload):
    force_run_id = payload.get("force_run_id")
    if force_run_id:
        return hashlib.sha256(f"force:{force_run_id}".encode("utf-8")).hexdigest()[:20]
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


def iter_job_states():
    for state_path in sorted(AUDIO_JOB_ROOT.glob("*/**/job.json"), reverse=True):
        try:
            yield state_path, read_json_file(state_path)
        except (OSError, json.JSONDecodeError):
            continue


def job_has_finished_output(state):
    if state.get("status") != "completed":
        return False
    audio_path = Path(state.get("audio_path") or "")
    for metadata_path in sorted((WORK_ROOT / "data" / "dst").glob("*/**/metadata.json"), reverse=True):
        try:
            metadata = read_json_file(metadata_path)
        except (OSError, json.JSONDecodeError):
            continue
        if metadata.get("source_file") == str(audio_path):
            return True
    return True


def iter_transcribed_outputs():
    for status_path in sorted((WORK_ROOT / "data" / "dst").glob("*/**/status.json"), reverse=True):
        task_dir = status_path.parent
        try:
            status = read_json_file(status_path)
        except (OSError, json.JSONDecodeError):
            continue
        if status.get("status") == "failed":
            continue
        if not list(task_dir.glob("**/*.docx")) and not list(task_dir.glob("**/*.txt")):
            continue
        yield status_path, status


def find_completed_audio_matches(audio_path, audio_hash, payload):
    original_file_name = payload.get("original_file_name") or payload.get("file_name") or audio_path.name
    original_file_path = payload.get("original_file_path") or payload.get("save_path") or str(audio_path)
    matches = []
    for status_path, status in iter_transcribed_outputs():
        source_file = status.get("source_file")
        original_path = status.get("original_file_path")
        original_name = status.get("original_file_name")
        if source_file == str(audio_path) or original_path == original_file_path:
            matches.append((status_path, status, "output_path"))
            continue
        if original_name and original_name == original_file_name:
            old_path = Path(source_file or original_path or "")
            if old_path.exists() and old_path.is_file():
                try:
                    if sha256_file(old_path) == audio_hash:
                        matches.append((status_path, status, "output_hash"))
                except OSError:
                    pass
    for state_path, state in iter_job_states():
        if not job_has_finished_output(state):
            continue
        if state.get("audio_hash") and state.get("audio_hash") == audio_hash:
            matches.append((state_path, state, "sha256"))
            continue
        if state.get("audio_path") == str(audio_path) or state.get("original_file_path") == original_file_path:
            matches.append((state_path, state, "path"))
            continue
        if state.get("original_file_name") == original_file_name:
            old_path = Path(state.get("audio_path") or "")
            if old_path.exists() and old_path.is_file():
                try:
                    if sha256_file(old_path) == audio_hash:
                        state["audio_hash"] = audio_hash
                        write_json_file(state_path, state)
                        matches.append((state_path, state, "sha256_backfill"))
                except OSError:
                    pass
    return matches


def confirmation_paths(confirmation_id, date=None):
    confirm_dir = AUDIO_CONFIRM_ROOT / (date or today_ymd()) / confirmation_id
    return {
        "dir": confirm_dir,
        "state": confirm_dir / "confirmation.json",
    }


def find_confirmation_state(confirmation_id):
    for state_path in sorted(AUDIO_CONFIRM_ROOT.glob(f"*/{confirmation_id}/confirmation.json")):
        return state_path
    return None


def build_confirmation_id(audio_hash, payload):
    material = "|".join(
        [
            audio_hash,
            str(payload.get("from_user") or ""),
            str(payload.get("message_id") or ""),
            str(payload.get("original_file_path") or payload.get("audio_path") or payload.get("save_path") or ""),
        ]
    )
    return hashlib.sha256(f"confirm:{material}".encode("utf-8")).hexdigest()[:10]


def create_duplicate_confirmation(audio_path, audio_hash, payload, matches):
    confirmation_id = build_confirmation_id(audio_hash, payload)
    paths = confirmation_paths(confirmation_id, payload.get("date"))
    if paths["state"].exists():
        state = read_json_file(paths["state"])
        if state.get("status") == "pending":
            return state
    original_file_name = payload.get("original_file_name") or payload.get("file_name") or audio_path.name
    state = {
        "confirmation_id": confirmation_id,
        "status": "pending",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audio_path": str(audio_path),
        "audio_hash": audio_hash,
        "original_file_name": original_file_name,
        "original_file_path": payload.get("original_file_path") or payload.get("save_path") or str(audio_path),
        "message_id": payload.get("message_id"),
        "from_user": payload.get("from_user"),
        "request_payload": payload,
        "matched_jobs": [
            {
                "job_id": match_state.get("job_id"),
                "status": match_state.get("status"),
                "created_at": match_state.get("created_at"),
                "audio_path": match_state.get("audio_path") or match_state.get("source_file"),
                "original_file_name": match_state.get("original_file_name"),
                "match_reason": reason,
                "job_state": str(state_path),
            }
            for state_path, match_state, reason in matches[:5]
        ],
        "message": (
            "检测到这段音频已经转写过，已暂停本次转写。\n"
            f"- 原始文件名：{original_file_name}\n"
            f"- 确认码：{confirmation_id}\n"
            f"如需重新转写，请回复：确认重转 {confirmation_id}"
        ),
    }
    write_json_file(paths["state"], state)
    return state


def list_pending_confirmations(limit=20):
    pending = []
    for state_path in sorted(AUDIO_CONFIRM_ROOT.glob("*/**/confirmation.json")):
        try:
            state = read_json_file(state_path)
        except (OSError, json.JSONDecodeError):
            continue
        if state.get("status") != "pending" or (state_path.parent / ".notified").exists():
            continue
        pending.append(
            {
                "notification_type": state.get("confirmation_type") or "duplicate_confirmation",
                "confirmation_type": state.get("confirmation_type") or "duplicate",
                "confirmation_id": state.get("confirmation_id"),
                "status": state.get("status"),
                "metadata_file": str(state_path),
                "confirmation_file": str(state_path),
                "from_user": state.get("from_user"),
                "original_file_name": state.get("original_file_name"),
                "message": state.get("message"),
            }
        )
        if len(pending) >= limit:
            break
    return pending


def mark_confirmation_notified(confirmation_path):
    state_path = Path(confirmation_path).expanduser().resolve()
    if state_path.name != "confirmation.json":
        raise ValueError(f"不是 confirmation.json：{state_path}")
    marker = {
        "notified_at": now_iso(),
        "confirmation_file": str(state_path),
    }
    write_json_file(state_path.parent / ".notified", marker)
    return marker


def text_confirms_retry(text):
    normalized = str(text or "").strip().lower()
    if not normalized:
        return False
    if normalized in {"yes", "y"}:
        return True
    return any(token in normalized for token in ["确认重转", "确认本地", "重新转", "重转", "确认"])


def text_declines_confirmation(text):
    normalized = str(text or "").strip().lower()
    if not normalized:
        return False
    if normalized in {"no", "n"}:
        return True
    return any(token in normalized for token in ["取消", "不转", "不用", "否"])


def find_pending_confirmation_for_reply(text, from_user):
    candidates = []
    for state_path in sorted(AUDIO_CONFIRM_ROOT.glob("*/**/confirmation.json"), reverse=True):
        state = read_json_file(state_path)
        if state.get("status") != "pending":
            continue
        if from_user and state.get("from_user") not in {None, "", from_user}:
            continue
        if state.get("confirmation_id") in text or not candidates:
            candidates.append((state_path, state))
        if state.get("confirmation_id") in text:
            break
    if not candidates:
        return None, None
    return candidates[0]


def resolve_audio_confirmation(payload):
    text = payload.get("message_text") or payload.get("text") or payload.get("content") or ""
    from_user = payload.get("from_user")
    if not text_confirms_retry(text) and not text_declines_confirmation(text):
        return {"ok": False, "status": "ignored", "message": "未识别为确认消息。"}

    state_path, state = find_pending_confirmation_for_reply(text, from_user)
    if not state_path:
        return {"ok": False, "status": "not_found", "message": "没有找到待确认的音频任务。"}

    if text_declines_confirmation(text):
        confirmation_type = state.get("confirmation_type") or "duplicate"
        state["status"] = "declined"
        state["declined_at"] = now_iso()
        state["declined_by_message_id"] = payload.get("message_id")
        state["updated_at"] = now_iso()
        write_json_file(state_path, state)
        return {
            "ok": True,
            "status": "declined",
            "confirmation_id": state.get("confirmation_id"),
            "message": (
                "已取消，本次不会使用本地模型转写。"
                if confirmation_type == "local_funasr_fallback"
                else "已取消，本次不会重新转写。"
            ),
        }

    request_payload = dict(state.get("request_payload") or {})
    request_payload["force"] = True
    request_payload["force_run_id"] = f"{state.get('confirmation_id')}:{now_iso()}"
    request_payload.pop("idempotency_key", None)
    if state.get("confirmation_type") == "local_funasr_fallback":
        request_payload["local_funasr_confirmed"] = True
    result = submit_audio_job(request_payload)
    state["status"] = "confirmed"
    state["confirmed_at"] = now_iso()
    state["confirmed_by_message_id"] = payload.get("message_id")
    state["new_job_id"] = result.get("job_id")
    state["updated_at"] = now_iso()
    write_json_file(state_path, state)
    return {
        "ok": True,
        "status": "confirmed",
        "confirmation_id": state.get("confirmation_id"),
        "job_id": result.get("job_id"),
        "message": f"已确认，任务已提交：{result.get('job_id')}",
    }


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
    force = payload.get("force") is True or str(payload.get("force")).lower() in {"1", "true", "yes"}
    explicit_key = payload.get("idempotency_key") or payload.get("message_id")
    if explicit_key and not force:
        job_id = hashlib.sha256(f"idempotency:{explicit_key}".encode("utf-8")).hexdigest()[:20]
        existing_state_path = find_job_state(job_id)
        if existing_state_path:
            state = refresh_job_state(existing_state_path)
            state["deduplicated"] = True
            return state

    audio_path = ensure_safe_audio_path(payload.get("audio_path") or payload.get("save_path") or "")
    audio_hash = sha256_file(audio_path)
    if not force:
        matches = find_completed_audio_matches(audio_path, audio_hash, payload)
        if matches:
            state = create_duplicate_confirmation(audio_path, audio_hash, payload, matches)
            state["deduplicated"] = True
            state["requires_confirmation"] = True
            return state

    job_id = build_job_id(audio_path, payload)
    existing_state_path = find_job_state(job_id)
    if existing_state_path and not force:
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
    original_file_name = payload.get("original_file_name") or payload.get("file_name") or audio_path.name
    original_file_path = payload.get("original_file_path") or payload.get("save_path") or str(audio_path)
    command.extend(["--original-file-name", str(original_file_name)])
    command.extend(["--original-file-path", str(original_file_path)])
    if payload.get("message_id"):
        command.extend(["--message-id", str(payload.get("message_id"))])
    if payload.get("from_user"):
        command.extend(["--from-user", str(payload.get("from_user"))])
    if payload.get("local_funasr_confirmed") is True or str(payload.get("local_funasr_confirmed")).lower() in {"1", "true", "yes"}:
        command.append("--local-funasr-confirmed")
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
        "audio_hash": audio_hash,
        "force": force,
        "original_file_name": original_file_name,
        "original_file_path": original_file_path,
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
            if len(payload) < limit:
                payload.extend(list_pending_confirmations(limit - len(payload)))
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
            if parsed.path == "/audio/confirmations/resolve":
                payload = read_json_body(self)
                result = resolve_audio_confirmation(payload)
                json_response(self, 200, result)
                return
            if parsed.path == "/notifications/mark":
                payload = read_json_body(self)
                metadata = payload.get("metadata_file") or payload.get("metadata")
                if not metadata:
                    json_response(self, 400, {"error": "missing metadata_file"})
                    return
                metadata_path = Path(metadata)
                if metadata_path.name == "confirmation.json":
                    marker = mark_confirmation_notified(metadata_path)
                else:
                    marker = n8n_notify.mark_notified(metadata_path)
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

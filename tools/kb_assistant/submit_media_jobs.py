#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

import voice_record_pipeline


WORK_ROOT = Path(__file__).resolve().parents[2]


def audio_files(root):
    for path in sorted(root.rglob("*")):
        if path.name.startswith("."):
            continue
        if path.is_file() and path.suffix.lower() in voice_record_pipeline.AUDIO_SUFFIXES:
            yield path


def submit_job(api_url, path):
    payload = {
        "audio_path": str(path.resolve()),
        "original_file_name": path.name,
        "original_file_path": str(path.resolve()),
        "message_id": path.stem,
        "from_user": "manual",
        "idempotency_key": f"path:{path.resolve()}",
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/audio/jobs",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        try:
            payload = json.loads(error_body)
        except json.JSONDecodeError:
            payload = {"error": error_body}
        return exc.code, payload


def parse_args():
    parser = argparse.ArgumentParser(description="扫描 media inbox，并把手工放入的音频提交给 kb_assistant_api。")
    parser.add_argument("--inbox-root", default=str(WORK_ROOT / "data" / "src" / "media"), type=Path)
    parser.add_argument("--api-url", default="http://127.0.0.1:8765")
    parser.add_argument("--min-age", default=60, type=int, help="只提交最后修改时间早于该秒数的文件")
    parser.add_argument("--max-submit", default=1, type=int, help="单次扫描最多提交多少个新文件")
    return parser.parse_args()


def main():
    args = parse_args()
    inbox = args.inbox_root.expanduser().resolve()
    if not inbox.exists():
        print(f"inbox 不存在，跳过：{inbox}")
        return

    now = time.time()
    submitted = 0
    for path in audio_files(inbox):
        try:
            age = now - path.stat().st_mtime
        except FileNotFoundError:
            continue
        if age < args.min_age:
            continue
        status, payload = submit_job(args.api_url, path)
        print(json.dumps({"file": str(path), "http_status": status, "response": payload}, ensure_ascii=False))
        if status in {200, 202}:
            submitted += 1
        if submitted >= args.max_submit:
            break

    if submitted == 0:
        print("没有需要提交的新音频。")


if __name__ == "__main__":
    main()

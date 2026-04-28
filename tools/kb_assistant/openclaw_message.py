#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys


WORK_ROOT = Path(__file__).resolve().parents[2]


def today_ymd():
    return dt.datetime.now().strftime("%Y%m%d")


def safe_name(value, fallback):
    value = str(value or fallback).strip()
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE).strip("._")
    return value or fallback


def ext_from_payload(payload):
    file_name = payload.get("file_name") or payload.get("filename") or ""
    suffix = Path(file_name).suffix.lower()
    if suffix:
        return suffix
    mime = str(payload.get("mime_type") or payload.get("content_type") or "").lower()
    mapping = {
        "audio/amr": ".amr",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
    }
    return mapping.get(mime, ".amr")


def normalize(payload, inbox_root):
    if isinstance(payload.get("body"), dict):
        payload = payload["body"]
    ymd = today_ymd()
    message_id = safe_name(payload.get("message_id") or payload.get("msg_id"), "message")
    from_user = safe_name(payload.get("from_user") or payload.get("sender") or payload.get("user"), "unknown")
    ext = ext_from_payload(payload)
    inbox_dir = (inbox_root / ymd).expanduser().resolve()
    file_path = inbox_dir / f"{message_id}_{from_user}{ext}"
    return {
        "date": ymd,
        "message_id": message_id,
        "from_user": from_user,
        "message_type": payload.get("message_type") or payload.get("type"),
        "message_text": payload.get("text") or payload.get("content") or payload.get("message") or "",
        "file_url": payload.get("file_url") or payload.get("url"),
        "file_name": payload.get("file_name") or payload.get("filename"),
        "inbox_dir": str(inbox_dir),
        "save_path": str(file_path),
    }


def parse_args():
    parser = argparse.ArgumentParser(description="标准化 OpenClaw 微信消息，生成 n8n 保存路径。")
    parser.add_argument("--inbox-root", default=str(WORK_ROOT / "data" / "src" / "media"), type=Path)
    parser.add_argument("--payload", help="消息 JSON 字符串；不传则从 stdin 读取")
    return parser.parse_args()


def main():
    args = parse_args()
    raw = args.payload if args.payload else sys.stdin.read()
    payload = json.loads(raw)
    result = normalize(payload, args.inbox_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

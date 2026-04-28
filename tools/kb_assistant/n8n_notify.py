#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import datetime as dt
import json
from pathlib import Path


WORK_ROOT = Path(__file__).resolve().parents[2]


def today_ymd():
    return dt.datetime.now().strftime("%Y%m%d")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def task_dir_from_metadata(metadata_path):
    path = Path(metadata_path).expanduser().resolve()
    if path.name != "metadata.json":
        raise ValueError(f"不是 metadata.json：{path}")
    return path.parent


def build_notification(task_dir):
    metadata_path = task_dir / "metadata.json"
    status_path = task_dir / "status.json"
    metadata = read_json(metadata_path)
    status = read_json(status_path) if status_path.exists() else {"status": metadata.get("status")}
    return {
        "job_name": metadata.get("job_name") or task_dir.name,
        "date": metadata.get("date"),
        "status": status.get("status") or metadata.get("status"),
        "metadata_file": str(metadata_path),
        "task_dir": str(task_dir),
        "transcript_docx": metadata.get("transcript_docx"),
        "minutes_md": metadata.get("minutes_md"),
        "source_file": metadata.get("source_file"),
        "segment_count": metadata.get("segment_count"),
        "transcript_chars": metadata.get("transcript_chars"),
        "paperless_imported": metadata.get("paperless_imported", []),
        "dify_import": metadata.get("dify_import"),
        "dify_error": metadata.get("dify_error"),
        "message": (
            "语音记录已生成：\n"
            f"- 转写文档：{metadata.get('transcript_docx')}\n"
            f"- 会议纪要：{metadata.get('minutes_md')}\n"
            "- 已提交 Paperless 归档\n"
            f"- Dify 导入：{'已导入' if metadata.get('dify_import') else ('失败' if metadata.get('dify_error') else '未配置/跳过')}"
        ),
    }


def list_pending(output_root, date, include_failed=False, limit=20):
    day_dir = output_root / date
    if not day_dir.exists():
        return []
    pending = []
    for metadata_path in sorted(day_dir.glob("*/metadata.json")):
        task_dir = metadata_path.parent
        if (task_dir / ".notified").exists():
            continue
        status_path = task_dir / "status.json"
        status = read_json(status_path).get("status") if status_path.exists() else "completed"
        if status == "completed":
            pending.append(build_notification(task_dir))
        elif include_failed and (task_dir / "error.json").exists():
            error_payload = read_json(task_dir / "error.json")
            pending.append(
                {
                    "job_name": task_dir.name,
                    "date": date,
                    "status": "failed",
                    "task_dir": str(task_dir),
                    "error": error_payload.get("error"),
                    "message": f"语音记录处理失败：{error_payload.get('error')}",
                }
            )
        if len(pending) >= limit:
            break
    return pending


def mark_notified(metadata_path):
    task_dir = task_dir_from_metadata(metadata_path)
    marker = {
        "notified_at": dt.datetime.now().isoformat(timespec="seconds"),
        "metadata_file": str(task_dir / "metadata.json"),
    }
    write_json(task_dir / ".notified", marker)
    return marker


def parse_args():
    parser = argparse.ArgumentParser(description="n8n 结果通知辅助工具。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="列出未通知的已完成任务")
    list_parser.add_argument("--output-root", default=str(WORK_ROOT / "data" / "dst"), type=Path)
    list_parser.add_argument("--date", default=today_ymd())
    list_parser.add_argument("--include-failed", action="store_true")
    list_parser.add_argument("--limit", default=20, type=int)

    mark_parser = subparsers.add_parser("mark", help="标记某个任务已通知")
    mark_parser.add_argument("metadata", type=Path)

    return parser.parse_args()


def main():
    args = parse_args()
    if args.command == "list":
        output_root = args.output_root.expanduser().resolve()
        payload = list_pending(output_root, args.date, args.include_failed, args.limit)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if args.command == "mark":
        marker = mark_notified(args.metadata)
        print(json.dumps(marker, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

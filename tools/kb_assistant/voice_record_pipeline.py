#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import urllib.error
import urllib.request


WORK_ROOT = Path(__file__).resolve().parents[2]
XFYUNLLM_DIR = WORK_ROOT / "tools" / "transvideo" / "xfyunllm"
if str(XFYUNLLM_DIR) not in sys.path:
    sys.path.insert(0, str(XFYUNLLM_DIR))

import Ifasr  # noqa: E402


AUDIO_SUFFIXES = {
    ".aac",
    ".amr",
    ".flac",
    ".m4a",
    ".mp3",
    ".mp4",
    ".ogg",
    ".opus",
    ".wav",
    ".weba",
    ".wma",
}


def today_ymd():
    return dt.datetime.now().strftime("%Y%m%d")


def now_stamp():
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    return path


def stable_job_name(source):
    safe_stem = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in source.stem)
    return f"{now_stamp()}_{safe_stem}"


def write_json_file(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_status(output_dir, status, **extra):
    payload = {
        "status": status,
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        **extra,
    }
    write_json_file(output_dir / "status.json", payload)
    return payload


def write_error(output_dir, exc):
    error_payload = {
        "status": "failed",
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "error": str(exc),
        "traceback": traceback.format_exc(),
    }
    write_json_file(output_dir / "error.json", error_payload)
    (output_dir / "error.log").write_text(error_payload["traceback"], encoding="utf-8")
    write_status(output_dir, "failed", error=str(exc))


def read_transcript(json_path):
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    lines = [segment["line"] for segment in payload.get("segments", []) if segment.get("line")]
    plain_text = "\n".join(segment.get("text", "") for segment in payload.get("segments", []))
    return "\n".join(lines), plain_text, payload


def strip_deepseek_thinking(text):
    if "</think>" in text:
        return text.split("</think>", 1)[1].strip()
    return text.strip()


def generate_minutes_with_llm(transcript, model, llm_url, timeout, api_key):
    prompt = f"""你是一个中文会议纪要助手。请根据以下语音转写记录生成会议纪要。

要求：
1. 使用 Markdown。
2. 保留事实，不编造没有出现的信息。
3. 输出结构包括：会议摘要、关键议题、决策结论、待办事项、风险与跟进、原始记录索引。
4. 待办事项如果无法确认负责人或截止时间，请写“未明确”。
5. 原始记录索引用时间轴引用，例如 [00:01:20 - 00:01:48]。

语音转写记录：
{transcript}
"""
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.2,
            "max_tokens": 4096,
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        f"{llm_url.rstrip('/')}/chat/completions",
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"调用本地 MLX 模型失败：{exc}") from exc
    result = json.loads(body)
    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"本地 MLX 模型返回异常：{body}") from exc
    return strip_deepseek_thinking(content)


def import_to_dify(name, text, args):
    if args.no_dify_import or not args.dify_api_key or not args.dify_dataset_id:
        return None
    url = (
        f"{args.dify_api_url.rstrip('/')}/datasets/"
        f"{args.dify_dataset_id}/document/create-by-text"
    )
    payload = json.dumps(
        {
            "name": name,
            "text": text,
            "indexing_technique": args.dify_indexing_technique,
            "doc_form": "text_model",
            "doc_language": "Chinese",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {args.dify_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=args.dify_timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"导入 Dify 失败：HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"导入 Dify 失败：{exc}") from exc
    return json.loads(body)


def import_to_paperless(paths, consume_dir, prefix):
    if not consume_dir:
        return []
    consume_dir = ensure_dir(Path(consume_dir).expanduser().resolve())
    imported = []
    for path in paths:
        target = consume_dir / f"{prefix}_{path.name}"
        shutil.copy2(path, target)
        imported.append(target)
    return imported


def run_asr(audio_path, work_dir, args):
    wav_file, source_md5, wav_md5 = Ifasr.prepare_wav(audio_path, work_dir)
    client = Ifasr.XfyunAsrClient(
        args.xfyun_appid,
        args.xfyun_api_key,
        args.xfyun_api_secret,
        insecure=args.insecure,
    )
    api_response = client.transcribe(
        wav_file,
        poll_interval=args.poll_interval,
        max_attempts=args.max_attempts,
    )
    txt_path, json_path, docx_path = Ifasr.build_outputs(
        api_response,
        wav_file,
        source_md5,
        wav_md5,
        work_dir,
    )
    return txt_path, json_path, docx_path, wav_file


def process_audio(audio_path, args):
    source = Path(audio_path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"音频文件不存在：{source}")
    if source.suffix.lower() not in AUDIO_SUFFIXES:
        raise ValueError(f"不支持的音频格式：{source.suffix}")

    ymd = today_ymd()
    job_name = stable_job_name(source)
    archive_dir = ensure_dir(args.archive_root / ymd)
    output_dir = ensure_dir(args.output_root / ymd / job_name)
    work_dir = ensure_dir(output_dir / "_asr")
    write_status(output_dir, "processing", source_file=str(source))

    try:
        archived_source = archive_dir / f"{job_name}{source.suffix.lower()}"
        if source != archived_source:
            shutil.move(str(source), archived_source)
        else:
            archived_source = source

        write_status(output_dir, "transcribing", source_file=str(archived_source))
        txt_path, json_path, docx_path, wav_file = run_asr(archived_source, work_dir, args)
        transcript_with_time, transcript_plain, payload = read_transcript(json_path)

        final_docx = output_dir / "语音记录.docx"
        final_txt = output_dir / "语音记录.txt"
        final_json = output_dir / "语音记录.json"
        shutil.copy2(docx_path, final_docx)
        shutil.copy2(txt_path, final_txt)
        shutil.copy2(json_path, final_json)

        write_status(output_dir, "summarizing", source_file=str(archived_source))
        minutes = generate_minutes_with_llm(
            transcript_with_time,
            model=args.llm_model,
            llm_url=args.llm_url,
            timeout=args.llm_timeout,
            api_key=args.llm_api_key,
        )
        minutes_path = output_dir / "语音记录.会议纪要.md"
        minutes_path.write_text(minutes + "\n", encoding="utf-8")

        write_status(output_dir, "indexing_dify", source_file=str(archived_source))
        dify_result = None
        dify_error = None
        try:
            dify_result = import_to_dify(f"{job_name}_语音记录.会议纪要.md", minutes, args)
        except Exception as exc:
            if args.dify_fail_hard:
                raise
            dify_error = str(exc)
            write_json_file(
                output_dir / "dify_error.json",
                {
                    "error": dify_error,
                    "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
                },
            )

        metadata = {
            "job_name": job_name,
            "date": ymd,
            "status": "completed",
            "created_at": dt.datetime.now().isoformat(timespec="seconds"),
            "source_file": str(archived_source),
            "wav_file": str(wav_file),
            "transcript_docx": str(final_docx),
            "transcript_txt": str(final_txt),
            "transcript_json": str(final_json),
            "minutes_md": str(minutes_path),
            "model": args.llm_model,
            "segment_count": len(payload.get("segments", [])),
            "transcript_chars": len(transcript_plain),
        }
        if dify_result:
            metadata["dify_import"] = dify_result
        if dify_error:
            metadata["dify_error"] = dify_error
        metadata_path = output_dir / "metadata.json"
        write_json_file(metadata_path, metadata)

        write_status(output_dir, "importing", source_file=str(archived_source))
        paperless_files = import_to_paperless(
            [final_docx, minutes_path],
            args.paperless_consume_dir,
            prefix=job_name,
        )
        if paperless_files:
            metadata["paperless_imported"] = [str(path) for path in paperless_files]
            write_json_file(metadata_path, metadata)

        write_status(output_dir, "completed", metadata_file=str(metadata_path))
        return metadata
    except Exception as exc:
        write_error(output_dir, exc)
        raise


def watch(args):
    inbox = ensure_dir(args.inbox_root)
    print(f"递归监听目录：{inbox}")
    seen = set()
    while True:
        for path in sorted(inbox.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in AUDIO_SUFFIXES:
                continue
            if path in seen:
                continue
            try:
                print(f"开始处理：{path}")
                metadata = process_audio(path, args)
                print(json.dumps(metadata, ensure_ascii=False, indent=2))
            except Exception as exc:
                print(f"处理失败：{path}: {exc}", file=sys.stderr)
                seen.add(path)
        time.sleep(args.interval)


def parse_args():
    parser = argparse.ArgumentParser(description="本地知识库语音记录流水线。")
    parser.add_argument("audio", nargs="?", help="单次处理的音频文件；不传则配合 --watch 监听目录")
    parser.add_argument("--watch", action="store_true", help="递归监听 data/src/media 目录")
    parser.add_argument("--inbox-root", default=str(WORK_ROOT / "data" / "src" / "media"), type=Path)
    parser.add_argument("--archive-root", default=str(WORK_ROOT / "data" / "archive"), type=Path)
    parser.add_argument("--output-root", default=str(WORK_ROOT / "data" / "dst"), type=Path)
    parser.add_argument("--paperless-consume-dir", default=str(WORK_ROOT / "paperless-ngx" / "consume"))
    parser.add_argument(
        "--llm-url",
        "--ollama-url",
        dest="llm_url",
        default=os.getenv("LLM_URL") or os.getenv("OLLAMA_URL") or "http://127.0.0.1:9082/v1",
        help="OpenAI 兼容本地模型接口；--ollama-url 为兼容旧脚本的别名",
    )
    parser.add_argument(
        "--llm-model",
        "--ollama-model",
        dest="llm_model",
        default=(
            os.getenv("LLM_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or "mlx-community/DeepSeek-R1-Distill-Llama-70B-4bit"
        ),
        help="本地模型名称；--ollama-model 为兼容旧脚本的别名",
    )
    parser.add_argument("--llm-api-key", default=os.getenv("LLM_API_KEY", "ignored"))
    parser.add_argument("--llm-timeout", "--ollama-timeout", dest="llm_timeout", default=1800, type=int)
    parser.add_argument("--dify-api-url", default=os.getenv("DIFY_API_URL", "http://127.0.0.1/v1"))
    parser.add_argument("--dify-api-key", default=os.getenv("DIFY_API_KEY", ""))
    parser.add_argument("--dify-dataset-id", default=os.getenv("DIFY_DATASET_ID", ""))
    parser.add_argument("--dify-indexing-technique", default=os.getenv("DIFY_INDEXING_TECHNIQUE", "high_quality"))
    parser.add_argument("--dify-timeout", default=120, type=int)
    parser.add_argument("--no-dify-import", action="store_true")
    parser.add_argument("--dify-fail-hard", action="store_true")
    parser.add_argument("--interval", default=5, type=int, help="监听轮询间隔秒数")
    parser.add_argument("--xfyun-appid", default=os.getenv("XFYUN_APPID") or Ifasr.APPID)
    parser.add_argument("--xfyun-api-key", default=os.getenv("XFYUN_API_KEY") or Ifasr.API_KEY)
    parser.add_argument("--xfyun-api-secret", default=os.getenv("XFYUN_API_SECRET") or Ifasr.API_SECRET)
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--max-attempts", type=int, default=720)
    parser.add_argument("--insecure", action="store_true")
    args = parser.parse_args()

    args.inbox_root = args.inbox_root.expanduser().resolve()
    args.archive_root = args.archive_root.expanduser().resolve()
    args.output_root = args.output_root.expanduser().resolve()
    return args


def main():
    args = parse_args()
    if args.watch:
        watch(args)
        return
    if not args.audio:
        raise SystemExit("请传入音频文件，或使用 --watch 监听目录。")
    metadata = process_audio(args.audio, args)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

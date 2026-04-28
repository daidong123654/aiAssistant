#!/usr/bin/env python3
"""Transcribe video/audio with Fun-ASR-Nano-2512 and mandatory Apple MPS."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "FunAudioLLM/Fun-ASR-Nano-2512"
DEFAULT_VAD_MODEL = "fsmn-vad"
DEFAULT_LANGUAGE = "中文"
MODEL_ROOT = Path("models")
REMOTE_CODE = Path(__file__).resolve().parents[1] / "third_party" / "Fun-ASR" / "model.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Use FunASR Nano 2512 to turn local video/audio into text and subtitles. "
            "This script requires PyTorch MPS and will not fall back to CPU."
        )
    )
    parser.add_argument("input", type=Path, help="Video or audio file to process.")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for txt/json/srt outputs. Default: outputs",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Hugging Face model id or local model path. Default: FunAudioLLM/Fun-ASR-Nano-2512",
    )
    parser.add_argument(
        "--hf-endpoint",
        default=os.environ.get("HF_ENDPOINT"),
        help="Optional Hugging Face endpoint/mirror, e.g. https://hf-mirror.com.",
    )
    parser.add_argument(
        "--vad-model",
        default=DEFAULT_VAD_MODEL,
        help="VAD model id/local path. Use 'none' to disable. Default: fsmn-vad",
    )
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help="Recognition language for Nano 2512, e.g. 中文, 英文, 日文, 韩文, 粤语. Default: 中文",
    )
    parser.add_argument(
        "--batch-size-s",
        type=int,
        default=0,
        help=(
            "FunASR VAD batching window in seconds. Default: 0, which forces one VAD "
            "segment at a time because Fun-ASR-Nano-2512 does not implement batch decoding."
        ),
    )
    parser.add_argument(
        "--keep-wav",
        action="store_true",
        help="Keep the extracted 16 kHz mono wav next to outputs.",
    )
    return parser.parse_args()


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg was not found. Install it first, for example: brew install ffmpeg")


def require_mps() -> None:
    try:
        import torch
    except Exception as exc:
        raise RuntimeError("PyTorch is required before MPS can be used.") from exc

    if not torch.backends.mps.is_available():
        raise RuntimeError(
            "PyTorch MPS is not available. This script is MPS-only and will not fall back to CPU."
        )


def require_nano_dependencies() -> None:
    missing = [
        package
        for package in ("transformers", "safetensors", "whisper", "tiktoken")
        if importlib.util.find_spec(package) is None
    ]
    if missing:
        raise RuntimeError(
            "Fun-ASR-Nano-2512 requires missing package(s): "
            f"{', '.join(missing)}. Install them with: pip install {' '.join(missing)}"
        )


def register_nano_remote_code(remote_code: Path = REMOTE_CODE) -> str:
    if not remote_code.exists():
        raise RuntimeError(
            f"Fun-ASR-Nano remote code was not found: {remote_code}. "
            "Run: git clone --depth 1 https://github.com/FunAudioLLM/Fun-ASR.git /tmp/Fun-ASR"
        )

    code_dir = str(remote_code.parent)
    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)

    from funasr.utils.dynamic_import import import_module_from_path

    import_module_from_path(str(remote_code))
    return str(remote_code)


def extract_audio(input_path: Path, wav_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def normalize_model(value: str) -> str | None:
    return None if value.lower() in {"", "none", "null", "false"} else value


def prefer_local_model(value: str | None, model_root: Path = MODEL_ROOT) -> str | None:
    if value is None:
        return None

    configured_path = Path(value).expanduser()
    if configured_path.exists():
        return str(configured_path.resolve())

    local_snapshot = model_root / value
    if local_snapshot.exists():
        return str(local_snapshot.resolve())

    return value


def collect_text(result: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for item in result:
        text = item.get("text")
        if text:
            chunks.append(str(text).strip())
    return "\n".join(chunks).strip()


def ms_to_srt_time(ms: int | float) -> str:
    total_ms = int(ms)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def extract_sentences(result: list[dict[str, Any]]) -> list[tuple[int, int, str]]:
    sentences: list[tuple[int, int, str]] = []
    for item in result:
        sentence_info = item.get("sentence_info") or []
        for sentence in sentence_info:
            text = str(sentence.get("text", "")).strip()
            if not text:
                continue
            start = int(sentence.get("start", 0))
            end = int(sentence.get("end", start + 1))
            sentences.append((start, end, text))
    return sentences


def write_outputs(base: Path, result: list[dict[str, Any]]) -> None:
    text = collect_text(result)
    base.with_suffix(".txt").write_text(text + ("\n" if text else ""), encoding="utf-8")
    base.with_suffix(".json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    sentences = extract_sentences(result)
    if not sentences and text:
        sentences = [(0, 1_000, text)]

    srt_lines: list[str] = []
    for index, (start, end, sentence) in enumerate(sentences, start=1):
        srt_lines.extend(
            [
                str(index),
                f"{ms_to_srt_time(start)} --> {ms_to_srt_time(end)}",
                sentence,
                "",
            ]
        )
    base.with_suffix(".srt").write_text("\n".join(srt_lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.hf_endpoint:
        os.environ["HF_ENDPOINT"] = args.hf_endpoint

    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        require_ffmpeg()
        require_mps()
        require_nano_dependencies()
        remote_code = register_nano_remote_code()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_base = args.output_dir / f"{input_path.stem}.nano2512"

    with tempfile.TemporaryDirectory(prefix="funasr_nano2512_") as temp_dir:
        temp_wav = Path(temp_dir) / f"{input_path.stem}.16k.wav"
        print(f"[1/3] Extracting 16 kHz mono audio: {input_path}")
        extract_audio(input_path, temp_wav)

        if args.keep_wav:
            kept_wav = output_base.with_suffix(".16k.wav")
            shutil.copy2(temp_wav, kept_wav)
            wav_for_asr = kept_wav
        else:
            wav_for_asr = temp_wav

        print("[2/3] Loading Fun-ASR-Nano-2512 on mps. First run may download model files.")
        from funasr import AutoModel

        asr_model = prefer_local_model(args.model)
        vad_model = prefer_local_model(normalize_model(args.vad_model))

        model_kwargs: dict[str, Any] = {
            "model": asr_model,
            "hub": "hf",
            "device": "mps",
            "disable_update": True,
            "trust_remote_code": True,
            "remote_code": remote_code,
        }
        if vad_model:
            model_kwargs["vad_model"] = vad_model

        model = AutoModel(**model_kwargs)

        print(f"[3/3] Recognizing with language={args.language!r} on mps...")
        result = model.generate(
            input=str(wav_for_asr),
            language=args.language,
            batch_size=1,
            batch_size_s=args.batch_size_s,
        )
        write_outputs(output_base, result)

    print(f"TXT : {output_base.with_suffix('.txt')}")
    print(f"JSON: {output_base.with_suffix('.json')}")
    print(f"SRT : {output_base.with_suffix('.srt')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

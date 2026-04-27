#!/usr/bin/env python3
"""Transcribe a local video/audio file with a local FunASR model."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
DEFAULT_VAD_MODEL = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
DEFAULT_PUNC_MODEL = "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use Alibaba Tongyi FunASR local models to transcribe video/audio."
    )
    parser.add_argument("input", type=Path, help="Video or audio file to transcribe.")
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
        help="ModelScope id or local model path for ASR model.",
    )
    parser.add_argument(
        "--vad-model",
        default=DEFAULT_VAD_MODEL,
        help="ModelScope id or local path for VAD model. Use 'none' to disable.",
    )
    parser.add_argument(
        "--punc-model",
        default=DEFAULT_PUNC_MODEL,
        help="ModelScope id or local path for punctuation model. Use 'none' to disable.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Inference device, e.g. cpu, mps, cuda:0, or auto. CPU is safest on macOS.",
    )
    parser.add_argument(
        "--batch-size-s",
        type=int,
        default=300,
        help="FunASR batch size in seconds. Lower it if memory is tight.",
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


def prefer_local_model(value: str | None, model_root: Path = Path("models")) -> str | None:
    if value is None:
        return None
    configured_path = Path(value).expanduser()
    if configured_path.exists():
        return str(configured_path.resolve())

    local_snapshot = model_root / value
    if local_snapshot.exists():
        return str(local_snapshot.resolve())
    return value


def resolve_device(requested: str) -> str:
    requested = requested.strip().lower()
    if requested == "auto":
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda:0"
            if torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        return "cpu"

    if requested == "mps":
        try:
            import torch

            if torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        print("Warning: PyTorch MPS is not available in this environment; falling back to CPU.")
        return "cpu"

    return requested


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
    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    require_ffmpeg()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_base = args.output_dir / input_path.stem

    with tempfile.TemporaryDirectory(prefix="funasr_") as temp_dir:
        temp_wav = Path(temp_dir) / f"{input_path.stem}.16k.wav"
        print(f"[1/3] Extracting 16 kHz mono audio: {input_path}")
        extract_audio(input_path, temp_wav)

        if args.keep_wav:
            kept_wav = output_base.with_suffix(".16k.wav")
            shutil.copy2(temp_wav, kept_wav)
            wav_for_asr = kept_wav
        else:
            wav_for_asr = temp_wav

        print("[2/3] Loading FunASR model. First run may download model files.")
        from funasr import AutoModel

        asr_model = prefer_local_model(args.model)
        vad_model = prefer_local_model(normalize_model(args.vad_model))
        punc_model = prefer_local_model(normalize_model(args.punc_model))
        device = resolve_device(args.device)

        model_kwargs: dict[str, Any] = {
            "model": asr_model,
            "device": device,
            "disable_update": True,
        }
        if vad_model:
            model_kwargs["vad_model"] = vad_model
            model_kwargs["vad_kwargs"] = {"max_single_segment_time": 30_000}
        if punc_model:
            model_kwargs["punc_model"] = punc_model

        model = AutoModel(**model_kwargs)

        print("[3/3] Transcribing...")
        result = model.generate(input=str(wav_for_asr), batch_size_s=args.batch_size_s)
        write_outputs(output_base, result)

    print(f"TXT : {output_base.with_suffix('.txt')}")
    print(f"JSON: {output_base.with_suffix('.json')}")
    print(f"SRT : {output_base.with_suffix('.srt')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

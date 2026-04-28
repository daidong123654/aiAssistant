#!/usr/bin/env python3
"""Download FunASR ModelScope models to a local directory."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path

from modelscope import snapshot_download


DEFAULT_MODELS = [
    "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
]
NANO_2512_MODEL = "FunAudioLLM/Fun-ASR-Nano-2512"


def download_modelscope_model(model_id: str, model_dir: Path) -> None:
    print(f"Downloading {model_id} from ModelScope ...")
    path = snapshot_download(model_id, cache_dir=str(model_dir))
    print(f"Saved: {path}")


def download_hf_model(model_id: str, model_dir: Path, max_workers: int) -> None:
    from huggingface_hub import snapshot_download as hf_snapshot_download

    local_dir = model_dir / model_id
    print(f"Downloading {model_id} from Hugging Face ...")
    path = hf_snapshot_download(
        repo_id=model_id,
        local_dir=str(local_dir),
        max_workers=max_workers,
    )
    print(f"Saved: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-download FunASR models from ModelScope.")
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models"),
        help="Where to store downloaded model snapshots. Default: models",
    )
    parser.add_argument(
        "models",
        nargs="*",
        default=DEFAULT_MODELS,
        help="ModelScope model ids to download.",
    )
    parser.add_argument(
        "--with-nano-2512",
        action="store_true",
        help="Also download FunAudioLLM/Fun-ASR-Nano-2512.",
    )
    parser.add_argument(
        "--only-nano-2512",
        action="store_true",
        help="Download only FunAudioLLM/Fun-ASR-Nano-2512.",
    )
    parser.add_argument(
        "--hf-endpoint",
        default=os.environ.get("HF_ENDPOINT"),
        help="Optional Hugging Face endpoint/mirror for Nano 2512, e.g. https://hf-mirror.com.",
    )
    parser.add_argument(
        "--hf-transfer",
        action="store_true",
        help="Use hf_transfer for faster Hugging Face downloads. Requires: pip install hf_transfer",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=16,
        help="Parallel file download workers for Hugging Face snapshots. Default: 16",
    )
    args = parser.parse_args()

    if args.hf_endpoint:
        os.environ["HF_ENDPOINT"] = args.hf_endpoint
    if args.hf_transfer:
        if importlib.util.find_spec("hf_transfer") is None:
            raise SystemExit(
                "Error: --hf-transfer requires hf_transfer. Install it with: "
                ".venv/bin/pip install hf_transfer"
            )
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

    args.model_dir.mkdir(parents=True, exist_ok=True)
    if not args.only_nano_2512:
        for model_id in args.models:
            download_modelscope_model(model_id, args.model_dir)

    if args.with_nano_2512 or args.only_nano_2512:
        download_hf_model(NANO_2512_MODEL, args.model_dir, args.max_workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

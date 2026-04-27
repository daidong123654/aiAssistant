#!/usr/bin/env python3
"""Download FunASR ModelScope models to a local directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from modelscope import snapshot_download


DEFAULT_MODELS = [
    "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
]


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
    args = parser.parse_args()

    args.model_dir.mkdir(parents=True, exist_ok=True)
    for model_id in args.models:
        print(f"Downloading {model_id} ...")
        path = snapshot_download(model_id, cache_dir=str(args.model_dir))
        print(f"Saved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

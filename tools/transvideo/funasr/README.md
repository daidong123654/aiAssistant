# FunASR local video transcription

This project uses Alibaba Tongyi FunASR local models to transcribe local video or audio files.

## Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

`ffmpeg` is required for extracting audio from videos:

```bash
brew install ffmpeg
```

## Optional: pre-download models

```bash
source .venv/bin/activate
python scripts/download_models.py
```

When these directories exist under `models/`, `scripts/transcribe_video.py` automatically prefers them over remote model ids.

To also download the Nano 2512 model used by the MPS script:

```bash
python scripts/download_models.py --with-nano-2512
```

If Hugging Face downloads are slow, use a mirror endpoint:

```bash
pip install hf_transfer
python scripts/download_models.py --only-nano-2512 --hf-endpoint https://hf-mirror.com --hf-transfer --max-workers 32
```

The default models are:

- ASR: `iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`
- VAD: `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch`
- Punctuation: `iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch`

You can also pass a local model path to `--model`, `--vad-model`, or `--punc-model`.

## Transcribe a video

```bash
source .venv/bin/activate
python scripts/transcribe_video.py /path/to/video.mp4
```

Outputs are written to `outputs/<video-name>.txt`, `outputs/<video-name>.json`, and `outputs/<video-name>.srt`.

Useful options:

```bash
python scripts/transcribe_video.py /path/to/video.mp4 --device cpu --keep-wav
python scripts/transcribe_video.py /path/to/video.mp4 --model /path/to/local/asr_model
python scripts/transcribe_video.py /path/to/video.mp4 --punc-model none
```

On macOS, `--device cpu` is the safest default. You can try `--device mps`, but the script will fall back to CPU when PyTorch reports that MPS is unavailable. If you use a CUDA machine, try `--device cuda:0`.

## Recognize with Fun-ASR-Nano-2512 on MPS

For the strongest Nano 2512 model with mandatory Apple MPS acceleration:

```bash
source .venv/bin/activate
python scripts/translate_nano_mps.py /path/to/video.mp4
```

This script defaults to `FunAudioLLM/Fun-ASR-Nano-2512`, uses `device="mps"`, and exits instead of falling back to CPU when MPS is unavailable.
The Nano model implementation is loaded from `third_party/Fun-ASR/model.py`, copied from the official FunAudioLLM/Fun-ASR repository, because the Hugging Face model snapshot does not include that runtime file.
Keep `--batch-size-s` at its default `0` for this model; the official Nano runtime does not implement batch decoding.

Useful options:

```bash
python scripts/translate_nano_mps.py /path/to/video.mp4 --language 中文
python scripts/translate_nano_mps.py /path/to/video.mp4 --language 英文 --keep-wav
python scripts/translate_nano_mps.py /path/to/video.mp4 --vad-model none
python scripts/translate_nano_mps.py /path/to/video.mp4 --hf-endpoint https://hf-mirror.com
```

Outputs are written to `outputs/<video-name>.nano2512.txt`, `.json`, and `.srt`.

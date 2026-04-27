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


1. 10s cost 20s
whisper 1.wav --model large-v3 --language Chinese --output_format srt --fp16 False

2. 10s cost 1s
whisper-cli -m ~/.cache/whisper/ggml-large-v3-turbo.bin -f 1.wav -l zh -osrt

解决重复问题
whisper-cli \
  -m ~/.cache/whisper/ggml-large-v3.bin \
  -f 48.wav \
  -l zh \
  -osrt \
  --max-context 0 \
  --max-len 150 \
  --temperature 0 \
  --beam-size 5 \
  
--no-timestamps

关键解释（很重要）
--max-context 0
👉 等价于老版本的 no-context（核心！）
--no-timestamps
👉 避免时间戳漂移导致重复拼接
--max-len 150
👉 强行打断“复读循环


3. Qwen3-ASR
cd ~/Work/tools/transvideo
python3 qwen3asr.py
curl -X POST http://localhost:7777/transcribe -F "file=@/path/to/your/audio.wav"



转格式
ffmpeg -i 48.m4a -ar 16000 -ac 1 -c:a pcm_s16le 48.wav

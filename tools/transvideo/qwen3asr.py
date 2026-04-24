import os
# 在所有 import transformers 之前设置环境变量
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# 强制使用本地缓存，避免重复下载
os.environ["TRANSFORMERS_OFFLINE"] = "0"
import time
import librosa
import torch
# 关键：修改导入的类
from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration
from flask import Flask, request, jsonify

import mlx.core as mx
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
from flask import Flask, request, jsonify

app = Flask(__name__)

# 配置区
MODEL_ID = "Qwen/Qwen2-Audio-7B-Instruct" # 暂时使用Qwen2-Audio架构兼容版，0.6B细节可替换路径
DEVICE = "cpu" # 目前transformers官方库主要运行在cpu/torch，MLX原生适配需后续转换

print("正在加载 Qwen-ASR 模型到内存...")
# 你的 128G 内存足以支持全精度加载
processor = AutoProcessor.from_pretrained(MODEL_ID)
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    MODEL_ID, 
    torch_dtype=torch.float16, 
    low_cpu_mem_usage=True
).to(DEVICE)

@app.route('/transcribe', methods=['POST'])
def transcribe_api():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    temp_path = f"temp_{int(time.time())}.wav"
    file.save(temp_path)

    try:
        # 加载并重采样音频
        audio, _ = librosa.load(temp_path, sr=16000)
        
        # 预处理
        inputs = processor(audios=audio, return_tensors="pt").to(DEVICE)
        
        # 推理
        start_time = time.time()
        generated_ids = model.generate(**inputs, max_new_tokens=256)
        result = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        duration = time.time() - start_time
        return jsonify({
            "text": result,
            "time_cost": f"{duration:.2f}s",
            "model": MODEL_ID
        })
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == '__main__':
    # 既然你在本地用，绑定到 0.0.0.0 方便 Docker 调用
    app.run(host='0.0.0.0', port=7777)


import os
# 在代码最开头添加这两行，使用国内镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'


from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import torch
import librosa
import soundfile as sf
import os

# 加载模型（0.6B 版本，你的 128GB 内存绰绰有余）
model = AutoModelForSpeechSeq2Seq.from_pretrained("Qwen/Qwen3-ASR-0.6B")
processor = AutoProcessor.from_pretrained("Qwen/Qwen3-ASR-0.6B")

# 如果有 GPU/MLX 可用，自动加速
device = "mps" if torch.backends.mps.is_available() else "cpu"
model = model.to(device)

def transcribe(audio_path):
    """
    语音转文字
    参数:
        audio_path: 语音文件路径（支持 wav, mp3, m4a, flac 等格式）
    返回:
        识别出的文字
    """
    # 1. 检查文件是否存在
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"文件不存在: {audio_path}")
    
    # 2. 加载音频并自动重采样到 16kHz（Qwen3-ASR 要求）
    audio_array, original_sr = librosa.load(audio_path, sr=16000)
    
    # 3. 处理音频
    inputs = processor(audio_array, sampling_rate=16000, return_tensors="pt").to(device)
    
    # 4. 推理
    with torch.no_grad():
        outputs = model.generate(**inputs)
    
    # 5. 解码返回文字
    text = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    return text


def transcribe_batch(audio_folder, extensions=('.wav', '.mp3', '.m4a', '.flac')):
    """
    批量处理文件夹中的音频文件
    参数:
        audio_folder: 文件夹路径
        extensions: 支持的音频格式
    返回:
        dict: {文件名: 识别文字}
    """
    results = {}
    for file in os.listdir(audio_folder):
        if file.lower().endswith(extensions):
            file_path = os.path.join(audio_folder, file)
            try:
                text = transcribe(file_path)
                results[file] = text
                print(f"✅ {file}: {text[:50]}...")
            except Exception as e:
                results[file] = f"错误: {e}"
                print(f"❌ {file}: {e}")
    return results


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 单个文件
    text = transcribe("/Users/jianfeisu/Work/tools/videos/1.wav")
    print(text)
    
    # 批量处理文件夹
    results = transcribe_batch("/Users/jianfeisu/Work/tools/videos/")
    for filename, text in results.items():
        print(f"{filename}: {text}")

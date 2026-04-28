# 本地 AI 助理系统

这是一个用于在 macOS Apple Silicon 机器上搭建本地 AI 助理环境的项目集合。项目把本地大模型、语音转写、文档管理和自动化工作流相关工具放在一起，方便在一台 Mac 上部署和维护一套个人或小团队可用的 AI 工作台。

## 项目内容

本仓库主要包含以下几类内容：

- 一键部署脚本：安装和启动 Homebrew、Docker、n8n、Dify、Paperless-ngx、Open WebUI 等组件。
- 文档管理服务：基于 Paperless-ngx 的本地文档归档、OCR 和检索配置。
- 语音和视频转写工具：包含 Whisper、whisper.cpp、FunASR、Qwen3-ASR 等相关脚本和实验文件。
- 本地知识库语音助手：通过 OpenClaw、n8n、讯飞转写、MLX 本地模型和 Paperless-ngx，把微信语音整理为语音记录和会议纪要。
- 本地模型资源：存放 Whisper、MLX、Hugging Face 等模型文件或缓存。
- 常用环境脚本：Homebrew、Oh My Zsh、Paperless 等本机工具安装脚本。

## 目录结构

```text
.
├── depoly.sh              # 本地 AI 助理系统一键部署脚本
├── paperless-ngx/         # Paperless-ngx Docker Compose 配置
├── models/                # 本地模型文件与模型缓存
│   ├── whisper/           # Whisper / whisper.cpp 模型
│   ├── mlx/               # MLX 相关模型与配置
│   └── huggingface/       # Hugging Face 本地缓存
└── tools/                 # 工具脚本与实验项目
    ├── paperless-ngx/     # Paperless-ngx 辅助配置
    ├── kb_assistant/      # 微信语音到本地知识库的自动化流水线
    ├── transvideo/        # 音视频转写相关工具
    ├── videos/            # 转写测试用音视频文件与结果
    └── ollama/            # 历史遗留目录，当前本地模型服务不再依赖 Ollama
```

## 核心能力

### 本地 AI 服务

- MLX 本地模型服务：通过 `models/mlx/sup*.ini` 由 supervisor 管理，并以 OpenAI 兼容接口暴露。
- Open WebUI：统一的本地模型聊天界面，可连接 MLX 本地模型接口。
- Dify：AI 应用编排和工作流平台。
- n8n：自动化工作流引擎。

### 文档处理

- Paperless-ngx：文档上传、OCR、归档和全文检索。
- 默认 Docker Compose 配置包含 PostgreSQL、Redis 和 Paperless-ngx Web 服务。
- 默认 OCR 语言配置包含简体中文。

### 音视频转写

- Whisper Python 版本转写。
- whisper.cpp 命令行转写。
- Qwen3-ASR 本地服务接口。
- FunASR 相关脚本和第三方运行时。
- 讯飞转写脚本：`tools/transvideo/xfyunllm`，可生成带时间轴的 txt/json/docx。

### 本地知识库助手

- OpenClaw 接收微信语音消息。
- n8n 负责消息编排、文件保存和结果通知。
- `tools/kb_assistant/voice_record_pipeline.py` 监听 `data/src/YYYYMMDD/` 并处理音频。
- 讯飞转写生成 `语音记录.docx`。
- 本地 MLX 模型生成 `语音记录.会议纪要.md`。
- Paperless-ngx 自动消费生成文件，形成可检索的本地知识库。

## 环境要求

- macOS，推荐 Apple Silicon 机型。
- Xcode Command Line Tools。
- Docker Desktop。
- Homebrew。
- Python 3。
- ffmpeg。
- 可访问 Docker Hub、GitHub 和模型下载源的网络环境。

部分组件会占用较大的磁盘空间，尤其是 `models/`、`tools/videos/` 和第三方源码目录。建议在运行前确认磁盘空间充足。

## 快速开始

### 1. 克隆或进入项目目录

```bash
cd ~/Work
```

### 2. 执行一键部署

```bash
bash depoly.sh
```

该脚本会依次检查网络、安装基础工具、启动 Docker 服务，检查 `models/mlx/sup*.ini` 本地模型配置，并启动 n8n、Dify、Paperless-ngx 和 Open WebUI。

### 3. 访问服务

部署完成后，常用服务地址如下：

| 服务 | 地址 | 用途 |
| --- | --- | --- |
| n8n | http://localhost:5678 | 自动化工作流 |
| Dify | http://localhost | AI 应用编排 |
| Paperless-ngx | http://localhost:8000 | 文档管理与 OCR |
| Open WebUI | http://localhost:3000 | 本地模型聊天界面 |
| MLX 1.5B API | http://localhost:9080/v1 | 本地小模型 API |
| MLX 27B API | http://localhost:9081/v1 | 本地中型模型 API |
| MLX 70B API | http://localhost:9082/v1 | 本地大模型 API |

## 本地模型管理

Ollama 已废弃，当前本地模型统一使用 MLX 运行，配置文件位于：

```text
models/mlx/sup1.5b.ini
models/mlx/sup27b.ini
models/mlx/sup70b.ini
```

这些 `sup*.ini` 是 supervisor program 配置。当前以配置文件内容为准，`sup27b.ini` 和 `sup70b.ini` 的文件名与实际 program 有历史遗留差异：

| 配置文件 | 模型 | 端口 | 用途建议 |
| --- | --- | --- | --- |
| `models/mlx/sup1.5b.ini` | `mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit` | 9080 | 高频分类、轻量摘要 |
| `models/mlx/sup70b.ini` | `mlx-community/gemma-2-27b-it-4bit` | 9081 | 日常问答、较复杂摘要 |
| `models/mlx/sup27b.ini` | `mlx-community/DeepSeek-R1-Distill-Llama-70B-4bit` | 9082 | 会议纪要、深度分析 |

### 启动方式

推荐使用 supervisor 管理后台服务：

```bash
supervisorctl status
supervisorctl reread
supervisorctl update
supervisorctl start mlx-1.5b
supervisorctl start mlx-27b
supervisorctl start mlx-70b
supervisorctl stop mlx-1.5b
supervisorctl stop mlx-27b
supervisorctl stop mlx-70b
```

如果只想前台临时启动，也可以使用 `models/mlx/m.sh`：

```bash
cd ~/Work/models/mlx
./m.sh 1.5b
./m.sh 27b
./m.sh 70b
```

`m.sh` 和 `sup*.ini` 都使用 `/Users/jianfeisu/mlx_env/bin/python -m mlx_lm.server` 启动服务，并设置模型缓存目录：

```bash
export HF_HOME="/Users/jianfeisu/Work/models/huggingface"
export HF_ENDPOINT="https://hf-mirror.com"
export HF_HUB_ENABLE_HF_TRANSFER="1"
```

MLX 模型文件和缓存默认放在 `models/huggingface/`。替换模型时优先修改对应的 `models/mlx/sup*.ini`，再执行 `supervisorctl reread && supervisorctl update`。

### 本地模型测试用例

服务启动后可以使用 OpenAI 兼容接口测试。最简单的问题统一问“地球到太阳的距离是多少？”。

测试 1.5B 模型：

```bash
curl http://127.0.0.1:9080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "stream": false,
    "model": "mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit",
    "messages": [
      {"role": "user", "content": "地球到太阳的距离是多少？"}
    ],
    "temperature": 0.7
  }'
```

测试 27B 模型：

```bash
curl http://127.0.0.1:9081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "stream": false,
    "model": "mlx-community/gemma-2-27b-it-4bit",
    "messages": [
      {"role": "user", "content": "地球到太阳的距离是多少？"}
    ],
    "temperature": 0.7
  }'
```

测试 70B 模型：

```bash
curl http://127.0.0.1:9082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "stream": false,
    "model": "mlx-community/DeepSeek-R1-Distill-Llama-70B-4bit",
    "messages": [
      {"role": "user", "content": "地球到太阳的距离是多少？"}
    ],
    "temperature": 0.7
  }'
```

正常情况下，回答应包含“约 1.5 亿公里”或“1 个天文单位（AU）”之类的表述。

## Paperless-ngx

如果只需要启动 Paperless-ngx，可以进入对应目录单独运行：

```bash
cd paperless-ngx
docker compose pull
docker compose up -d
```

默认配置会创建以下服务：

- `broker`：Redis。
- `db`：PostgreSQL。
- `webserver`：Paperless-ngx Web 服务。

常用目录：

- `paperless-ngx/consume/`：待导入文档目录。
- `paperless-ngx/export/`：导出目录。
- Docker volumes：保存数据库、媒体文件和应用数据。

## 音视频转写

转写相关工具主要在 `tools/transvideo/` 和 `models/whisper/` 中。

### Whisper 示例

```bash
whisper 1.wav --model large-v3 --language Chinese --output_format srt --fp16 False
```

### whisper.cpp 示例

```bash
whisper-cli -m ~/.cache/whisper/ggml-large-v3-turbo.bin -f 1.wav -l zh -osrt
```

### Qwen3-ASR 示例

```bash
cd tools/transvideo
python3 qwen3asr.py
curl -X POST http://localhost:7777/transcribe -F "file=@/path/to/audio.wav"
```

### 音频格式转换

```bash
ffmpeg -i input.m4a -ar 16000 -ac 1 -c:a pcm_s16le output.wav
```

## 本地知识库语音助手

详细说明见：

- `tools/kb_assistant/README.md`
- `tools/kb_assistant/WORKFLOW_DESIGN.md`

监听当天微信语音输入目录：

```bash
python3 tools/kb_assistant/voice_record_pipeline.py --watch
```

默认目录约定：

- 输入目录：`data/src/YYYYMMDD/`
- 原始音频归档：`data/archive/YYYYMMDD/`
- 输出目录：`data/dst/YYYYMMDD/<任务名>/`
- Paperless-ngx 导入目录：`paperless-ngx/consume/`

每条语音会生成：

- `语音记录.docx`
- `语音记录.txt`
- `语音记录.json`
- `语音记录.会议纪要.md`
- `metadata.json`

## 常用维护命令

查看 Docker 服务状态：

```bash
docker ps
```

停止 Paperless-ngx：

```bash
cd paperless-ngx
docker compose down
```

更新 Paperless-ngx 镜像：

```bash
cd paperless-ngx
docker compose pull
docker compose up -d
```

查看 MLX 模型服务状态：

```bash
supervisorctl status
```

重载本地模型配置：

```bash
supervisorctl reread
supervisorctl update
```

## 注意事项

- `models/` 中可能包含大体积模型文件，不建议直接提交到远程 Git 仓库。
- `tools/videos/` 中可能包含测试音视频和转写结果，提交前请确认是否包含隐私内容。
- `paperless-ngx/docker-compose.env` 和 `.env` 类配置文件可能包含部署参数，生产环境中应避免泄露敏感信息。
- 首次部署会下载 Docker 镜像和模型文件，耗时取决于网络和磁盘速度。

## 建议工作流

1. 使用 `depoly.sh` 启动基础 AI 服务。
2. 在 Open WebUI 中连接 `http://host.docker.internal:9080/v1`、`9081/v1`、`9082/v1`，本地测试模型能力。
3. 在 Dify 中配置 OpenAI-API-compatible 模型供应商，指向 MLX 本地模型接口，搭建可复用 AI 应用。
4. 在 Paperless-ngx 中维护文档库，并按需接入 OCR 和自动归档流程。
5. 使用 n8n 串联文档、转写、模型调用和通知推送等自动化任务。

## 许可证

当前仓库未声明统一许可证。第三方项目、模型和工具请分别遵循其原始许可证和使用条款。

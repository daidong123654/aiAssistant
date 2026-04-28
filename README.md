# 本地 AI 助理系统

这是一个用于在 macOS Apple Silicon 机器上搭建本地 AI 助理环境的项目集合。项目把本地大模型、语音转写、文档管理和自动化工作流相关工具放在一起，方便在一台 Mac 上部署和维护一套个人或小团队可用的 AI 工作台。

## 项目内容

本仓库主要包含以下几类内容：

- 一键部署脚本：安装和启动 Homebrew、Docker、Ollama、n8n、Dify、Paperless-ngx、Open WebUI 等组件。
- 文档管理服务：基于 Paperless-ngx 的本地文档归档、OCR 和检索配置。
- 语音和视频转写工具：包含 Whisper、whisper.cpp、FunASR、Qwen3-ASR 等相关脚本和实验文件。
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
    ├── transvideo/        # 音视频转写相关工具
    ├── videos/            # 转写测试用音视频文件与结果
    └── ollama/            # Ollama 源码或本地构建目录
```

## 核心能力

### 本地 AI 服务

- Ollama：本地大模型运行服务。
- Open WebUI：统一的本地模型聊天界面。
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

该脚本会依次检查网络、安装基础工具、启动 Docker 服务、安装 Ollama、拉取推荐模型，并启动 n8n、Dify、Paperless-ngx 和 Open WebUI。

### 3. 访问服务

部署完成后，常用服务地址如下：

| 服务 | 地址 | 用途 |
| --- | --- | --- |
| n8n | http://localhost:5678 | 自动化工作流 |
| Dify | http://localhost | AI 应用编排 |
| Paperless-ngx | http://localhost:8000 | 文档管理与 OCR |
| Open WebUI | http://localhost:3000 | 本地模型聊天界面 |
| Ollama API | http://localhost:11434 | 本地模型 API |

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

查看 Ollama 模型：

```bash
ollama list
```

拉取新模型：

```bash
ollama pull <model-name>
```

## 注意事项

- `models/` 中可能包含大体积模型文件，不建议直接提交到远程 Git 仓库。
- `tools/videos/` 中可能包含测试音视频和转写结果，提交前请确认是否包含隐私内容。
- `paperless-ngx/docker-compose.env` 和 `.env` 类配置文件可能包含部署参数，生产环境中应避免泄露敏感信息。
- 首次部署会下载 Docker 镜像和模型文件，耗时取决于网络和磁盘速度。

## 建议工作流

1. 使用 `depoly.sh` 启动基础 AI 服务。
2. 在 Open WebUI 中连接 Ollama，本地测试模型能力。
3. 在 Dify 中配置 Ollama 作为模型供应商，搭建可复用 AI 应用。
4. 在 Paperless-ngx 中维护文档库，并按需接入 OCR 和自动归档流程。
5. 使用 n8n 串联文档、转写、模型调用和通知推送等自动化任务。

## 许可证

当前仓库未声明统一许可证。第三方项目、模型和工具请分别遵循其原始许可证和使用条款。

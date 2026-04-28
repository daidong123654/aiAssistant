# 本地 AI 工作台

本目录是 macOS Apple Silicon 上的本地 AI 工作台。它把本地大模型、微信语音处理、音视频转写、文档归档、自动化编排和测试素材放在同一个工作目录中，方便在一台机器上维护个人知识库和自动化助手。

当前主线能力是：

- 用 MLX 在本机暴露 OpenAI 兼容模型接口。
- 用 OpenClaw/n8n 接收微信语音或媒体文件。
- 用语音处理流水线生成转写、文档和结构化结果。
- 用 Paperless-ngx 自动归档并检索文档。
- 用自定义字段自动标记文档来源：音频、图片、文档。

## 目录总览

```text
~/Work
├── README.md                         # 本说明文档
├── depoly.sh                         # 一键部署/检查脚本，历史文件名保留为 depoly
├── codex/                            # Codex 本地配置和日志
├── data/                             # 本地流水线运行数据，默认不提交
│   ├── src/                          # 输入区，n8n/OpenClaw/手工导入放文件
│   ├── jobs/                         # 后台任务记录
│   ├── archive/                      # 原始文件归档
│   ├── dst/                          # 处理结果，也是 Paperless 当前消费目录
│   └── logs/                         # 本地任务日志
├── models/                           # 本地模型和缓存，默认不提交
│   ├── huggingface/                  # Hugging Face/MLX 模型缓存
│   ├── mlx/                          # MLX 启动脚本和 supervisor 配置
│   ├── whisper/                      # Whisper 模型
│   └── .ollama/                      # 历史 Ollama 数据，当前主线不依赖
├── paperless-ngx/                    # 旧 Paperless 配置目录，当前不作为主配置
├── tools/
│   ├── kb_assistant/                 # 微信语音到本地知识库流水线
│   ├── paperless-ngx/                # 当前正在运行的 Paperless-ngx 配置
│   ├── transvideo/                   # 音视频转写工具集合
│   ├── videos/                       # 转写测试素材和结果，默认不提交
│   └── ollama/                       # Ollama 源码/实验目录，当前主线不依赖
└── 需求.docx                         # 项目需求说明文档
```

## 当前服务

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| n8n | `http://localhost:5678` | 自动化工作流入口 |
| Dify | `http://localhost` | AI 应用编排，端口 80 |
| Paperless-ngx | `http://localhost:8000` | 文档归档、OCR、全文检索 |
| Open WebUI | `http://localhost:3000` | 本地模型聊天界面 |
| MLX 1.5B | `http://127.0.0.1:9080/v1` | 轻量模型接口 |
| MLX 27B | `http://127.0.0.1:9081/v1` | 中型模型接口 |
| MLX 70B | `http://127.0.0.1:9082/v1` | 大模型接口 |
| kb_assistant API | `http://127.0.0.1:8765` | n8n 提交语音任务用 API |

查看 Docker 服务：

```bash
docker ps
docker compose -f ~/Work/tools/paperless-ngx/docker-compose.yml ps
```

## 快速启动

进入目录：

```bash
cd ~/Work
```

一键部署/检查：

```bash
bash depoly.sh
```

这个脚本会检查 Homebrew、Docker、MLX 配置，并尝试启动 n8n、Dify、Paperless-ngx、Open WebUI。脚本里仍保留部分历史逻辑，实际 Paperless 主配置以 `tools/paperless-ngx/` 为准。

## MLX 本地模型

当前不以 Ollama 为主线，本地模型由 MLX 提供 OpenAI 兼容接口。模型缓存目录：

```text
~/Work/models/huggingface/
```

启动脚本和配置：

```text
~/Work/models/mlx/m.sh
~/Work/models/mlx/sup1.5b.ini
~/Work/models/mlx/sup70b.ini
~/Work/models/mlx/sup27b.ini.bak
```

当前模型约定：

| 名称 | 模型 | 端口 | 说明 |
| --- | --- | --- | --- |
| 1.5B | `mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit` | 9080 | 轻量分类、短摘要 |
| 27B | `mlx-community/gemma-2-27b-it-4bit` | 9081 | 日常问答、一般摘要 |
| 70B | `mlx-community/DeepSeek-R1-Distill-Llama-70B-4bit` | 9082 | 复杂摘要、会议纪要、深度分析 |

用 supervisor 管理：

```bash
supervisorctl status
supervisorctl reread
supervisorctl update
supervisorctl start mlx-1.5b
supervisorctl start mlx-27b
supervisorctl start mlx-70b
```

临时前台启动：

```bash
cd ~/Work/models/mlx
./m.sh 1.5b
./m.sh 27b
./m.sh 70b
```

### 本地模型测试用例

统一用这个问题测试接口是否通：

```text
地球到太阳的距离是多少？
```

测试 1.5B：

```bash
curl http://127.0.0.1:9080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "stream": false,
    "model": "mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit",
    "messages": [{"role": "user", "content": "地球到太阳的距离是多少？"}],
    "temperature": 0.7
  }'
```

测试 27B：

```bash
curl http://127.0.0.1:9081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "stream": false,
    "model": "mlx-community/gemma-2-27b-it-4bit",
    "messages": [{"role": "user", "content": "地球到太阳的距离是多少？"}],
    "temperature": 0.7
  }'
```

测试 70B：

```bash
curl http://127.0.0.1:9082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "stream": false,
    "model": "mlx-community/DeepSeek-R1-Distill-Llama-70B-4bit",
    "messages": [{"role": "user", "content": "地球到太阳的距离是多少？"}],
    "temperature": 0.7
  }'
```

正常回答应包含“约 1.5 亿公里”或“1 个天文单位”。

## Paperless-ngx

当前实际运行配置：

```text
~/Work/tools/paperless-ngx/docker-compose.yml
~/Work/tools/paperless-ngx/docker-compose.env
~/Work/tools/paperless-ngx/scripts/set_source_field.py
```

不要优先使用顶层 `~/Work/paperless-ngx/`，它是旧配置目录。

启动、重建、查看日志：

```bash
cd ~/Work/tools/paperless-ngx
docker compose up -d
docker compose ps
docker compose logs --tail=120 webserver
```

当前 Paperless 服务包含：

- `webserver`：Paperless-ngx Web 服务，端口 8000。
- `db`：PostgreSQL。
- `broker`：Redis。
- `tika`：Office 文档解析。
- `gotenberg`：Office 文档转 PDF。

当前消费目录挂载：

```text
~/Work/data/dst -> /usr/src/paperless/consume
```

消费策略：

- 递归扫描子目录。
- 每 30 秒轮询一次，避免 macOS Docker bind mount 漏掉文件事件。
- 忽略音频、视频、日志、JSON、压缩包、HTML/XML/YAML/Markdown 等非目标文件。
- 当前允许进入 Paperless 的主目标是 `txt/docx/xlsx/pdf` 等文档，以及图片文件。

### 来源字段自动分类

Paperless 中已配置自定义选择字段：

```text
来源 = 音频 / 图片 / 文档
```

消费成功后会执行：

```text
~/Work/tools/paperless-ngx/scripts/set_source_field.py
```

自动分类规则：

- 路径或文件名包含 `_asr`、`语音`、`voice`、`tts`，或原始音频扩展名：`来源=音频`
- 图片扩展名或路径包含 `image`、`img`、`ocr`、`scan`、`图片`、`图像`：`来源=图片`
- 其他内容：`来源=文档`

历史文档已做过一次回填。新文档会在消费成功后自动打字段。

## 微信语音到知识库流水线

主代码在：

```text
~/Work/tools/kb_assistant/
```

关键脚本：

| 文件 | 用途 |
| --- | --- |
| `kb_assistant_api.py` | 本地 API，供 n8n 调用 |
| `voice_record_pipeline.py` | 单条语音转写和整理主流程 |
| `submit_media_jobs.py` | 扫描输入目录并提交后台任务 |
| `openclaw_message.py` | 标准化 OpenClaw 消息 |
| `n8n_notify.py` | 结果通知辅助逻辑 |
| `bin/start_api.sh` | 启动本地 API |
| `bin/start_watcher.sh` | 启动目录兜底监听 |
| `bin/recreate_n8n_with_work_mount.sh` | 重建 n8n 容器并挂载 `~/Work:/work` |

推荐数据流：

```text
微信语音/文件
  -> OpenClaw
  -> n8n Webhook
  -> kb_assistant API
  -> data/src/media/YYYYMMDD/
  -> voice_record_pipeline.py
  -> data/archive/YYYYMMDD/
  -> data/dst/YYYYMMDD/<任务名>/
  -> Paperless-ngx 自动消费
```

启动 API：

```bash
~/Work/tools/kb_assistant/bin/start_api.sh
```

手动扫描待处理媒体：

```bash
python3 ~/Work/tools/kb_assistant/submit_media_jobs.py
```

单次处理音频：

```bash
python3 ~/Work/tools/kb_assistant/voice_record_pipeline.py \
  ~/Work/data/src/media/$(date +%Y%m%d)/demo.wav \
  --llm-url http://127.0.0.1:9082/v1 \
  --llm-model mlx-community/DeepSeek-R1-Distill-Llama-70B-4bit
```

每条任务通常会生成：

```text
语音记录.txt
语音记录.docx
语音记录.json
status.json
error.json / error.log   # 失败时出现
_asr/                    # 中间转写文件
```

## 音视频转写工具

主要目录：

```text
~/Work/tools/transvideo/
~/Work/models/whisper/
~/Work/tools/videos/
```

常见工具：

- `tools/transvideo/qwen3asr.py`：Qwen3-ASR 服务测试入口。
- `tools/transvideo/xfyunllm/`：讯飞转写和结果整理。
- `tools/transvideo/funasr/`、`funasrv2/`：FunASR 实验。
- `tools/transvideo/whisper.cpp/`：whisper.cpp 源码和构建产物。
- `tools/videos/`：本地测试音视频和转写结果。

Whisper 示例：

```bash
whisper input.wav --model large-v3 --language Chinese --output_format srt --fp16 False
```

whisper.cpp 示例：

```bash
whisper-cli -m ~/.cache/whisper/ggml-large-v3-turbo.bin -f input.wav -l zh -osrt
```

音频格式转换：

```bash
ffmpeg -i input.m4a -ar 16000 -ac 1 -c:a pcm_s16le output.wav
```

## OpenClaw 与 DeepSeek

OpenClaw 的主要配置在用户目录下，不在本仓库：

```text
~/.openclaw/
~/.openclaw/openclaw.json
~/.openclaw/secrets/
```

DeepSeek API Key 建议放在：

```text
~/.openclaw/secrets/deepseek.json
```

不要把真实 API Key 写进本仓库。

本机还配置过一个本地模型别名：

```text
deepseek-r170b -> http://127.0.0.1:9082/v1
```

OpenAI 兼容接口测试问题仍统一使用：

```text
地球到太阳的距离是多少？
```

## 数据目录约定

`data/` 是运行数据目录，默认不提交 Git。

| 目录 | 说明 |
| --- | --- |
| `data/src/media/` | n8n/OpenClaw 保存原始语音、音频、媒体文件 |
| `data/src/img/` | 图片输入区 |
| `data/src/txt/` | 文本输入区 |
| `data/jobs/audio/` | 语音任务状态和幂等记录 |
| `data/archive/` | 原始文件归档 |
| `data/dst/` | 处理输出，Paperless 当前消费目录 |
| `data/logs/` | 本地脚本日志 |

按日期分组使用 `YYYYMMDD`，例如：

```text
data/src/media/20260429/
data/archive/20260429/
data/dst/20260429/
```

## 常用维护命令

Docker：

```bash
docker ps
docker compose ls
```

Paperless：

```bash
cd ~/Work/tools/paperless-ngx
docker compose ps
docker compose logs --tail=120 webserver
docker compose up -d
docker compose pull
docker compose up -d
```

MLX：

```bash
supervisorctl status
supervisorctl reread
supervisorctl update
tail -f ~/Work/models/mlx/log/70b.log
```

kb_assistant：

```bash
~/Work/tools/kb_assistant/bin/start_api.sh
curl http://127.0.0.1:8765/health
python3 ~/Work/tools/kb_assistant/submit_media_jobs.py
```

## 排障提示

### Paperless 不自动消费

先确认当前运行的是 `tools/paperless-ngx`：

```bash
docker compose ls
docker compose -f ~/Work/tools/paperless-ngx/docker-compose.yml ps
```

再看日志：

```bash
docker compose -f ~/Work/tools/paperless-ngx/docker-compose.yml logs --tail=200 webserver
```

如果看到重复文档错误，说明自动消费链路是通的，只是 Paperless 检测到内容重复。

### docx 或 Excel 不被识别

确认 `tika` 和 `gotenberg` 容器在运行：

```bash
docker compose -f ~/Work/tools/paperless-ngx/docker-compose.yml ps
```

Office 文档依赖 Tika/Gotenberg。没有它们时，Paperless 会把 docx 判为 unknown extension。

### 来源字段没有自动设置

确认 post-consume 脚本已挂载：

```bash
docker compose -f ~/Work/tools/paperless-ngx/docker-compose.yml exec -T webserver \
  printenv PAPERLESS_POST_CONSUME_SCRIPT
```

检查日志里是否有：

```text
Executing post-consume script /usr/src/paperless/scripts/set_source_field.py
Set 来源=...
```

### 模型接口不通

先查 supervisor：

```bash
supervisorctl status
```

再查端口：

```bash
lsof -i :9080
lsof -i :9081
lsof -i :9082
```

## Git 与隐私

默认 `.gitignore` 已排除：

- `data/`
- `models/`
- `tools/videos/`
- Python 缓存
- macOS `.DS_Store`
- Paperless consume/export 运行目录

提交前仍应检查：

```bash
git status --short
```

不要提交：

- API Key、Cookie、账号密码。
- 微信语音、聊天记录、会议录音。
- Paperless 数据库和媒体文件。
- 大体积模型文件。

## 相关文档

- `tools/kb_assistant/README.md`
- `tools/kb_assistant/WORKFLOW_DESIGN.md`
- `tools/transvideo/readme.md`
- `tools/transvideo/xfyunllm/README.md`
- `tools/paperless-ngx/readme`

## 许可证

本仓库未声明统一许可证。第三方项目、模型、Docker 镜像和 API 服务请分别遵循其原始许可证、模型协议和服务条款。

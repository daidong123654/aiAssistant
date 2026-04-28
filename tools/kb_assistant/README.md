# 本地知识库语音助手

这个模块用于把微信收到的语音消息自动整理成本地知识库资料。整体流程基于当前已经部署好的 OpenClaw、n8n、Dify、Paperless-ngx、MLX 本地模型服务和 `tools/transvideo/xfyunllm`。

完整工作流设计见 `WORKFLOW_DESIGN.md`。

## 目标流程

```text
微信语音消息
  -> OpenClaw 接收并转发
  -> n8n Webhook 接收消息
  -> 下载或保存音频到 ~/Work/data/src/YYYYMMDD/
  -> voice_record_pipeline.py 处理音频
  -> 讯飞转写生成语音记录.docx
  -> MLX 本地模型生成语音记录.会议纪要.md
  -> 写入 ~/Work/data/dst/YYYYMMDD/<任务名>/
  -> Paperless-ngx consume 目录自动归档
  -> n8n / OpenClaw 回发处理结果
```

## 目录约定

```text
~/Work/data/
├── src/
│   └── YYYYMMDD/              # OpenClaw/n8n 放入当天收到的音频
├── archive/
│   └── YYYYMMDD/              # 原始音频归档目录
└── dst/
    └── YYYYMMDD/
        └── YYYYMMDD_HHMMSS_xxx/
            ├── 语音记录.docx
            ├── 语音记录.txt
            ├── 语音记录.json
            ├── 语音记录.会议纪要.md
            ├── metadata.json
            └── _asr/
```

说明：

- `YYYYMMDD` 是当天日期，例如 `20260428`。
- `data/src/YYYYMMDD/` 是监听目录。
- 收到音频后会自动移动到 `data/archive/YYYYMMDD/`，避免重复处理。
- 最终文件会进入 `data/dst/YYYYMMDD/<任务名>/`，每条语音一个独立任务目录，避免同名覆盖。
- `paperless-ngx/consume/` 会收到 `语音记录.docx` 和 `语音记录.会议纪要.md` 的副本，由 Paperless-ngx 自动入库。

## 使用前检查

### 0. 让 n8n 能写入 Work 目录

当前 n8n 跑在 Docker 容器里，需要把宿主机 `~/Work` 挂载为容器内 `/work`。

如果 n8n 容器已经存在，运行：

```bash
~/Work/tools/kb_assistant/bin/recreate_n8n_with_work_mount.sh
```

该脚本会保留 `n8n_data` 数据卷，只重建 n8n 容器。

### 1. 确认 MLX 本地模型服务

Ollama 已废弃，当前使用 `models/mlx/sup*.ini` 通过 supervisor 管理本地模型：

```text
~/Work/models/mlx/sup1.5b.ini  -> http://127.0.0.1:9080/v1
~/Work/models/mlx/sup27b.ini   -> http://127.0.0.1:9081/v1
~/Work/models/mlx/sup70b.ini   -> http://127.0.0.1:9082/v1
```

查看服务状态：

```bash
supervisorctl status
```

会议纪要建议走 70B 接口，轻量分类和短摘要可以走 1.5B 或 27B 接口。

### 2. 配置讯飞转写密钥

优先使用环境变量：

```bash
export XFYUN_APPID="你的 appid"
export XFYUN_API_KEY="你的 api key"
export XFYUN_API_SECRET="你的 api secret"
```

也可以继续使用 `tools/transvideo/xfyunllm/Ifasr.py` 里已有的默认配置。

### 3. 创建目录

```bash
mkdir -p ~/Work/data/src/$(date +%Y%m%d)
mkdir -p ~/Work/data/archive/$(date +%Y%m%d)
mkdir -p ~/Work/data/dst/$(date +%Y%m%d)
mkdir -p ~/Work/paperless-ngx/consume
```

### 4. 可选：配置 Dify 知识库自动导入

如果希望会议纪要生成后自动进入 Dify 知识库，配置：

```bash
export DIFY_API_URL="http://127.0.0.1/v1"
export DIFY_API_KEY="你的 Dify Knowledge API Key"
export DIFY_DATASET_ID="你的知识库 Dataset ID"
```

未配置时会自动跳过 Dify 导入，不影响 `docx`、会议纪要和 Paperless 归档。

## 单次处理

```bash
python3 ~/Work/tools/kb_assistant/voice_record_pipeline.py ~/Work/data/src/$(date +%Y%m%d)/demo.wav
```

指定 MLX 模型接口：

```bash
python3 ~/Work/tools/kb_assistant/voice_record_pipeline.py \
  ~/Work/data/src/$(date +%Y%m%d)/demo.wav \
  --llm-url http://127.0.0.1:9082/v1 \
  --llm-model mlx-community/DeepSeek-R1-Distill-Llama-70B-4bit
```

## API 与兜底监听

启动本地 API，供 n8n 调用：

```bash
~/Work/tools/kb_assistant/bin/start_api.sh
```

生产主链路由 n8n 调用 API 提交任务，不需要启动 watcher。需要手工导入、NAS 同步等目录兜底时，再启动本地语音监听：

```bash
~/Work/tools/kb_assistant/bin/start_watcher.sh
```

监听模式会持续扫描：

```text
~/Work/data/src/media/
```

手动复制新的音频文件进来后，脚本会自动处理。

## n8n 编排建议

可导入的 n8n 工作流模板：

```text
tools/kb_assistant/n8n_workflows/openclaw_voice_ingest.json
tools/kb_assistant/n8n_workflows/openclaw_result_notify.json
```

导入前确认：

- n8n 容器已挂载 `~/Work:/work`。
- 本地 API 已启动：`http://host.docker.internal:8765/health`。
- 将通知工作流里的 `http://OPENCLAW_HOST:OPENCLAW_PORT/send` 改成 OpenClaw 实际回发接口。

### 工作流 1：微信消息入口

节点建议：

1. `Webhook`：接收 OpenClaw 转发的微信消息。
2. `HTTP Request`：调用本地 API 标准化消息并生成保存路径。
3. `IF`：判断消息类型是否为语音或音频文件。
4. `HTTP Request`：下载音频文件。
5. `Write Binary File`：保存到 `container_save_path`。
6. `HTTP Request`：调用本地 API `POST /audio/jobs` 提交后台转写任务。
7. `Respond to Webhook`：回复“已收到，已提交后台转写任务”。
8. 结果由通知工作流扫描 `metadata.json/status.json` 后回发。

标准化 OpenClaw 消息：

```text
POST http://host.docker.internal:8765/openclaw/normalize
```

提交音频处理任务：

```text
POST http://host.docker.internal:8765/audio/jobs
```

请求体示例：

```json
{
  "audio_path": "/Users/jianfeisu/Work/data/src/media/20260429/demo.amr",
  "message_id": "wxmsg_abc123",
  "from_user": "张三",
  "idempotency_key": "wxmsg_abc123"
}
```

查询任务状态：

```text
GET http://host.docker.internal:8765/audio/jobs/{job_id}
```

生产主链路使用 n8n 显式提交任务，不依赖 watcher。`voice_record_pipeline.py --watch` 仅保留给手工导入、NAS 同步等目录兜底场景。

### 工作流 2：结果通知

节点建议：

1. `Cron`：每分钟扫描 `~/Work/data/dst/YYYYMMDD/*/metadata.json`。
2. `Execute Command`：列出未通知任务。
3. `IF`：判断是否有待通知任务。
4. `HTTP Request`：通过 OpenClaw 回发 `语音记录.docx` 和 `语音记录.会议纪要.md` 路径或文件。
5. `Execute Command`：写入 `.notified` 标记，避免重复通知。

列出未通知任务：

```text
GET http://host.docker.internal:8765/notifications?include_failed=1
```

回发成功后标记已通知：

```text
POST http://host.docker.internal:8765/notifications/mark
```

## Dify 对接方式

Dify 在这个方案中承担“知识库问答”和“知识检索增强”的角色：

1. Paperless-ngx 负责保存文档原件和 OCR 检索。
2. Dify 创建知识库，导入 `data/dst/YYYYMMDD/*/语音记录.会议纪要.md`。
3. Dify 模型供应商配置为 OpenAI-API-compatible，指向 MLX 本地接口。
4. Dify 应用面向 n8n 暴露 API，n8n 收到微信文字问题后调用 Dify 返回答案。

当前流水线已经支持在配置 `DIFY_API_KEY` 和 `DIFY_DATASET_ID` 后自动导入会议纪要。也可以把会议纪要生成放到 Dify Workflow 中，但当前脚本直接调用 MLX 本地模型接口，链路更短，排错更容易。

## Paperless-ngx 入库

脚本默认把以下文件复制到：

```text
~/Work/paperless-ngx/consume/
```

文件包括：

- `语音记录.docx`
- `语音记录.会议纪要.md`

Paperless-ngx 会从 consume 目录自动消费入库。如果当前 Paperless-ngx 实际使用的是 `tools/paperless-ngx/consume/`，可以启动脚本时指定：

```bash
python3 ~/Work/tools/kb_assistant/voice_record_pipeline.py --watch \
  --paperless-consume-dir ~/Work/tools/paperless-ngx/consume
```

## OpenClaw 接入约定

OpenClaw 只负责两件事：

- 接收微信消息并把消息体转发到 n8n Webhook。
- 接收 n8n 的回调请求，把处理状态或文件发送回微信。

n8n Webhook 推荐接收字段：

```json
{
  "message_id": "微信消息 ID",
  "from_user": "发送人",
  "message_type": "voice",
  "file_url": "音频下载地址",
  "file_name": "原始文件名",
  "created_at": "消息时间"
}
```

如果 OpenClaw 给的是二进制文件，可以让 n8n 的 Webhook 直接接收 binary data，再写入 `data/src/YYYYMMDD/`。

## 常见命令

查看监听脚本是否运行：

```bash
ps ax | grep voice_record_pipeline.py
```

查看今天的输入目录：

```bash
ls ~/Work/data/src/$(date +%Y%m%d)
```

查看今天的输出目录：

```bash
find ~/Work/data/dst/$(date +%Y%m%d) -maxdepth 2 -type f
```

列出待通知任务：

```bash
python3 ~/Work/tools/kb_assistant/n8n_notify.py list --include-failed
```

检查本地 API：

```bash
curl http://127.0.0.1:8765/health
```

## 注意事项

- 讯飞转写需要外网访问讯飞接口，不是纯离线链路。
- 会议纪要生成走本地 MLX 模型服务，需要确认 `models/mlx/sup*.ini` 对应服务已启动。
- DeepSeek R1 输出中可能包含思考标签，脚本会自动裁掉 `</think>` 之前的内容。
- 长音频会显著增加讯飞轮询时间和本地模型生成时间。

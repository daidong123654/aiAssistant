# WPS 音频/视频转文字自动化

这个目录实现“方案 A：WPS 自动化（生产级）”的 shell 调度版：

1. 把音频/视频放进 `input/`
2. `bin/worker.sh` 单任务消费队列
3. `osascript scripts/trigger.scpt` 通过 Finder 快捷键触发 WPS Quick Action
4. `osascript scripts/export.scpt` 进入“上传音视频”，点击“立即上传”，选择任务文件，等待转换完成后下载源文
5. `bin/worker.sh` 监听 `txt/srt` 文件出现，收集到 `output/`
6. 超时后 watchdog 结束 WPS，并把任务放入 `failed/`

## 第一次使用

先在系统里配置 Quick Action 快捷键：

系统设置 -> 键盘 -> 键盘快捷键 -> 服务

给 WPS 的“音频/视频转文字”绑定：

```text
Control + Option + T
```

然后初始化目录：

```bash
./bin/init.sh
```

把文件加入队列：

```bash
./bin/enqueue.sh /path/to/audio.m4a
```

把失败目录里的任务重新放回队列：

```bash
./bin/requeue_failed.sh
```

如果 worker 被中断，`processing/` 里残留的任务可以重新放回队列：

```bash
./bin/requeue_processing.sh
```

启动 worker：

```bash
./bin/worker.sh
```

需要常驻轮询：

```bash
./bin/worker.sh --daemon
```

如果 UI 自动化提示找不到“上传音视频”“立即上传”或“下载源文”，先让 WPS 停在对应页面，然后导出当前可见控件文本：

```bash
osascript scripts/dump_wps_ui.scpt > logs/wps-ui.txt
```

## 配置

主要配置在 `config.sh`：

- `INPUT_DIR`：待处理队列
- `OUTPUT_DIR`：最终产物目录
- `EXPORT_WATCH_DIRS`：监听 WPS 导出文件出现的位置，默认包含 `output/`、`~/Downloads`、`~/Desktop`
- `WPS_CONVERSION_TIMEOUT_SECONDS`：WPS 上传和转换最长等待时间
- `TRANSCRIBE_TIMEOUT_SECONDS`：点击下载源文后，监听导出文件出现的最长等待时间
- `RESTART_WPS_EVERY_JOBS`：每处理 N 个任务重启 WPS
- `WPS_PROCESS_MATCH`：WPS 进程名匹配表达式

如果 WPS 导出时总是落在固定目录，建议把该目录放到 `EXPORT_WATCH_DIRS` 的第一项。

## 生产运行建议

- WPS 不支持并发，本项目用 `run/worker.lock` 强制单 worker。
- `run/worker.lock/pid` 会记录当前 worker 进程，残留锁会自动清理。
- 成功标志是监听到新生成的 `.txt` 或 `.srt` 文件。
- AppleScript 触发、上传、等待转换、下载源文都有外层超时，避免 UI 自动化卡死后拖住队列。
- 超时会触发 `killall WPS` / `killall wps`，避免卡死。
- 建议用 macOS 定时任务每天重启一次 WPS，或者依赖 `RESTART_WPS_EVERY_JOBS`。

# 讯飞星火语音转写工具

根据讯飞星火语音转写接口实现音频转写，并把结果输出为 `txt`、`json`、`docx` 三种格式。每一段转写内容都会带时间轴和角色编号。

输出示例：

```text
【文件信息】
文件名称：call_2026-04-21_15_15_15.mp3
文件完整路径：/Users/example/audio/call_2026-04-21_15_15_15.mp3
原始音频文件MD5：aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
转换后音频文件MD5：bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
名称时间：2026-04-21 15:15:15
文件创建时间：2026-04-22 10:00:00
文件修改时间：2026-04-23 11:00:00

【录音内容】
[00:00:05 – 00:00:12] 角色1：一楼737噢，那我就上楼。
```

## 功能

- 支持 WAV 音频直接转写。
- 非 WAV 音频会自动调用 `ffmpeg` 转成 WAV。
- 对源文件和转换后的 WAV 文件分别计算 MD5。
- 按日期创建输出目录：`output/YYYYMMDD/`。
- 脚本启动时生成固定批次号 `YYYYMMDDHHMMSS`，同一次转写的三种结果文件批次号一致。
- 转换后的临时 WAV 只放在系统临时目录，不写入 `output` 结果目录。
- 统一输出三种结果文件：`.txt`、`.json`、`.docx`。
- 在识别结果开头写入文件名称、文件完整路径、名称时间、文件创建时间、文件修改时间。
- 按讯飞接口参数 `roleType=1` 开启通用角色分离。
- 解析讯飞返回的 `bg`、`ed`、`rl` 字段，生成时间轴和角色文本。

## 文件时间信息

程序会从源文件收集三类时间，并写入最终识别结果开头：

- `名称时间`：从源文件名称中提取的时间。
- `文件完整路径`：源文件的绝对路径。
- `文件创建时间`：源文件在文件系统中的创建时间。
- `文件修改时间`：源文件在文件系统中的最后修改时间。

名称时间支持常见格式，例如：

```text
2026-04-21_15_15_15
2026-04-21 15:15:15
20260421151515
2026年04月21日15时15分15秒
```

如果文件名中没有可识别时间，`名称时间` 会写为 `未识别`。

如果源文件和最终 WAV 文件的 MD5 一样，头部只写一行：

```text
音频文件MD5：aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

如果两者不一样，头部会写两行：

```text
原始音频文件MD5：aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
转换后音频文件MD5：bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

## 环境要求

- Python 3.8+
- `ffmpeg`：仅在输入文件不是 WAV 时需要

检查 `ffmpeg`：

```bash
ffmpeg -version
```

本项目当前实现只使用 Python 标准库，不需要安装 `requests`、`python-docx` 等额外依赖。

## 配置接口信息

打开 `Ifasr.py`，在文件顶部填写你的讯飞接口信息：

```python
APPID = "请填写你的appId"
API_KEY = "请填写你的APIKey"
API_SECRET = "请填写你的APISecret"
ROLE_TYPE = "1"
```

`ROLE_TYPE = "1"` 表示通用角色分离，讯飞返回的 `rl` 会被输出为 `角色1`、`角色2` 等。

也可以使用环境变量覆盖：

```bash
export XFYUN_APPID="你的appId"
export XFYUN_API_KEY="你的APIKey"
export XFYUN_API_SECRET="你的APISecret"
export XFYUN_ROLE_TYPE="1"
```

## 使用方法

转写一个音频文件：

```bash
python3 Ifasr.py audio/lfasr_涉政.wav
```

指定输出根目录：

```bash
python3 Ifasr.py audio/demo.mp3 --output-root output
```

调整轮询间隔：

```bash
python3 Ifasr.py audio/demo.wav --poll-interval 5 --max-attempts 720
```

如果遇到 HTTPS 证书校验问题，可临时关闭证书校验：

```bash
python3 Ifasr.py audio/demo.wav --insecure
```

## 输出规则

程序启动时会先生成一个批次号：

```text
YYYYMMDDHHMMSS
```

同一次运行生成的 `.txt`、`.json`、`.docx` 三个文件会使用相同批次号，并把批次号放在扩展名前。

程序会先计算源文件 MD5。

如果输入文件不是 WAV：

1. 调用 `ffmpeg` 转成：

   ```text
   文件原名称.源文件md5.wav
   ```

2. 计算新 WAV 文件 MD5。

3. 重命名为：

   ```text
   文件原名称.源文件md5.新文件md5.wav
   ```

如果输入文件已经是 WAV，也会复制到临时目录，并命名为：

```text
文件原名称.源文件md5.源文件md5.wav
```

最终三种转写结果会生成在 `output/YYYYMMDD/`：

```text
output/YYYYMMDD/文件原名称.源文件md5.新文件md5.批次号.txt
output/YYYYMMDD/文件原名称.源文件md5.新文件md5.批次号.json
output/YYYYMMDD/文件原名称.源文件md5.新文件md5.批次号.docx
```

准备好的 WAV 文件只会保存在系统临时目录中，用于上传转写；转写流程结束后临时目录会自动清理。

## JSON 内容说明

`.json` 文件包含：

- `file_info`：文件名称、文件完整路径、名称时间、文件创建时间、文件修改时间
- `source_md5`：源文件 MD5
- `wav_md5`：最终 WAV 文件 MD5
- `wav_file`：最终 WAV 文件名
- `segments`：按段落解析后的转写结果
- `api_response`：讯飞接口原始返回结果

整体结构示例：

```json
{
  "file_info": {
    "file_name": "call_2026-04-21_15_15_15.mp3",
    "file_path": "/Users/example/audio/call_2026-04-21_15_15_15.mp3",
    "name_time": "2026-04-21 15:15:15",
    "created_time": "2026-04-22 10:00:00",
    "modified_time": "2026-04-23 11:00:00"
  },
  "source_md5": "...",
  "wav_md5": "...",
  "wav_file": "call.xxx.yyy.wav",
  "segments": [
    {
      "begin_ms": 5000,
      "end_ms": 12000,
      "role": "1",
      "text": "一楼737噢，那我就上楼。",
      "begin": "00:00:05",
      "end": "00:00:12",
      "line": "[00:00:05 – 00:00:12] 角色1：一楼737噢，那我就上楼。"
    }
  ],
  "api_response": {}
}
```

## 常见问题

### 缺少 appid/api-key/api-secret

请确认已经在 `Ifasr.py` 顶部填写：

```python
APPID = "..."
API_KEY = "..."
API_SECRET = "..."
```

或设置了对应环境变量。

### 非 WAV 文件转写失败

请确认系统已安装 `ffmpeg`，并且命令行可以直接执行：

```bash
ffmpeg -version
```

### 转写一直处理中

可以适当增加最大轮询次数：

```bash
python3 Ifasr.py audio/demo.wav --max-attempts 1200
```

默认轮询间隔为 10 秒，最大轮询 720 次。

# -*- coding: utf-8 -*-
import argparse
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
from pathlib import Path
import random
import re
import shutil
import ssl
import string
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
import zipfile
from xml.sax.saxutils import escape

import orderResult


LFASR_HOST = "https://office-api-ist-dx.iflyaisol.com"
API_UPLOAD = "/v2/upload"
API_GET_RESULT = "/v2/getResult"

# 在这里填写你的讯飞接口信息；也可以用命令行参数或环境变量覆盖。
APPID = "59b81e60"
API_KEY = "a188a639b083585a34696ffda45f7e6f"
API_SECRET = "MDRkYzIwNTViZDg5MjE0ZDdmMjAzN2Y3"

# 角色分离：0=不开启，1=通用角色分离，3=声纹角色分离。
ROLE_TYPE = "1"


def md5_file(path, chunk_size=1024 * 1024):
    digest = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_with_tz():
    local_now = dt.datetime.now().astimezone()
    return local_now.strftime("%Y-%m-%dT%H:%M:%S%z")


def random_string(length=16):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def sign_params(params, secret):
    parts = []
    for key, value in sorted(params.items(), key=lambda item: item[0]):
        if key == "signature" or value is None or str(value).strip() == "":
            continue
        encoded_key = urllib.parse.quote(str(key), safe="")
        encoded_value = urllib.parse.quote(str(value), safe="")
        parts.append(f"{encoded_key}={encoded_value}")
    base_string = "&".join(parts)
    signature = base64.b64encode(
        hmac.new(secret.encode("utf-8"), base_string.encode("utf-8"), "sha1").digest()
    ).decode("utf-8")
    return signature, base_string


def encoded_query(params):
    return urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def wav_duration_ms(path):
    with wave.open(str(path), "rb") as wav_file:
        return int(round(wav_file.getnframes() / wav_file.getframerate() * 1000))


def _try_datetime(parts):
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    hour = int(parts[3]) if len(parts) > 3 and parts[3] is not None else 0
    minute = int(parts[4]) if len(parts) > 4 and parts[4] is not None else 0
    second = int(parts[5]) if len(parts) > 5 and parts[5] is not None else 0
    try:
        return dt.datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def extract_datetime_from_name(filename):
    name = Path(filename).stem
    patterns = [
        r"(?<!\d)(20\d{2})([01]\d)([0-3]\d)([0-2]\d)([0-5]\d)([0-5]\d)(?!\d)",
        r"(?<!\d)(20\d{2})\D+([01]?\d)\D+([0-3]?\d)\D+([0-2]?\d)\D+([0-5]?\d)(?:\D+([0-5]?\d))?(?!\d)",
        r"(?<!\d)(20\d{2})\D+([01]?\d)\D+([0-3]?\d)(?!\d)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, name):
            parsed = _try_datetime(match.groups())
            if parsed:
                return parsed
    return None


def format_datetime(value):
    if not value:
        return "未识别"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def file_datetime_from_timestamp(timestamp):
    return dt.datetime.fromtimestamp(timestamp)


def collect_file_info(source_path):
    source = Path(source_path).expanduser().resolve()
    stat = source.stat()
    created_timestamp = getattr(stat, "st_birthtime", stat.st_ctime)
    name_datetime = extract_datetime_from_name(source.name)
    created_datetime = file_datetime_from_timestamp(created_timestamp)
    modified_datetime = file_datetime_from_timestamp(stat.st_mtime)
    return {
        "file_name": source.name,
        "file_path": str(source),
        "name_time": format_datetime(name_datetime),
        "created_time": format_datetime(created_datetime),
        "modified_time": format_datetime(modified_datetime),
    }


def prepare_wav(source_path, work_dir):
    source = Path(source_path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"文件不存在：{source}")

    work_dir.mkdir(parents=True, exist_ok=True)
    source_md5 = md5_file(source)
    source_stem = source.stem

    if source.suffix.lower() == ".wav":
        new_md5 = source_md5
        final_name = f"{source_stem}.{source_md5}.{new_md5}.wav"
        final_path = work_dir / final_name
        if source != final_path:
            shutil.copy2(source, final_path)
        return final_path, source_md5, new_md5

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，无法把非 WAV 文件转成 WAV")

    first_wav = work_dir / f"{source_stem}.{source_md5}.wav"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(first_wav),
        ],
        check=True,
    )
    new_md5 = md5_file(first_wav)
    final_path = work_dir / f"{source_stem}.{source_md5}.{new_md5}.wav"
    if final_path.exists():
        final_path.unlink()
    first_wav.rename(final_path)
    return final_path, source_md5, new_md5


class XfyunAsrClient:
    def __init__(self, appid, access_key_id, access_key_secret, role_type="1", insecure=False):
        self.appid = appid
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.role_type = role_type
        self.signature_random = random_string()
        self.insecure = insecure

    def _urlopen_json(self, url, headers, body, timeout):
        context = ssl._create_unverified_context() if self.insecure else None
        request = urllib.request.Request(url=url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"请求失败：{exc}") from exc
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"API 返回非 JSON 数据：{payload}") from exc

    def upload_audio(self, audio_path):
        audio_path = Path(audio_path).resolve()
        params = {
            "appId": self.appid,
            "accessKeyId": self.access_key_id,
            "dateTime": now_with_tz(),
            "signatureRandom": self.signature_random,
            "fileSize": str(audio_path.stat().st_size),
            "fileName": audio_path.name,
            "language": "autodialect",
            "duration": str(wav_duration_ms(audio_path)),
            "roleType": self.role_type,
        }
        signature, base_string = sign_params(params, self.access_key_secret)
        url = f"{LFASR_HOST}{API_UPLOAD}?{encoded_query(params)}"
        headers = {"Content-Type": "application/octet-stream", "signature": signature}
        result = self._urlopen_json(url, headers, audio_path.read_bytes(), timeout=60)
        if result.get("code") != "000000":
            raise RuntimeError(
                "上传失败："
                f"{result.get('code')} {result.get('descInfo', '')}\n"
                f"签名原始串：{base_string}"
            )
        return result["content"]["orderId"], result

    def get_result(self, order_id, poll_interval=10, max_attempts=720):
        last_result = None
        for attempt in range(1, max_attempts + 1):
            params = {
                "appId": self.appid,
                "accessKeyId": self.access_key_id,
                "dateTime": now_with_tz(),
                "ts": str(int(time.time())),
                "orderId": order_id,
                "signatureRandom": self.signature_random,
            }
            signature, _ = sign_params(params, self.access_key_secret)
            url = f"{LFASR_HOST}{API_GET_RESULT}?{encoded_query(params)}"
            headers = {"Content-Type": "application/json", "signature": signature}
            result = self._urlopen_json(url, headers, b"{}", timeout=30)
            last_result = result
            if result.get("code") != "000000":
                raise RuntimeError(f"查询失败：{result.get('code')} {result.get('descInfo', '')}")

            status = result.get("content", {}).get("orderInfo", {}).get("status")
            if status == 4:
                return result
            if status != 3:
                raise RuntimeError(f"转写异常：status={status}, desc={result.get('descInfo', '')}")
            print(f"转写处理中：第 {attempt}/{max_attempts} 次查询，{poll_interval} 秒后重试")
            time.sleep(poll_interval)
        raise TimeoutError(f"查询超时，最后响应：{last_result}")

    def transcribe(self, audio_path, poll_interval=10, max_attempts=720):
        order_id, upload_result = self.upload_audio(audio_path)
        print(f"上传成功，orderId={order_id}")
        result = self.get_result(order_id, poll_interval=poll_interval, max_attempts=max_attempts)
        result.setdefault("_uploadResult", upload_result)
        return result


def format_timestamp(milliseconds):
    seconds = max(0, int(round(milliseconds / 1000)))
    hh = seconds // 3600
    mm = (seconds % 3600) // 60
    ss = seconds % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def format_segment(segment):
    begin = format_timestamp(segment["begin_ms"])
    end = format_timestamp(segment["end_ms"])
    return f"[{begin} – {end}] 角色{segment['role']}：{segment['text']}"


def metadata_lines(file_info, source_md5, wav_md5):
    lines = [
        "【文件信息】",
        f"文件名称：{file_info['file_name']}",
        f"文件完整路径：{file_info['file_path']}",
    ]
    if source_md5 == wav_md5:
        lines.append(f"音频文件MD5：{source_md5}")
    else:
        lines.extend(
            [
                f"原始音频文件MD5：{source_md5}",
                f"转换后音频文件MD5：{wav_md5}",
            ]
        )
    lines.extend(
        [
            f"名称时间：{file_info['name_time']}",
            f"文件创建时间：{file_info['created_time']}",
            f"文件修改时间：{file_info['modified_time']}",
        ]
    )
    return lines


def write_txt(path, segments, file_info, source_md5, wav_md5):
    lines = metadata_lines(file_info, source_md5, wav_md5) + ["", "【录音内容】"] + [
        format_segment(segment) for segment in segments
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path, api_response, segments, source_md5, wav_md5, wav_file, file_info):
    payload = {
        "file_info": file_info,
        "source_md5": source_md5,
        "wav_md5": wav_md5,
        "wav_file": wav_file.name,
        "segments": [
            {
                **segment,
                "begin": format_timestamp(segment["begin_ms"]),
                "end": format_timestamp(segment["end_ms"]),
                "line": format_segment(segment),
            }
            for segment in segments
        ],
        "api_response": api_response,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _docx_paragraph(text):
    return (
        "<w:p><w:r><w:rPr><w:rFonts w:ascii=\"Microsoft YaHei\" "
        "w:eastAsia=\"Microsoft YaHei\" w:hAnsi=\"Microsoft YaHei\"/></w:rPr>"
        f"<w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"
    )


def write_docx(path, title, segments, file_info, source_md5, wav_md5):
    paragraphs = [
        "<w:p><w:pPr><w:pStyle w:val=\"Title\"/></w:pPr><w:r><w:t>"
        f"{escape(title)}</w:t></w:r></w:p>"
    ]
    paragraphs.extend(_docx_paragraph(line) for line in metadata_lines(file_info, source_md5, wav_md5))
    paragraphs.append(_docx_paragraph(""))
    paragraphs.append(_docx_paragraph("【录音内容】"))
    paragraphs.extend(_docx_paragraph(format_segment(segment)) for segment in segments)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(paragraphs)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" '
        'w:right="1440" w:bottom="1440" w:left="1440" w:header="720" '
        'w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document_xml)


def build_outputs(api_response, wav_file, source_md5, wav_md5, output_dir, file_info, batch_id):
    segments = orderResult.parse_segments(api_response)
    if not segments:
        raise RuntimeError("转写完成，但未解析到有效文本段落")
    base = wav_file.with_suffix("").name
    result_base = f"{base}.{batch_id}"
    txt_path = output_dir / f"{result_base}.txt"
    json_path = output_dir / f"{result_base}.json"
    docx_path = output_dir / f"{result_base}.docx"
    write_txt(txt_path, segments, file_info, source_md5, wav_md5)
    write_json(json_path, api_response, segments, source_md5, wav_md5, wav_file, file_info)
    write_docx(docx_path, base, segments, file_info, source_md5, wav_md5)
    return txt_path, json_path, docx_path


def parse_args():
    parser = argparse.ArgumentParser(description="讯飞星火语音转写，并输出 txt/json/docx。")
    parser.add_argument("audio", help="待转写音频文件路径")
    parser.add_argument("--appid", default=os.getenv("XFYUN_APPID") or APPID, help="讯飞 appId")
    parser.add_argument("--api-key", default=os.getenv("XFYUN_API_KEY") or API_KEY, help="讯飞 APIKey/accessKeyId")
    parser.add_argument("--api-secret", default=os.getenv("XFYUN_API_SECRET") or API_SECRET, help="讯飞 APISecret/accessKeySecret")
    parser.add_argument("--role-type", default=os.getenv("XFYUN_ROLE_TYPE") or ROLE_TYPE, help="角色分离类型：0=不开启，1=通用角色分离，3=声纹角色分离")
    parser.add_argument("--output-root", default="output", help="输出根目录，默认 output")
    parser.add_argument("--poll-interval", type=int, default=10, help="轮询间隔秒数")
    parser.add_argument("--max-attempts", type=int, default=720, help="最大轮询次数")
    parser.add_argument("--insecure", action="store_true", help="关闭 HTTPS 证书校验")
    return parser.parse_args()


def main():
    args = parse_args()
    batch_id = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    placeholders = {
        "appid": "请填写你的appId",
        "api-key": "请填写你的APIKey",
        "api-secret": "请填写你的APISecret",
    }
    missing = [
        name
        for name, value in (("appid", args.appid), ("api-key", args.api_key), ("api-secret", args.api_secret))
        if not value or value == placeholders[name]
    ]
    if missing:
        raise SystemExit(
            "缺少参数："
            + ", ".join(missing)
            + "。请在 Ifasr.py 顶部填写 APPID/API_KEY/API_SECRET，或设置 XFYUN_APPID/XFYUN_API_KEY/XFYUN_API_SECRET。"
        )

    date_dir = dt.datetime.now().strftime("%Y%m%d")
    output_dir = Path(args.output_root).expanduser().resolve() / date_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    file_info = collect_file_info(args.audio)
    work_root = Path(tempfile.gettempdir()) / "xfyunllm" / batch_id
    work_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{batch_id}-", dir=work_root.parent) as tmp_dir:
        work_dir = Path(tmp_dir)
        wav_file, source_md5, wav_md5 = prepare_wav(args.audio, work_dir)
        print(f"批次号：{batch_id}")
        print(f"临时 WAV：{wav_file}")
        print(f"文件名称：{file_info['file_name']}")
        print(f"文件完整路径：{file_info['file_path']}")
        print(f"名称时间：{file_info['name_time']}")
        print(f"文件创建时间：{file_info['created_time']}")
        print(f"文件修改时间：{file_info['modified_time']}")
        print(f"源文件 MD5：{source_md5}")
        print(f"新 WAV MD5：{wav_md5}")

        client = XfyunAsrClient(args.appid, args.api_key, args.api_secret, role_type=args.role_type, insecure=args.insecure)
        api_response = client.transcribe(wav_file, poll_interval=args.poll_interval, max_attempts=args.max_attempts)
        txt_path, json_path, docx_path = build_outputs(
            api_response, wav_file, source_md5, wav_md5, output_dir, file_info, batch_id
        )
    print("已生成：")
    print(txt_path)
    print(json_path)
    print(docx_path)


if __name__ == "__main__":
    main()

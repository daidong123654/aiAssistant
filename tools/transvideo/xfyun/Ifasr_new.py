# -*- coding: utf-8 -*-
import argparse
import base64
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

LFASR_HOST = "https://raasr.xfyun.cn/v2/api"
API_UPLOAD = "/upload"
API_GET_RESULT = "/getResult"

DEFAULT_APPID = "59b81e60"
DEFAULT_SECRET_KEY = "79afab0e6c6cef51a01da3173e740ca3"
POLL_INTERVAL_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 60
DEFAULT_ROLE_TYPE = 1
DEFAULT_ROLE_NUM = 0


def file_md5(path, chunk_size=1024 * 1024):
    digest = hashlib.md5()
    with open(path, "rb") as file_obj:
        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def ensure_wav_file(source_path):
    source_path = Path(source_path).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError("找不到音频文件: {}".format(source_path))

    source_md5 = file_md5(source_path)
    first_wav_path = source_path.with_name(
        "{}.{}.wav".format(source_path.stem, source_md5)
    )

    if source_path.suffix.lower() == ".wav":
        if source_path.resolve() != first_wav_path.resolve():
            shutil.copy2(source_path, first_wav_path)
    else:
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(first_wav_path),
        ]
        subprocess.run(command, check=True)

    new_md5 = file_md5(first_wav_path)
    final_wav_path = source_path.with_name(
        "{}.{}.{}.wav".format(source_path.stem, source_md5, new_md5)
    )
    if first_wav_path.resolve() != final_wav_path.resolve():
        if final_wav_path.exists():
            final_wav_path.unlink()
        first_wav_path.rename(final_wav_path)

    return {
        "source_path": str(source_path),
        "source_md5": source_md5,
        "wav_path": str(final_wav_path),
        "wav_md5": new_md5,
        "new_file_name": final_wav_path.name,
        "new_file_stem": final_wav_path.stem,
    }


def post_binary(url, data=None):
    request = urllib.request.Request(
        url=url,
        data=data or b"",
        headers={"Content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


class RequestApi(object):
    def __init__(
        self,
        appid,
        secret_key,
        upload_file_path,
        result_type="transfer",
        role_type=DEFAULT_ROLE_TYPE,
        role_num=DEFAULT_ROLE_NUM,
    ):
        self.appid = appid
        self.secret_key = secret_key
        self.upload_file_path = upload_file_path
        self.result_type = result_type
        self.role_type = role_type
        self.role_num = role_num
        self.ts = str(int(time.time()))
        self.signa = self.get_signa()

    def get_signa(self):
        md5 = hashlib.md5((self.appid + self.ts).encode("utf-8")).hexdigest()
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            md5.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    def upload(self):
        upload_file_path = self.upload_file_path
        file_len = os.path.getsize(upload_file_path)
        file_name = os.path.basename(upload_file_path)

        params = {
            "appId": self.appid,
            "signa": self.signa,
            "ts": self.ts,
            "fileSize": file_len,
            "fileName": file_name,
            "duration": "200",
            "roleType": self.role_type,
            "roleNum": self.role_num,
        }
        with open(upload_file_path, "rb") as file_obj:
            result = post_binary(
                LFASR_HOST + API_UPLOAD + "?" + urllib.parse.urlencode(params),
                file_obj.read(),
            )
        if result.get("code") != "000000":
            raise RuntimeError("上传失败: {}".format(json.dumps(result, ensure_ascii=False)))
        return result

    def get_result(self):
        upload_response = self.upload()
        order_id = upload_response["content"]["orderId"]
        params = {
            "appId": self.appid,
            "signa": self.signa,
            "ts": self.ts,
            "orderId": order_id,
            "resultType": self.result_type,
        }

        while True:
            result = post_binary(
                LFASR_HOST + API_GET_RESULT + "?" + urllib.parse.urlencode(params)
            )
            if result.get("code") != "000000":
                raise RuntimeError(
                    "查询失败: {}".format(json.dumps(result, ensure_ascii=False))
                )

            order_info = result.get("content", {}).get("orderInfo", {})
            status = order_info.get("status")
            print("orderId={} status={}".format(order_id, status))
            if status == 4:
                return result
            if status == -1:
                raise RuntimeError(
                    "转写失败: {}".format(json.dumps(result, ensure_ascii=False))
                )
            time.sleep(POLL_INTERVAL_SECONDS)


def parse_order_result(raw_result):
    if isinstance(raw_result, str):
        if not raw_result.strip():
            return {}
        return json.loads(raw_result)
    return raw_result or {}


def json_1best_to_dict(json_1best):
    if isinstance(json_1best, str):
        return json.loads(json_1best)
    return json_1best or {}


def words_from_json_1best(json_1best):
    json_1best = json_1best_to_dict(json_1best)
    words = []
    st = json_1best.get("st", {})
    for rt_item in st.get("rt", []):
        for ws_item in rt_item.get("ws", []):
            cw_items = ws_item.get("cw", [])
            if not cw_items:
                continue
            word = cw_items[0].get("w", "")
            if word:
                words.append(word)
    return "".join(words)


def speaker_key(item, json_1best):
    json_1best = json_1best_to_dict(json_1best)
    st = json_1best.get("st", {})
    return (
        item.get("spk")
        or st.get("rl")
        or st.get("pa")
        or item.get("role")
        or item.get("lid")
        or "0"
    )


def format_timestamp(value):
    if value is None or value == "":
        return "00:00:00"
    try:
        total_seconds = int(float(value) / 1000.0)
    except (TypeError, ValueError):
        return "00:00:00"
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)


def segment_time_values(item, json_1best):
    json_1best = json_1best_to_dict(json_1best)
    st = json_1best.get("st", {})
    begin = item.get("begin")
    end = item.get("end")
    if begin is None or begin == "":
        begin = st.get("bg")
    if end is None or end == "":
        end = st.get("ed")
    return begin, end


def extract_segments(order_result):
    parsed = parse_order_result(order_result)
    segments = []
    role_labels = {}
    for item in parsed.get("lattice", []):
        json_1best = item.get("json_1best")
        if not json_1best:
            continue
        text = words_from_json_1best(json_1best)
        if not text:
            continue
        role_key = str(speaker_key(item, json_1best))
        if role_key not in role_labels:
            role_labels[role_key] = "说话人{}".format(len(role_labels) + 1)
        role_label = role_labels[role_key]
        begin, end = segment_time_values(item, json_1best)
        time_range = "{} – {}".format(format_timestamp(begin), format_timestamp(end))
        segments.append(
            {
                "begin": begin,
                "end": end,
                "time_range": time_range,
                "speaker": role_key,
                "role": role_label,
                "text": text,
                "line": "[{}] {}：{}".format(time_range, role_label, text),
            }
        )
    return parsed, segments


def write_docx(path, title, paragraphs):
    document_parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        "<w:body>",
        (
            "<w:p><w:r><w:rPr><w:b/><w:sz w:val=\"32\"/></w:rPr>"
            "<w:t>{}</w:t></w:r></w:p>"
        ).format(escape(title)),
    ]
    for paragraph in paragraphs:
        if paragraph:
            document_parts.append(
                '<w:p><w:r><w:t xml:space="preserve">{}</w:t></w:r></w:p>'.format(
                    escape(paragraph)
                )
            )
    document_parts.append(
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
        "</w:sectPr></w:body></w:document>"
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        docx.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        docx.writestr("word/document.xml", "".join(document_parts))


def save_outputs(output_root, audio_meta, api_result):
    date_dir = Path(output_root).expanduser().resolve() / datetime.now().strftime("%Y%m%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    parsed_order_result, segments = extract_segments(
        api_result.get("content", {}).get("orderResult", "")
    )
    text_lines = [segment["line"] for segment in segments]
    text = "\n".join(text_lines)

    base_path = date_dir / audio_meta["new_file_name"]
    txt_path = Path(str(base_path) + ".txt")
    json_path = Path(str(base_path) + ".json")
    docx_path = Path(str(base_path) + ".docx")

    txt_path.write_text(text + ("\n" if text else ""), encoding="utf-8")
    json_payload = {
        "audio": audio_meta,
        "api_result": api_result,
        "order_result": parsed_order_result,
        "segments": segments,
        "text": text,
    }
    json_path.write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_docx(docx_path, audio_meta["new_file_name"], text_lines)

    return {
        "txt": str(txt_path),
        "json": str(json_path),
        "docx": str(docx_path),
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description="讯飞录音文件转写并导出 txt/json/docx")
    parser.add_argument("audio_file", help="待转写音频文件")
    parser.add_argument("--appid", default=os.environ.get("XFYUN_APPID", DEFAULT_APPID))
    parser.add_argument(
        "--secret-key",
        default=os.environ.get("XFYUN_SECRET_KEY", DEFAULT_SECRET_KEY),
        help="讯飞 secret_key，也可用 XFYUN_SECRET_KEY 环境变量",
    )
    parser.add_argument("--output-root", default="output", help="输出根目录")
    parser.add_argument(
        "--result-type",
        default="transfer",
        help="查询结果类型，默认只取 transfer；如已开通质检可传 transfer,predict",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    audio_meta = ensure_wav_file(args.audio_file)
    print("转写文件: {}".format(audio_meta["wav_path"]))

    api = RequestApi(
        appid=args.appid,
        secret_key=args.secret_key,
        upload_file_path=audio_meta["wav_path"],
        result_type=args.result_type,
    )
    api_result = api.get_result()
    output_paths = save_outputs(args.output_root, audio_meta, api_result)
    print("输出完成:")
    for kind, path in output_paths.items():
        print("{}: {}".format(kind, path))


if __name__ == "__main__":
    main()

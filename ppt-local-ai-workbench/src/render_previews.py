from __future__ import annotations

import math
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont, ImageStat


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
PREVIEW = ROOT / "scratch" / "previews"
PPTX = OUT / "本地AI工作台宣传.pptx"

W, H = 1920, 1080
C = {
    "bg": "#08121F",
    "bg2": "#0C1B2B",
    "ink": "#F7FAFC",
    "muted": "#A9B9C8",
    "cyan": "#38D5FF",
    "mint": "#67F2B0",
    "lime": "#C8FF5A",
    "orange": "#FFB45C",
    "pink": "#FF6FAE",
    "blue": "#6C8CFF",
    "line": "#24445F",
    "panel": "#102338",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size, index=0)
    return ImageFont.load_default()


F = {
    "label": font(20),
    "body": font(30),
    "small": font(24),
    "title": font(60, True),
    "hero": font(86, True),
    "num": font(82, True),
}


def wrap(text: str, fnt: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        buf = ""
        for ch in para:
            if fnt.getlength(buf + ch) <= width:
                buf += ch
            else:
                if buf:
                    lines.append(buf)
                buf = ch
        if buf:
            lines.append(buf)
    return lines


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt, fill, width=None, line_gap=10):
    x, y = xy
    lines = wrap(text, fnt, width) if width else text.split("\n")
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + line_gap


def bg(alt=False) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), C["bg2"] if alt else C["bg"])
    d = ImageDraw.Draw(img)
    d.arc((1420, -170, 2120, 530), 105, 335, fill=C["cyan"], width=3)
    d.arc((-160, 710, 500, 1370), 35, 260, fill=C["mint"], width=3)
    d.line((88, 1000, 1832, 1000), fill=C["line"], width=2)
    return img, d


def footer(d: ImageDraw.ImageDraw, n: int):
    d.text((88, 1016), "LOCAL AI WORKBENCH", font=F["label"], fill=C["muted"])
    d.text((1780, 1016), f"{n:02d}", font=F["label"], fill=C["muted"])


def title(d, txt, sub, n, y=110):
    draw_text(d, (104, y), txt, F["title"], C["ink"], 980, 8)
    if sub:
        draw_text(d, (108, y + 112), sub, F["small"], C["muted"], 880, 8)
    footer(d, n)


def pill(d, xy, text, color):
    x, y, w, h = xy
    d.rounded_rectangle((x, y, x + w, y + h), radius=18, outline=color, fill=C["panel"], width=2)
    d.text((x + 24, y + 15), text, font=F["small"], fill=C["ink"])


def node(d, xy, text, sub, color):
    x, y, w, h = xy
    d.rounded_rectangle((x, y, x + w, y + h), radius=16, outline=color, fill=C["panel"], width=3)
    d.ellipse((x + 22, y + 31, x + 48, y + 57), fill=color)
    d.text((x + 70, y + 22), text, font=F["body"], fill=C["ink"])
    if sub:
        draw_text(d, (x + 70, y + 70), sub, F["small"], C["muted"], w - 100, 5)


def arrow(d, a, b, color):
    d.line((a, b), fill=color, width=4)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    p1 = (b[0] - 18 * math.cos(ang - 0.45), b[1] - 18 * math.sin(ang - 0.45))
    p2 = (b[0] - 18 * math.cos(ang + 0.45), b[1] - 18 * math.sin(ang + 0.45))
    d.polygon([b, p1, p2], fill=color)


def make_slide(i: int) -> Image.Image:
    img, d = bg(i in {4, 8})
    if i == 1:
        d.text((108, 120), "LOCAL AI WORKBENCH", font=F["label"], fill=C["mint"])
        draw_text(d, (108, 218), "本地 AI 工作台", F["hero"], C["ink"], 860, 16)
        draw_text(d, (118, 466), "把微信、文件、语音、图片和本地模型连成一个私有知识闭环。", F["body"], C["muted"], 760, 12)
        for k, item in enumerate(["OpenClaw", "MLX 本地模型", "Paperless-ngx", "DeepSeek"]):
            pill(d, (118 + k * 250, 650, 220, 64), item, [C["mint"], C["cyan"], C["orange"], C["lime"]][k])
        for k, (name, c) in enumerate([("采集", C["mint"]), ("理解", C["orange"]), ("沉淀", C["cyan"]), ("检索", C["lime"])]):
            x = 1220 + math.cos(k * math.pi / 2 + .5) * 210
            y = 450 + math.sin(k * math.pi / 2 + .5) * 210
            d.ellipse((x - 58, y - 58, x + 58, y + 58), fill=c)
            d.text((x - 35, y - 17), name, font=F["small"], fill=C["bg"])
        footer(d, 1)
    elif i == 2:
        title(d, "信息散落，知识就会变慢", "微信、文件夹、日志、图片和文档各自为政，检索和复用成本持续增加。", 2)
        items = [("语音转文字后不归档", C["orange"]), ("图片资料没有来源标记", C["cyan"]), ("日志/多媒体误入知识库", C["pink"]), ("模型入口和文档库割裂", C["mint"])]
        for k, (txt, c) in enumerate(items):
            node(d, (180 + (k % 2) * 760, 360 + (k // 2) * 220, 600, 135), txt, "需要自动化入口和统一规则", c)
    elif i == 3:
        title(d, "一台 Mac，形成私有 AI 闭环", "从输入、处理到沉淀尽量在本机完成，必要时再调用外部 DeepSeek。", 3)
        nodes = [("微信机器人", 170, 400, C["mint"]), ("n8n 工作流", 470, 270, C["orange"]), ("ASR / OCR", 820, 400, C["cyan"]), ("Paperless", 1130, 270, C["lime"]), ("本地模型", 1430, 400, C["blue"])]
        for name, x, y, c in nodes:
            node(d, (x, y, 230, 120), name, "", c)
        for a, b, c in [((400, 460), (470, 330), C["mint"]), ((700, 330), (820, 460), C["orange"]), ((1050, 460), (1130, 330), C["cyan"]), ((1360, 330), (1430, 460), C["lime"])]:
            arrow(d, a, b, c)
    elif i == 4:
        title(d, "标准化数据流", "目录约定、消费规则、来源字段，让新增资料自动进入正确位置。", 4)
        steps = [("输入目录", "微信、扫描件、办公文档", C["mint"]), ("过滤消费", "docx / excel / txt / pdf / 图片", C["orange"]), ("智能标记", "来源=音频 / 图片 / 文档", C["cyan"]), ("检索问答", "Paperless + 本地模型", C["lime"])]
        for k, (a, b, c) in enumerate(steps):
            node(d, (180 + k * 420, 430, 320, 145), a, b, c)
            if k < 3:
                arrow(d, (500 + k * 420, 503), (590 + k * 420, 503), c)
    elif i == 5:
        title(d, "本地模型分层", "轻量模型负责日常响应，大模型负责推理场景，DeepSeek 作为可选云端增强。", 5)
        tiers = [("Qwen3-4B", "快速问答 / 低成本常驻", C["mint"]), ("deepseek-r170b", "本地 70B 推理能力", C["cyan"]), ("DeepSeek API", "复杂任务外部增强", C["orange"])]
        for k, (a, b, c) in enumerate(tiers):
            x, y, w, h = 260 + k * 470, 360, 360, 260
            d.rounded_rectangle((x, y, x + w, y + h), 18, fill=C["panel"], outline=c, width=3)
            d.text((x + 34, y + 42), a, font=F["body"], fill=c)
            draw_text(d, (x + 34, y + 100), b, F["small"], C["ink"], 280, 8)
    elif i == 6:
        title(d, "Paperless 变成主动归档层", "消费时识别资料类型，不让语音、视频和 .log 噪声污染文档库。", 6)
        rows = [("音频转写稿", "来源：音频", C["orange"]), ("图片 / 扫描件", "来源：图片", C["cyan"]), ("docx / excel / txt", "来源：文档", C["mint"]), ("视频 / 语音 / .log", "不消费", C["pink"])]
        for k, (a, b, c) in enumerate(rows):
            y = 300 + k * 145
            d.rounded_rectangle((260, y, 1570, y + 88), 12, fill=C["panel"], outline=C["line"], width=2)
            d.text((300, y + 25), a, font=F["body"], fill=C["ink"])
            d.text((1280, y + 25), b, font=F["body"], fill=c)
    elif i == 7:
        title(d, "不是又一个工具，而是工作方式升级", "从资料收集到可搜索知识库，减少重复劳动，把注意力还给判断。", 7)
        vals = [("更快沉淀", "微信语音自动转写成文档。", C["mint"]), ("更好检索", "OCR、全文检索和来源筛选。", C["cyan"]), ("更可控", "本地模型和本地目录优先。", C["orange"]), ("更可扩展", "n8n 与 OpenAI 兼容接口。", C["lime"])]
        for k, (a, b, c) in enumerate(vals):
            x, y = (210 if k % 2 == 0 else 980), (330 if k < 2 else 620)
            d.text((x, y), a, font=F["title"], fill=c)
            d.line((x, y + 92, x + 125, y + 92), fill=c, width=5)
            draw_text(d, (x, y + 125), b, F["body"], C["ink"], 600, 8)
    elif i == 8:
        d.text((112, 118), "FROM FILES TO KNOWLEDGE", font=F["label"], fill=C["orange"])
        draw_text(d, (112, 220), "让每一条语音、\n每一张图片、\n每一份文档，\n都自动进入知识库。", F["title"], C["ink"], 760, 12)
        draw_text(d, (120, 710), "下一步：接入更多输入源、完善 n8n 工作流、把 Paperless 检索和本地模型问答合并成一个日常入口。", F["body"], C["muted"], 780, 10)
        loop = [("输入", 1270, 250, C["mint"]), ("处理", 1510, 430, C["orange"]), ("理解", 1430, 705, C["cyan"]), ("检索", 1100, 700, C["lime"]), ("沉淀", 1040, 420, C["blue"])]
        for k, (_, x, y, c) in enumerate(loop):
            nx, ny = loop[(k + 1) % len(loop)][1:3]
            arrow(d, (x, y), (nx, ny), c)
        for name, x, y, c in loop:
            d.ellipse((x - 54, y - 54, x + 54, y + 54), fill=c)
            d.text((x - 32, y - 16), name, font=F["small"], fill=C["bg"])
        footer(d, 8)
    return img


def inspect_pptx() -> tuple[int, int, list[str]]:
    if not PPTX.exists():
        raise FileNotFoundError(PPTX)
    with zipfile.ZipFile(PPTX) as zf:
        slides = sorted(n for n in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n))
        texts: list[str] = []
        for name in slides:
            root = ET.fromstring(zf.read(name))
            for el in root.iter():
                if el.tag.endswith("}t") and el.text:
                    texts.append(el.text)
    placeholders = [t for t in texts if "TODO" in t or "PLACEHOLDER" in t]
    return len(slides), len(texts), placeholders


def main() -> int:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    files = []
    for i in range(1, 9):
        img = make_slide(i)
        p = PREVIEW / f"slide_{i:02d}.png"
        img.save(p)
        files.append(p)

    sheet = Image.new("RGB", (W, H), C["bg"])
    thumbs = [Image.open(p).resize((456, 256)) for p in files]
    d = ImageDraw.Draw(sheet)
    for idx, thumb in enumerate(thumbs):
        x = 24 + (idx % 4) * 474
        y = 56 + (idx // 4) * 450
        sheet.paste(thumb, (x, y))
        d.text((x, y + 270), f"Slide {idx + 1:02d}", font=F["small"], fill=C["muted"])
    contact = PREVIEW / "contact_sheet.png"
    sheet.save(contact)

    slide_count, text_count, placeholders = inspect_pptx()
    blank = []
    for p in [*files, contact]:
        stat = ImageStat.Stat(Image.open(p).convert("L"))
        if stat.stddev[0] < 1.5:
            blank.append(str(p))

    print(f"pptx={PPTX}")
    print(f"pptx_slide_count={slide_count}")
    print(f"pptx_text_runs={text_count}")
    print(f"placeholder_count={len(placeholders)}")
    print(f"preview_count={len(files)}")
    print(f"contact_sheet={contact}")
    print(f"blank_png_count={len(blank)}")
    if slide_count != 8 or placeholders or blank:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

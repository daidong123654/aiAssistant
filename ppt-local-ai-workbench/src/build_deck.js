import pptxgen from "/Users/jianfeisu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs/dist/pptxgen.es.js";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const outDir = path.join(__dirname, "..", "output");
fs.mkdirSync(outDir, { recursive: true });

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Codex";
pptx.subject = "本地 AI 工作台宣传介绍";
pptx.title = "本地 AI 工作台";
pptx.company = "Local AI Workbench";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "PingFang SC",
  bodyFontFace: "PingFang SC",
  lang: "zh-CN",
};
pptx.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pptx.layout = "WIDE";

const W = 13.333;
const H = 7.5;
const C = {
  bg: "08121F",
  bg2: "0C1B2B",
  ink: "F7FAFC",
  muted: "A9B9C8",
  cyan: "38D5FF",
  mint: "67F2B0",
  lime: "C8FF5A",
  orange: "FFB45C",
  pink: "FF6FAE",
  blue: "6C8CFF",
  line: "24445F",
  panel: "102338",
};

function addBg(slide, opts = {}) {
  slide.background = { color: C.bg };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: W, h: H, fill: { color: C.bg }, line: { color: C.bg } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: W, h: H, fill: { color: opts.alt ? C.bg2 : C.bg, transparency: 0 }, line: { color: opts.alt ? C.bg2 : C.bg } });
  slide.addShape(pptx.ShapeType.arc, { x: 9.9, y: -1.0, w: 4.8, h: 4.8, adjustPoint: 0.18, line: { color: C.cyan, transparency: 58, width: 1.2 }, rotate: 20 });
  slide.addShape(pptx.ShapeType.arc, { x: -1.0, y: 4.9, w: 4.2, h: 4.2, adjustPoint: 0.25, line: { color: C.mint, transparency: 68, width: 1.0 }, rotate: 210 });
  slide.addShape(pptx.ShapeType.line, { x: 0.6, y: 6.95, w: 12.2, h: 0, line: { color: C.line, transparency: 20, width: 0.8 } });
}

function label(slide, txt, x, y, color = C.mint) {
  slide.addText(txt, { x, y, w: 3.2, h: 0.22, fontFace: "Avenir Next", fontSize: 7.5, charSpace: 1.6, color, bold: true, margin: 0 });
}

function title(slide, t, st, y = 0.74) {
  slide.addText(t, { x: 0.72, y, w: 7.4, h: 0.82, fontSize: 27, bold: true, color: C.ink, margin: 0, breakLine: false, fit: "shrink" });
  if (st) slide.addText(st, { x: 0.75, y: y + 0.74, w: 6.7, h: 0.42, fontSize: 10.5, color: C.muted, margin: 0, fit: "shrink" });
}

function footer(slide, n) {
  slide.addText(String(n).padStart(2, "0"), { x: 12.1, y: 6.78, w: 0.45, h: 0.2, fontFace: "Avenir Next", fontSize: 8, color: C.muted, margin: 0, align: "right" });
  slide.addText("LOCAL AI WORKBENCH", { x: 0.72, y: 6.78, w: 2.2, h: 0.2, fontFace: "Avenir Next", fontSize: 7.2, charSpace: 1.4, color: C.muted, margin: 0 });
}

function pill(slide, txt, x, y, w, color) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h: 0.38, rectRadius: 0.08, fill: { color, transparency: 80 }, line: { color, transparency: 25, width: 1 } });
  slide.addText(txt, { x: x + 0.13, y: y + 0.095, w: w - 0.26, h: 0.14, fontSize: 7.6, bold: true, color: C.ink, margin: 0, fit: "shrink" });
}

function node(slide, txt, x, y, w, color, sub) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h: sub ? 0.76 : 0.54, rectRadius: 0.06, fill: { color: C.panel, transparency: 4 }, line: { color, transparency: 10, width: 1.1 } });
  slide.addShape(pptx.ShapeType.ellipse, { x: x + 0.12, y: y + 0.16, w: 0.18, h: 0.18, fill: { color }, line: { color } });
  slide.addText(txt, { x: x + 0.42, y: y + 0.14, w: w - 0.58, h: 0.18, fontSize: 9.2, bold: true, color: C.ink, margin: 0, fit: "shrink" });
  if (sub) slide.addText(sub, { x: x + 0.42, y: y + 0.42, w: w - 0.58, h: 0.18, fontSize: 6.8, color: C.muted, margin: 0, fit: "shrink" });
}

function arrow(slide, x1, y1, x2, y2, color = C.cyan) {
  slide.addShape(pptx.ShapeType.line, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color, width: 1.35, beginArrowType: "none", endArrowType: "triangle" } });
}

function bigNumber(slide, num, labelText, x, y, color) {
  slide.addText(num, { x, y, w: 1.28, h: 0.72, fontFace: "Avenir Next", fontSize: 34, bold: true, color, margin: 0 });
  slide.addText(labelText, { x: x + 1.18, y: y + 0.22, w: 2.4, h: 0.25, fontSize: 9.4, color: C.ink, bold: true, margin: 0, fit: "shrink" });
}

// 1. Cover
{
  const s = pptx.addSlide();
  addBg(s);
  label(s, "PRIVATE AI OPERATING SYSTEM", 0.75, 0.66, C.mint);
  s.addText("本地 AI\n工作台", { x: 0.72, y: 1.28, w: 5.0, h: 1.95, fontSize: 44, bold: true, color: C.ink, margin: 0, breakLine: false, fit: "shrink" });
  s.addText("把微信语音、图片、文档和本地大模型接进同一个可控闭环。", { x: 0.76, y: 3.62, w: 4.78, h: 0.52, fontSize: 15.5, color: C.muted, margin: 0, fit: "shrink" });
  pill(s, "MLX", 0.78, 4.48, 0.84, C.cyan);
  pill(s, "OpenClaw", 1.78, 4.48, 1.26, C.mint);
  pill(s, "n8n", 3.21, 4.48, 0.78, C.orange);
  pill(s, "Paperless-ngx", 4.15, 4.48, 1.64, C.blue);
  const cx = 9.25, cy = 3.52;
  s.addShape(pptx.ShapeType.ellipse, { x: cx - 1.35, y: cy - 1.35, w: 2.7, h: 2.7, fill: { color: "0E2134" }, line: { color: C.cyan, width: 1.4, transparency: 15 } });
  s.addText("AI", { x: cx - 0.48, y: cy - 0.42, w: 0.96, h: 0.5, fontFace: "Avenir Next", fontSize: 24, bold: true, color: C.ink, align: "center", margin: 0 });
  const pts = [
    [7.0, 1.35, "微信", C.mint], [11.3, 1.52, "文档", C.blue], [11.75, 5.25, "检索", C.lime],
    [6.95, 5.55, "模型", C.orange], [9.2, 0.92, "自动化", C.pink], [9.05, 6.28, "归档", C.cyan],
  ];
  pts.forEach(([x, y, t, c]) => {
    s.addShape(pptx.ShapeType.line, { x: cx, y: cy, w: x - cx + 0.22, h: y - cy + 0.12, line: { color: c, transparency: 35, width: 1 } });
    s.addShape(pptx.ShapeType.ellipse, { x, y, w: 0.44, h: 0.44, fill: { color: c }, line: { color: c } });
    s.addText(t, { x: x - 0.26, y: y + 0.52, w: 1.0, h: 0.18, fontSize: 7.5, color: C.muted, align: "center", margin: 0 });
  });
  s.addText("宣传介绍 · 2026", { x: 0.76, y: 6.72, w: 2.0, h: 0.22, fontSize: 8.5, color: C.muted, margin: 0 });
}

// 2. Pain
{
  const s = pptx.addSlide();
  addBg(s, { alt: true });
  title(s, "信息散落，知识就会变慢", "语音、图片、文档、模型和自动化工具各自为政，最终让检索和复用变成体力活。");
  const lanes = [
    ["微信语音", "聊天里沉没", C.mint],
    ["会议录音", "只剩文件名", C.orange],
    ["本地文档", "没有统一入口", C.blue],
  ];
  lanes.forEach((l, i) => {
    const y = 2.25 + i * 1.13;
    node(s, l[0], 0.9, y, 2.2, l[2], l[1]);
    arrow(s, 3.28, y + 0.38, 6.2, y + 0.38, l[2]);
    s.addText("无法自动归档 / 难以全文检索 / 缺少来源标签", { x: 6.55, y: y + 0.18, w: 4.7, h: 0.22, fontSize: 10.2, color: C.ink, margin: 0 });
  });
  s.addText("痛点不是模型不够强，而是信息没有进入同一条流水线。", { x: 0.9, y: 6.02, w: 8.0, h: 0.34, fontSize: 16, bold: true, color: C.lime, margin: 0 });
  footer(s, 2);
}

// 3. One machine loop
{
  const s = pptx.addSlide();
  addBg(s);
  title(s, "一台 Mac，形成私有 AI 闭环", "从接收、处理、归档到检索，全链路在本机可观察、可替换、可扩展。");
  const steps = [
    ["接收", "OpenClaw / n8n", C.mint],
    ["处理", "ASR / 清洗 / 任务记录", C.orange],
    ["理解", "MLX 本地模型", C.cyan],
    ["沉淀", "Paperless-ngx", C.blue],
    ["复用", "全文检索 / 来源分类", C.lime],
  ];
  steps.forEach((st, i) => {
    const x = 0.75 + i * 2.48;
    node(s, st[0], x, 3.05, 1.72, st[2], st[1]);
    if (i < steps.length - 1) arrow(s, x + 1.84, 3.43, x + 2.36, 3.43, st[2]);
  });
  bigNumber(s, "5", "核心环节串成闭环", 1.05, 5.48, C.cyan);
  bigNumber(s, "3", "来源自动分类", 4.45, 5.48, C.mint);
  bigNumber(s, "1", "本地工作台统一承载", 7.85, 5.48, C.orange);
  footer(s, 3);
}

// 4. Architecture
{
  const s = pptx.addSlide();
  addBg(s, { alt: true });
  title(s, "架构不是堆工具，而是标准化数据流", "每个组件只负责一件事：接收、编排、转写、理解、归档。");
  node(s, "微信 / 文件", 0.9, 2.0, 1.65, C.mint, "语音、图片、文档");
  node(s, "OpenClaw", 3.0, 1.55, 1.65, C.cyan, "消息入口");
  node(s, "n8n", 3.0, 2.78, 1.65, C.orange, "编排与通知");
  node(s, "kb API", 5.2, 2.18, 1.65, C.lime, "任务提交");
  node(s, "ASR 流水线", 7.35, 1.55, 1.85, C.pink, "转写 / 文档化");
  node(s, "MLX 模型", 7.35, 2.78, 1.85, C.cyan, "摘要 / 纪要");
  node(s, "Paperless", 10.0, 2.18, 1.95, C.blue, "归档 / OCR / 检索");
  arrow(s, 2.56, 2.32, 2.95, 1.88, C.mint);
  arrow(s, 2.56, 2.32, 2.95, 3.12, C.mint);
  arrow(s, 4.75, 2.0, 5.15, 2.42, C.cyan);
  arrow(s, 4.75, 3.12, 5.15, 2.58, C.orange);
  arrow(s, 6.92, 2.42, 7.28, 1.92, C.lime);
  arrow(s, 6.92, 2.58, 7.28, 3.12, C.lime);
  arrow(s, 9.32, 1.92, 9.9, 2.42, C.pink);
  arrow(s, 9.32, 3.12, 9.9, 2.58, C.cyan);
  s.addText("data/src → jobs → archive → dst", { x: 2.0, y: 5.58, w: 4.8, h: 0.36, fontFace: "Avenir Next", fontSize: 16, bold: true, color: C.ink, margin: 0 });
  s.addText("统一目录约定让任务可追踪、可重跑、可排障。", { x: 2.02, y: 6.02, w: 5.0, h: 0.22, fontSize: 9.5, color: C.muted, margin: 0 });
  footer(s, 4);
}

// 5. Model tier
{
  const s = pptx.addSlide();
  addBg(s);
  title(s, "本地模型分层：轻任务快跑，重任务深算", "同一个 OpenAI 兼容接口风格，按任务成本选择不同模型。");
  const tiers = [
    ["1.5B", "9080", "轻量分类 / 短摘要", C.mint],
    ["27B", "9081", "日常问答 / 一般摘要", C.orange],
    ["70B", "9082", "会议纪要 / 深度分析", C.cyan],
  ];
  tiers.forEach((t, i) => {
    const x = 1.0 + i * 4.05;
    s.addShape(pptx.ShapeType.line, { x, y: 5.45 - i * 0.78, w: 2.85, h: 0, line: { color: t[3], width: 8, transparency: 15 } });
    s.addText(t[0], { x, y: 2.1 + i * 0.12, w: 2.1, h: 0.65, fontFace: "Avenir Next", fontSize: 34, bold: true, color: t[3], margin: 0 });
    s.addText(`:${t[1]}`, { x: x + 1.54, y: 2.43 + i * 0.12, w: 1.0, h: 0.18, fontFace: "Avenir Next", fontSize: 10, color: C.muted, margin: 0 });
    s.addText(t[2], { x, y: 3.15, w: 2.6, h: 0.44, fontSize: 12.5, bold: true, color: C.ink, margin: 0, fit: "shrink" });
    s.addText("OpenAI-compatible / MLX / 本机运行", { x, y: 3.72, w: 2.82, h: 0.18, fontSize: 7.5, color: C.muted, margin: 0 });
  });
  s.addText("统一测试问题：地球到太阳的距离是多少？", { x: 0.98, y: 6.1, w: 4.4, h: 0.28, fontSize: 11.5, color: C.lime, bold: true, margin: 0 });
  footer(s, 5);
}

// 6. Paperless intelligence
{
  const s = pptx.addSlide();
  addBg(s, { alt: true });
  title(s, "文档库不只存文件，还自动理解来源", "Paperless-ngx 负责归档、OCR 和检索，消费脚本负责给每个新文档打上来源标签。");
  node(s, "音频转写", 1.1, 2.25, 2.2, C.mint, "_asr / 语音 / voice");
  node(s, "图片资料", 1.1, 3.45, 2.2, C.orange, "image / scan / 图片");
  node(s, "文字文档", 1.1, 4.65, 2.2, C.blue, "txt / docx / xlsx / pdf");
  arrow(s, 3.48, 2.62, 5.0, 3.38, C.mint);
  arrow(s, 3.48, 3.82, 5.0, 3.58, C.orange);
  arrow(s, 3.48, 5.02, 5.0, 3.78, C.blue);
  s.addShape(pptx.ShapeType.roundRect, { x: 5.35, y: 2.58, w: 2.55, h: 1.55, rectRadius: 0.08, fill: { color: "132A42" }, line: { color: C.cyan, width: 1.2 } });
  s.addText("来源", { x: 5.72, y: 2.92, w: 1.85, h: 0.26, fontSize: 16, bold: true, color: C.ink, align: "center", margin: 0 });
  s.addText("音频  /  图片  /  文档", { x: 5.62, y: 3.42, w: 2.0, h: 0.18, fontSize: 8.5, color: C.muted, align: "center", margin: 0 });
  arrow(s, 8.05, 3.38, 9.4, 3.38, C.cyan);
  node(s, "可检索资产", 9.65, 3.02, 2.45, C.lime, "全文检索 / 来源筛选 / 长期沉淀");
  s.addText("自动跳过音频、视频、日志、JSON 等噪声文件，保留真正进入知识库的内容。", { x: 1.12, y: 6.08, w: 7.9, h: 0.24, fontSize: 10.8, color: C.muted, margin: 0 });
  footer(s, 6);
}

// 7. Value
{
  const s = pptx.addSlide();
  addBg(s);
  title(s, "它带来的不是“又一个工具”，而是工作方式升级", "个人和小团队都能用一套可控系统，把分散素材变成可复用的知识资产。");
  const vals = [
    ["更快沉淀", "微信语音自动转写成文档，不再手工搬运。", C.mint],
    ["更好检索", "Paperless 统一归档、OCR、全文检索和来源筛选。", C.cyan],
    ["更可控", "本地模型、本地目录、本地服务，敏感资料少外流。", C.orange],
    ["更可扩展", "n8n、OpenAI 兼容接口和清晰目录约定方便接新流程。", C.lime],
  ];
  vals.forEach((v, i) => {
    const x = i % 2 === 0 ? 1.0 : 6.7;
    const y = i < 2 ? 2.18 : 4.28;
    s.addText(v[0], { x, y, w: 2.0, h: 0.3, fontSize: 18, bold: true, color: v[2], margin: 0 });
    s.addShape(pptx.ShapeType.line, { x, y: y + 0.48, w: 0.78, h: 0, line: { color: v[2], width: 2 } });
    s.addText(v[1], { x, y: y + 0.78, w: 4.35, h: 0.46, fontSize: 11.5, color: C.ink, margin: 0, fit: "shrink" });
  });
  footer(s, 7);
}

// 8. Closing
{
  const s = pptx.addSlide();
  addBg(s, { alt: true });
  label(s, "FROM FILES TO KNOWLEDGE", 0.76, 0.82, C.orange);
  s.addText("让每一条语音、\n每一张图片、\n每一份文档，\n都自动进入知识库。", { x: 0.78, y: 1.42, w: 5.3, h: 2.6, fontSize: 31, bold: true, color: C.ink, margin: 0, fit: "shrink" });
  s.addText("下一步：接入更多输入源、完善 n8n 工作流、把 Paperless 检索和本地模型问答合并成一个日常入口。", { x: 0.82, y: 4.6, w: 5.5, h: 0.52, fontSize: 13.8, color: C.muted, margin: 0, fit: "shrink" });
  const loop = [
    ["输入", 8.8, 1.15, C.mint],
    ["处理", 10.65, 2.35, C.orange],
    ["理解", 10.25, 4.65, C.cyan],
    ["检索", 7.95, 4.88, C.lime],
    ["沉淀", 7.28, 2.55, C.blue],
  ];
  loop.forEach(([t, x, y, c], i) => {
    s.addShape(pptx.ShapeType.ellipse, { x, y, w: 0.76, h: 0.76, fill: { color: c }, line: { color: c } });
    s.addText(t, { x: x - 0.12, y: y + 0.96, w: 1.0, h: 0.2, fontSize: 8.8, bold: true, color: C.ink, align: "center", margin: 0 });
    const next = loop[(i + 1) % loop.length];
    arrow(s, x + 0.38, y + 0.38, next[1] + 0.38, next[2] + 0.38, c);
  });
  footer(s, 8);
}

await Promise.all([
  pptx.writeFile({ fileName: path.join(outDir, "本地AI工作台宣传.pptx") }),
  pptx.writeFile({ fileName: path.join(outDir, "output.pptx") }),
]);

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Markdown → 微信公众号排版 HTML(内联样式)。粘贴进公众号编辑器直接就是成品样式。零依赖, Python 3.8+。

为什么需要: 公众号编辑器不认 Markdown, 直接粘贴会原样显示 # 和 **; 编辑器也会剥掉 <style> 和 class,
只保留行内 style —— 所以这里把每个元素的样式都写成内联。
支持: # 标题(作为文章标题, 不进正文) / ## ### / 段落 / **加粗** / > 引用(浅底提示框) / - 无序 / 1. 有序 /
      | 表格 | / ---(忽略) / 文末「不构成…建议」类引用自动改成灰色小字。
插图: --fig "锚点文字=>图片文件名=>图注", 插在第一个包含锚点文字的块之后; 可重复。锚点找不到会报错。

用法:
  python3 wechat_format.py article.md out/ --digest "摘要" [--cover cover.png] [--fig "锚点=>fig1.png=>图 1：……"] [--accent "#00809f"]
产物: out/article.html(正文片段) 与 out/index.html(预览页 + 「复制正文（含排版）」按钮 + 素材下载链接)。
"""
import argparse, html, os, re

C = {"text": "#2b3640", "head": "#14222e", "accent": "#00809f", "muted": "#7b8a96", "tipbg": "#f2f8fa", "tip": "#3b4c58"}
def _styles():
    return {
        "p": f"margin:0 0 18px;font-size:16px;line-height:1.85;color:{C['text']};letter-spacing:.3px;text-align:justify",
        "h2": f"margin:34px 0 16px;padding-left:12px;border-left:4px solid {C['accent']};font-size:19px;font-weight:700;line-height:1.5;color:{C['head']}",
        "h3": f"margin:24px 0 12px;font-size:17px;font-weight:700;line-height:1.5;color:{C['head']}",
        "tip": f"margin:0 0 18px;padding:12px 16px;background:{C['tipbg']};border-left:3px solid {C['accent']};border-radius:4px;font-size:15px;line-height:1.8;color:{C['tip']}",
        "ul": "margin:0 0 18px;padding-left:20px",
        "li": f"margin:0 0 10px;font-size:16px;line-height:1.8;color:{C['text']}",
        "small": f"margin:0 0 12px;font-size:13px;line-height:1.75;color:{C['muted']}",
        "cap": f"margin:-8px 0 22px;text-align:center;font-size:13px;color:{C['muted']}",
        "table": "width:100%;border-collapse:collapse;margin:0 0 20px;font-size:14px",
        "th": f"padding:8px 6px;background:{C['tipbg']};border:1px solid #d9e3e8;color:{C['head']};font-weight:700;text-align:center",
        "td": f"padding:8px 6px;border:1px solid #d9e3e8;color:{C['text']};text-align:center",
    }


S = _styles()


def set_accent(color):
    """换强调色(二级标题竖条、引用框边线), 如 #c0392b。"""
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color or ""):
        raise SystemExit("--accent 需要形如 #00809f 的颜色")
    C["accent"] = color
    S.update(_styles())


def inline(t):
    """`代码` 里的内容原样显示(先摘出来占位, 免得 `**x**` 被当成粗体), 再转义、处理粗体, 最后放回。"""
    codes = []
    t = re.sub(r"`([^`]+)`", lambda m: codes.append(m.group(1)) or f"\x00{len(codes) - 1}\x00", t)
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", lambda m: f"<strong style='color:{C['head']}'>{m.group(1)}</strong>", t)
    return re.sub(r"\x00(\d+)\x00", lambda m: html.escape(codes[int(m.group(1))], quote=False), t)


def blocks(md):
    """→ [(类型, 原文, html)] ; 类型用于锚点匹配与免责识别。"""
    lines = md.split("\n"); out = []; i = 0; title = None
    while i < len(lines):
        l = lines[i].rstrip()
        if not l.strip() or re.fullmatch(r"-{3,}", l.strip()):
            i += 1; continue
        if l.startswith("# ") and title is None:
            title = l[2:].strip(); i += 1; continue
        if l.startswith("## "):
            out.append(("h2", l[3:], f'<h2 style="{S["h2"]}">{inline(l[3:])}</h2>')); i += 1; continue
        if l.startswith("### "):
            out.append(("h3", l[4:], f'<h3 style="{S["h3"]}">{inline(l[4:])}</h3>')); i += 1; continue
        if l.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").strip()); i += 1
            txt = " ".join(buf)
            out.append(("quote", txt, f'<p style="{S["tip"]}">{inline(txt)}</p>')); continue
        if l.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            h = f'<table style="{S["table"]}"><tr>' + "".join(f'<th style="{S["th"]}">{inline(c)}</th>' for c in rows[0]) + "</tr>"
            h += "".join("<tr>" + "".join(f'<td style="{S["td"]}">{inline(c)}</td>' for c in r) + "</tr>" for r in rows[1:]) + "</table>"
            out.append(("table", " ".join(" ".join(r) for r in rows), h)); continue
        if re.match(r"\s*([-*]|\d+[.)])\s+", l):
            ordered = bool(re.match(r"\s*\d+[.)]\s+", l)); items = []
            while i < len(lines) and re.match(r"\s*([-*]|\d+[.)])\s+", lines[i]):
                items.append(re.sub(r"^\s*([-*]|\d+[.)])\s+", "", lines[i]).strip()); i += 1
            tag = "ol" if ordered else "ul"
            h = f'<{tag} style="{S["ul"]}">' + "".join(f'<li style="{S["li"]}">{inline(x)}</li>' for x in items) + f"</{tag}>"
            out.append(("list", " ".join(items), h)); continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#{1,3} |>|\||\s*([-*]|\d+[.)])\s+|-{3,}\s*$)", lines[i]):
            buf.append(lines[i].strip()); i += 1
        txt = "".join(buf)
        out.append(("p", txt, f'<p style="{S["p"]}">{inline(txt)}</p>'))
    return title, out


def build(md_path, outdir, digest, cover=None, figs=(), page="index.html"):
    md = open(md_path, encoding="utf-8").read()
    title, bl = blocks(md)
    parts, used = [], set()
    for k, (typ, raw, h) in enumerate(bl):
        last = k == len(bl) - 1
        if last and typ == "quote":   # 文末的引用(通常是免责声明/来源说明)改成灰色小字
            h = f'<p style="{S["small"]}">{inline(raw)}</p>'
        parts.append(h)
        for n, (anchor, fn, cap) in enumerate(figs):
            if n not in used and anchor in raw:
                used.add(n)
                parts.append(f"<section data-fig='{n + 1}' style='margin:6px 0 18px'><img src='{html.escape(fn)}' alt='{html.escape(cap)}' "
                             f"style='display:block;width:100%;border-radius:6px'></section><p style=\"{S['cap']}\">{html.escape(cap)}</p>")
    miss = [figs[n][0] for n in range(len(figs)) if n not in used]
    if miss:
        raise SystemExit(f"插图锚点没找到: {miss}")
    art = "\n".join(parts)
    os.makedirs(outdir, exist_ok=True)
    open(os.path.join(outdir, "article.html"), "w", encoding="utf-8").write(art)
    dl = " · ".join(([f"<a href='{html.escape(cover)}' download>封面</a>"] if cover else [])
                    + [f"<a href='{html.escape(fn)}' download>图{n + 1}</a>" for n, (_, fn, _) in enumerate(figs)])
    idx = f"""<!doctype html><html lang=zh><meta charset=utf-8><meta name=robots content=noindex><meta name=viewport content='width=device-width,initial-scale=1'><title>公众号排版 · {html.escape(title or '')}</title>
<body style='margin:0;background:#eef2f4;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif'><div style='max-width:760px;margin:0 auto;padding:20px'>
<div style='background:#fff;border-radius:10px;padding:18px 20px;margin-bottom:16px;font-size:14px;line-height:1.8;color:#2b3640'>
<b style='font-size:16px'>发布素材</b><br>标题：{html.escape(title or '')}<br>摘要：{html.escape(digest)}<br>
<button id=c style='margin:10px 8px 6px 0;padding:8px 14px;border:0;border-radius:6px;background:{C['accent']};color:#fff;font-size:14px;cursor:pointer'>复制正文（含排版）</button> {dl}
<div style='font-size:12.5px;color:#7b8a96;margin-top:6px'>点按钮后到公众号编辑器直接粘贴即为成品样式。插图在本地目录里, 编辑器读不到 —— 粘贴后在灰色图注上方把对应的图重新上传一次。</div></div>
<div id=t style='background:#fff;border-radius:10px;padding:26px 22px'>{art}</div></div>
<script>document.getElementById('c').onclick=async function(){{var h=document.getElementById('t').innerHTML;var d=document.createElement('div');d.innerHTML=h;
await navigator.clipboard.write([new ClipboardItem({{'text/html':new Blob([h],{{type:'text/html'}}),'text/plain':new Blob([d.innerText],{{type:'text/plain'}})}})]);this.textContent='已复制';}}</script></body></html>"""
    open(os.path.join(outdir, page), "w", encoding="utf-8").write(idx)
    return title, len(bl), len(figs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("md"); ap.add_argument("outdir"); ap.add_argument("--digest", required=True)
    ap.add_argument("--cover"); ap.add_argument("--fig", action="append", default=[])
    ap.add_argument("--page", default="index.html", help="排版页文件名(目录里已有 index.html 时另起名)")
    ap.add_argument("--accent", help="强调色, 如 #c0392b(默认 #00809f)")
    a = ap.parse_args()
    if a.accent:
        set_accent(a.accent)
    figs = [tuple(x.split("=>", 2)) for x in a.fig]
    t, nb, nf = build(a.md, a.outdir, a.digest, a.cover, figs, a.page)
    print(f"排版完成: {t} · {nb} 块 · 插图 {nf} 张 → {a.outdir}/{a.page}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯 Python 标准库 PDF 生成器
使用 weasyprint 将 Markdown 章节渲染为排版精美的 PDF
"""

import os
import re
import sys

# 添加 EPUB 脚本路径以复用 md_to_html_simple
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_epub import (
    md_to_html_simple,
    read_chapter,
    CHAPTERS,
    BOOK_TITLE,
    BOOK_AUTHOR,
    OUTPUT_DIR,
    CHAPS_DIR,
)

PDF_CSS = """
@page {
    size: A4;
    margin: 2.5cm 2cm 2.5cm 2cm;

    @bottom-center {
        content: "— " counter(page) " —";
        font-family: "PingFang SC", "Hiragino Sans GB", sans-serif;
        font-size: 9pt;
        color: #aaa;
    }
}

@page :first {
    @bottom-center { content: none; }
}

@page cover-page {
    @bottom-center { content: none; }
    margin: 0;
}

@page toc-page {
    @bottom-center { content: none; }
}

/* === 中文排版优化 === */
body {
    font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    font-size: 11pt;
    line-height: 1.9;
    color: #2c2c2c;
    text-align: justify;
    hyphens: auto;
}

/* === 封面 === */
.cover-page {
    page: cover-page;
    page-break-after: always;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    color: white;
    text-align: center;
    padding: 2cm;
}

.cover-top-line {
    width: 60%;
    height: 4px;
    background: linear-gradient(90deg, #533483, #e94560);
    border-radius: 2px;
    margin-bottom: 3cm;
}

.cover-title {
    font-size: 32pt;
    font-weight: 700;
    letter-spacing: 3pt;
    color: #ffffff;
    margin-bottom: 0.8cm;
    line-height: 1.4;
}

.cover-subtitle {
    font-size: 14pt;
    font-weight: 400;
    color: #b0b0c0;
    letter-spacing: 1pt;
    margin-bottom: 2cm;
}

.cover-divider {
    width: 30%;
    height: 1px;
    background: rgba(255, 255, 255, 0.2);
    margin-bottom: 2cm;
}

.cover-author {
    font-size: 13pt;
    color: #8888a0;
    margin-bottom: 0.5cm;
}

.cover-desc {
    font-size: 11pt;
    color: #777;
    max-width: 70%;
    line-height: 1.8;
    margin-bottom: 2cm;
}

.cover-bottom-line {
    width: 60%;
    height: 2px;
    background: linear-gradient(90deg, #533483, #e94560);
    border-radius: 1px;
    margin-top: 2cm;
}

.cover-date {
    font-size: 10pt;
    color: #666;
    margin-top: 1cm;
}

/* === 目录 === */
.toc-page {
    page: toc-page;
    page-break-after: always;
    padding-top: 2cm;
}

.toc-title {
    font-size: 22pt;
    font-weight: 700;
    text-align: center;
    color: #1a1a2e;
    letter-spacing: 6pt;
    margin-bottom: 2cm;
    padding-bottom: 0.5cm;
    border-bottom: 2px solid #533483;
}

.toc-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.toc-list li {
    padding: 0.35em 0;
    border-bottom: 1px dotted #ccc;
    font-size: 11.5pt;
    color: #333;
}

.toc-list li .toc-num {
    display: inline-block;
    width: 3.5em;
    color: #533483;
    font-weight: 600;
}

.toc-list li.preface .toc-num,
.toc-list li.afterword .toc-num {
    width: 3em;
}

/* === 章节 === */
.chapter-start {
    page-break-before: always;
    padding-top: 1cm;
}

h1.book-title {
    text-align: center;
    font-size: 20pt;
    color: #1a1a2e;
    font-weight: 700;
    margin: 2em 0 1.5em;
    padding-bottom: 0.5em;
    border-bottom: 2px solid #e0e0e0;
    letter-spacing: 2pt;
}

h1 {
    font-size: 17pt;
    color: #1a1a2e;
    font-weight: 700;
    margin: 2em 0 0.8em;
    padding-bottom: 0.3em;
    border-bottom: 1px solid #e8e8e8;
}

h2 {
    font-size: 14pt;
    color: #16213e;
    font-weight: 600;
    margin: 1.5em 0 0.6em;
    border-left: 4px solid #533483;
    padding-left: 0.6em;
}

h3 {
    font-size: 12pt;
    color: #0f3460;
    font-weight: 600;
    margin: 1.2em 0 0.5em;
}

h4 {
    font-size: 11pt;
    color: #333;
    font-weight: 600;
    margin: 1em 0 0.4em;
}

/* === 段落 === */
p {
    text-indent: 2em;
    margin: 0.5em 0;
    orphans: 2;
    widows: 2;
}

p:first-of-type {
    text-indent: 0;
}

/* === 引用 === */
blockquote {
    margin: 1em 1.5em;
    padding: 0.6em 1.2em;
    border-left: 4px solid #533483;
    background: #f8f8fc;
    color: #555;
    orphans: 3;
    widows: 3;
}

blockquote p {
    text-indent: 0;
    margin: 0.3em 0;
}

/* === 强调 === */
strong, b {
    color: #16213e;
    font-weight: 700;
}

em, i {
    color: #0f3460;
    font-style: italic;
}

/* === 代码 === */
code {
    background: #f0f0f5;
    padding: 0.15em 0.4em;
    border-radius: 3px;
    font-family: "SF Mono", "Fira Code", "Consolas", "Menlo", monospace;
    font-size: 9pt;
    color: #e94560;
}

pre {
    background: #1a1a2e;
    color: #d4d4d8;
    padding: 1em 1.2em;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
    orphans: 3;
    widows: 3;
}

pre code {
    background: none;
    padding: 0;
    color: inherit;
    font-size: inherit;
}

/* === 表格 === */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.2em 0;
    font-size: 10pt;
    orphans: 3;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em 0.7em;
    text-align: left;
}

th {
    background: #16213e;
    color: #ffffff;
    font-weight: 600;
}

tr:nth-child(even) {
    background: #f8f8fc;
}

/* === 列表 === */
ul, ol {
    margin: 0.5em 0 0.5em 1.5em;
    padding: 0;
}

li {
    margin: 0.25em 0;
}

ul ul, ol ol, ul ol, ol ul {
    margin: 0.2em 0 0.2em 1.5em;
}

/* === 分隔线 === */
hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 2em 0;
}

/* === 链接 === */
a {
    color: #533483;
    text-decoration: none;
}

/* === 图片 === */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
    border-radius: 4px;
}

/* === 打印优化 === */
@media print {
    .no-print { display: none; }
}

/* 尾注 */
.footnote, .footnotes {
    font-size: 9pt;
    color: #666;
    border-top: 1px solid #ddd;
    padding-top: 0.5em;
    margin-top: 2em;
}
"""


def build_html_for_pdf():
    """构建完整的 HTML 用于 PDF 渲染"""
    print("=" * 60)
    print("📄 构建 PDF 源 HTML...")
    print("=" * 60)

    # 封面
    cover_html = f"""<div class="cover-page">
<div class="cover-top-line"></div>
<div class="cover-title">{BOOK_TITLE}</div>
<div class="cover-subtitle">OntologyOps 工程范式 · 让本体像代码一样被管理</div>
<div class="cover-divider"></div>
<div class="cover-author">{BOOK_AUTHOR} · 著</div>
<div class="cover-desc">大模型越强，本体越重要。从 Palantir Foundry 到中数睿智，一本面向企业技术决策者的本体推理实践指南。</div>
<div class="cover-bottom-line"></div>
<div class="cover-date">2026年6月</div>
</div>"""

    # 版权页
    copyright_html = f"""<div class="chapter-start">
<div style="padding-top: 30%; text-align: center;">
<h1 class="book-title">{BOOK_TITLE}</h1>
<p style="text-align:center; color:#888; font-size:11pt;">作者：{BOOK_AUTHOR}</p>
<p style="text-align:center; color:#888; font-size:10pt;">2026年6月 · 第一版</p>
<hr style="margin: 2em 4em;"/>
<div style="text-align:left; max-width:70%; margin:0 auto;">
<p style="font-size:10pt; color:#555; text-indent:0;"><strong>书籍内容许可</strong></p>
<p style="font-size:9.5pt; color:#555;">本书文字内容（含章节、图表、案例分析）采用 <strong>CC BY-NC-SA 4.0</strong> 许可协议（署名-非商业性使用-相同方式共享）。你可以自由分享和改编，但必须署名作者（森林瀑布），不得用于商业目的，改编作品须使用相同许可。</p>
<p style="font-size:9.5pt; color:#555;">完整协议：https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.zh-Hans</p>
<p style="font-size:9.5pt; color:#555; margin-top:1.2em;"><strong>代码许可</strong></p>
<p style="font-size:9.5pt; color:#555;">本书配套代码、脚本、工具采用 <strong>MIT</strong> 许可协议，可自由使用、修改和商用。</p>
<p style="font-size:9.5pt; color:#555;">源码仓库：https://github.com/georgewangchn/OntologyOps</p>
</div>
<hr style="margin: 2em 4em;"/>
<p style="text-align:center; font-size:9pt; color:#aaa;">Copyright © 2026 森林瀑布</p>
<p style="text-align:center; font-size:9pt; color:#aaa;">保留商业使用的所有权利。商业授权请联系作者。</p>
</div>
</div>"""

    # 目录
    toc_items = ""
    for i, (filename, short_title, full_title) in enumerate(CHAPTERS):
        if short_title in ("序言", "后记"):
            css_class = "preface" if short_title == "序言" else "afterword"
            num_span = f'<span class="toc-num">{short_title}</span>'
        else:
            css_class = ""
            num_span = f'<span class="toc-num">{short_title}</span>'
        toc_items += f'<li class="{css_class}">{num_span}{full_title}</li>\n'

    toc_html = f"""<div class="toc-page">
<div class="toc-title">目　录</div>
<ol class="toc-list">
{toc_items}</ol>
</div>"""

    # 章节内容
    body_html = ""
    for i, (filename, short_title, full_title) in enumerate(CHAPTERS):
        print(f"  [{short_title}] 处理中...", end=" ")
        md_text, filepath = read_chapter(filename)
        if not md_text:
            print("跳过")
            continue

        # 去掉重复的 H1
        lines = md_text.strip().split("\n")
        if lines[0].startswith("# ") and not lines[0].startswith("## "):
            lines = lines[1:]
        md_text = "\n".join(lines)

        chapter_html = md_to_html_simple(md_text)

        # 序言和后记加特殊标题样式
        if short_title in ("序言", "后记"):
            header = f"<h1 class='book-title'>{full_title}</h1>"
            body_html += f'<div class="chapter-start">\n{header}\n{chapter_html}\n</div>\n'
        else:
            body_html += f'<div class="chapter-start">\n{chapter_html}\n</div>\n'

        print(f"✓ ({len(md_text)} 字符)")

    # 完整 HTML
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="author" content="{BOOK_AUTHOR}"/>
<title>{BOOK_TITLE}</title>
<style>
{PDF_CSS}
</style>
</head>
<body>
{cover_html}
{copyright_html}
{toc_html}
{body_html}
</body>
</html>"""

    html_path = os.path.join(OUTPUT_DIR, f"{BOOK_TITLE}.html")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"\n✅ HTML 源文件: {html_path}")
    return html_path


def render_pdf(html_path):
    """使用 weasyprint 渲染 PDF"""
    print("\n" + "=" * 60)
    print("📕 渲染 PDF...")
    print("=" * 60)

    from weasyprint import HTML

    pdf_path = os.path.join(OUTPUT_DIR, f"{BOOK_TITLE}.pdf")

    print("  正在渲染... (可能需要 30-60 秒)")
    doc = HTML(filename=html_path)
    doc.write_pdf(pdf_path)

    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    print(f"\n✅ PDF 生成完成!")
    print(f"   {pdf_path}")
    print(f"   文件大小: {size_mb:.2f} MB")
    return pdf_path


def main():
    print(f"\n{'='*60}")
    print(f"📖 {BOOK_TITLE}")
    print(f"👤 {BOOK_AUTHOR}")
    print(f"📅 2026年6月")
    print(f"{'='*60}\n")

    html_path = build_html_for_pdf()
    pdf_path = render_pdf(html_path)

    print(f"\n{'='*60}")
    print("🎉 全部完成！")
    print(f"{'='*60}")
    print(f"  EPUB: {os.path.join(OUTPUT_DIR, f'{BOOK_TITLE}.epub')}")
    print(f"  PDF:  {pdf_path}")
    print(f"{'='*60}\n")

    return pdf_path


if __name__ == "__main__":
    main()

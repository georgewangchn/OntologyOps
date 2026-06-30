#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 EPUB 和 PDF 电子书
从 Markdown 章节文件生成标准 EPUB 3.0 和排版精美的 PDF
"""

import os
import re
import sys
from pathlib import Path

# === 书籍元数据 ===
BOOK_TITLE = "当LLM不够用了——本体推理的企业决策实践"
BOOK_AUTHOR = "森林瀑布"
BOOK_LANGUAGE = "zh-CN"
BOOK_DESCRIPTION = (
    "大模型越强，本体越重要。本书从第一性原理出发，论证 LLM 和本体推理的互补关系，"
    "提出 OntologyOps 工程范式——让 LLM 负责知识工程链、本体负责知识模型、"
    "推理机负责确定性推理。以 Palantir Foundry 和中数睿智为深度案例，"
    "为 CTO、技术 VP、企业架构师提供决策参考。"
)
BOOK_PUBLISHER = "OntologyOps"
BOOK_IDENTIFIER = "urn:uuid:ontologyops-decision-reasoning-2026"

# === 路径配置 ===
CHAPS_DIR = "/Users/siidt/Documents/code/1petpri-main/ontologyops/chapters"
OUTPUT_DIR = "/Users/siidt/Documents/code/1petpri-main/ontologyops/book/output"
COVER_IMG = f"{CHAPS_DIR}/img.png"

# === 章节列表（按顺序）===
CHAPTERS = [
    ("序言-为什么现在是时候了.md", "序言", "序言：为什么现在是时候了", "preface"),
    ("第一章-本体论是什么.md", "第一章", "第一章：本体论是什么（以及它不是什么）", "chapter"),
    ("第二章-企业为什么需要本体推理.md", "第二章", "第二章：企业为什么需要本体推理？", "chapter"),
    ("第三章-本体落地的认知工程.md", "第三章", "第三章：本体落地——一场不亚于管理咨询的认知工程", "chapter"),
    ("第四章-本体推理的技术基础设施.md", "第四章", "第四章：本体推理的技术基础设施", "chapter"),
    ("第五章-企业级本体推理架构设计.md", "第五章", "第五章：企业级本体推理架构设计", "chapter"),
    ("第六章-Palantir-Foundry深度剖析.md", "第六章", "第六章：Palantir Foundry 深度剖析", "chapter"),
    ("第七章-中数睿智-动态本体引擎.md", "第七章", "第七章：中数睿智——本体推理的中国答案", "chapter"),
    ("第八章-GraphRAG与本体增强的大模型应用.md", "第八章", "第八章：GraphRAG 与本体增强的大模型应用", "chapter"),
    ("第九章-打造你的第一条企业决策推理链.md", "第九章", "第九章：打造你的第一条企业决策推理链", "chapter"),
    ("第十章-OntologyOps.md", "第十章", "第十章：OntologyOps——让本体像代码一样被管理", "chapter"),
    ("后记-从工具到思维.md", "后记", "后记：从工具到思维——本体论的方法论意义", "afterword"),
]


def read_chapter(filename):
    """读取章节文件，返回 (内容, 文件路径)"""
    filepath = os.path.join(CHAPS_DIR, filename)
    if not os.path.exists(filepath):
        print(f"⚠️  文件不存在: {filepath}")
        return "", filepath
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read(), filepath


def md_to_html(md_text, chapter_title=""):
    """Markdown 转 HTML（加强版，支持更多语法）"""
    import markdown

    # 预处理：去掉第一行的 # 标题（如果和章节标题重复）
    lines = md_text.strip().split("\n")
    processed_lines = []
    skip_first_h1 = False

    if lines and lines[0].startswith("# ") and not lines[0].startswith("## "):
        # 第一行是 H1 标题，可能和书名重复，保留但降级
        skip_first_h1 = True
        processed_lines.append(f"<h1 class='book-title'>{lines[0][2:].strip()}</h1>")
        processed_lines.extend(lines[1:])
        md_text = "\n".join(processed_lines)

    # 使用 Python-Markdown 扩展
    html = markdown.markdown(
        md_text,
        extensions=[
            "extra",  # 表格、代码块、脚注等
            "codehilite",  # 代码高亮
            "toc",  # 目录
            "sane_lists",  # 更好的列表处理
            "smarty",  # 智能引号
        ],
        extension_configs={
            "codehilite": {"css_class": "codehilite", "guess_lang": False},
        },
    )

    return html


def generate_epub():
    """生成 EPUB 3.0 电子书"""
    print("=" * 60)
    print("📚 生成 EPUB 电子书...")
    print("=" * 60)

    from ebooklib import epub

    book = epub.EpubBook()

    # --- 元数据 ---
    book.set_identifier(BOOK_IDENTIFIER)
    book.set_title(BOOK_TITLE)
    book.set_language(BOOK_LANGUAGE)
    book.add_author(BOOK_AUTHOR)
    book.add_metadata("DC", "description", BOOK_DESCRIPTION)
    book.add_metadata("DC", "publisher", BOOK_PUBLISHER)

    # --- CSS 样式 ---
    css = epub.EpubItem(
        uid="book-style",
        file_name="style/book.css",
        media_type="text/css",
        content="""
body {
    font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    line-height: 1.8;
    color: #333;
    margin: 2em;
}
h1.book-title {
    text-align: center;
    font-size: 1.8em;
    color: #1a1a2e;
    margin: 1.5em 0 1em;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 0.5em;
}
h1 {
    font-size: 1.5em;
    color: #16213e;
    margin: 1.2em 0 0.6em;
}
h2 {
    font-size: 1.3em;
    color: #0f3460;
    margin: 1em 0 0.5em;
    border-left: 4px solid #533483;
    padding-left: 0.6em;
}
h3 {
    font-size: 1.15em;
    color: #1a1a2e;
    margin: 0.8em 0 0.4em;
}
p {
    text-indent: 2em;
    margin: 0.6em 0;
}
p:first-of-type {
    text-indent: 0;
}
blockquote {
    margin: 1em 1.5em;
    padding: 0.5em 1em;
    border-left: 4px solid #533483;
    background: #f8f8fc;
    color: #555;
    font-style: italic;
}
blockquote p {
    text-indent: 0;
}
strong, b {
    color: #16213e;
    font-weight: 700;
}
em, i {
    color: #0f3460;
}
code {
    background: #f0f0f5;
    padding: 0.15em 0.4em;
    border-radius: 3px;
    font-family: "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 0.9em;
}
pre {
    background: #1a1a2e;
    color: #e0e0e0;
    padding: 1em 1.2em;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 0.85em;
    line-height: 1.6;
    margin: 1em 0;
}
pre code {
    background: none;
    padding: 0;
    color: inherit;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 0.95em;
}
th, td {
    border: 1px solid #ddd;
    padding: 0.6em 0.8em;
    text-align: left;
}
th {
    background: #16213e;
    color: white;
    font-weight: 600;
}
tr:nth-child(even) {
    background: #f8f8fc;
}
ul, ol {
    margin: 0.5em 0 0.5em 1.5em;
}
li {
    margin: 0.3em 0;
}
hr {
    border: none;
    border-top: 1px solid #e0e0e0;
    margin: 2em 0;
}
a {
    color: #533483;
    text-decoration: none;
}
/* 章节分隔页 */
.chapter-break {
    page-break-before: always;
    text-align: center;
    padding-top: 30%;
}
.chapter-break h1 {
    font-size: 2em;
    border: none;
    color: #1a1a2e;
}
""".strip(),
    )
    book.add_item(css)

    # --- 封面 ---
    if os.path.exists(COVER_IMG):
        with open(COVER_IMG, "rb") as f:
            cover_data = f.read()
        book.set_cover("cover.png", cover_data)
        print("  ✓ 封面图片已添加")

        # 封面页
        cover_page = epub.EpubHtml(
            title="封面",
            file_name="cover.xhtml",
            lang="zh-CN",
        )
        cover_page.content = f"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>封面</title></head>
<body style="margin:0; padding:0; text-align:center;">
  <img src="cover.png" alt="{BOOK_TITLE}" style="width:100%; max-width:100%;"/>
</body></html>"""
        book.add_item(cover_page)
    else:
        print("  ⚠️  未找到封面图片，使用文字封面")

    # --- 章节处理 ---
    spine = ["nav"]
    toc_entries = []
    all_chapters = []

    for i, (filename, short_title, full_title, ch_type) in enumerate(CHAPTERS):
        print(f"  [{short_title}] 处理中...", end=" ")
        md_text, filepath = read_chapter(filename)
        if not md_text:
            print("跳过（无内容）")
            continue

        html_body = md_to_html(md_text, full_title)

        # 创建 EPUB 章节
        chapter_id = f"ch_{i:02d}"
        chapter = epub.EpubHtml(
            title=full_title,
            file_name=f"{chapter_id}.xhtml",
            lang="zh-CN",
        )

        # 根据章节类型添加分隔样式
        if ch_type == "preface":
            header_html = f'<h1 class="book-title">{full_title}</h1>'
        elif ch_type == "afterword":
            header_html = f'<h1 class="book-title">{full_title}</h1>'
        else:
            header_html = ""  # 章节内已有 h1

        chapter.content = f"""<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{full_title}</title>
  <link rel="stylesheet" type="text/css" href="style/book.css"/>
</head>
<body>
{header_html}
{html_body}
</body></html>"""

        chapter.add_item(css)
        book.add_item(chapter)
        spine.append(chapter)
        all_chapters.append(chapter)

        # TOC 条目
        toc_entries.append(
            epub.Link(f"{chapter_id}.xhtml", full_title, chapter_id)
        )
        print(f"✓ ({len(md_text)} 字符)")

    # --- 目录 ---
    book.toc = toc_entries
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # --- 设置 spine ---
    book.spine = spine

    # --- 写入文件 ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    epub_path = os.path.join(OUTPUT_DIR, f"{BOOK_TITLE}.epub")
    epub.write_epub(epub_path, book, {})
    size_mb = os.path.getsize(epub_path) / (1024 * 1024)
    print(f"\n✅ EPUB 生成完成: {epub_path}")
    print(f"   文件大小: {size_mb:.2f} MB")
    return epub_path


def generate_html_for_pdf():
    """生成用于 PDF 转换的单个 HTML 文件"""
    print("\n" + "=" * 60)
    print("📄 准备 PDF 生成...")
    print("=" * 60)

    css = """
<style>
@page {
    size: A4;
    margin: 2.5cm 2cm 2.5cm 2cm;
    @footnotes {
        border-top: 1px solid #ccc;
        padding-top: 0.3cm;
    }
    @bottom-center {
        content: counter(page);
        font-family: "PingFang SC", sans-serif;
        font-size: 9pt;
        color: #999;
    }
}
@page :first {
    @bottom-center {
        content: none;
    }
}
body {
    font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    line-height: 1.9;
    font-size: 11pt;
    color: #333;
}
/* 封面 */
.cover-page {
    page-break-after: always;
    text-align: center;
    padding-top: 25%;
}
.cover-page .cover-title {
    font-size: 28pt;
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: 2pt;
    margin-bottom: 1.5em;
}
.cover-page .cover-subtitle {
    font-size: 14pt;
    color: #533483;
    margin-bottom: 3em;
}
.cover-page .cover-author {
    font-size: 13pt;
    color: #666;
}
.cover-page .cover-date {
    font-size: 11pt;
    color: #999;
    margin-top: 1em;
}
/* 目录 */
.toc-page {
    page-break-after: always;
}
.toc-title {
    font-size: 20pt;
    text-align: center;
    margin-bottom: 1.5em;
    color: #1a1a2e;
}
.toc-list {
    list-style: none;
    padding: 0;
}
.toc-list li {
    padding: 0.3em 0;
    border-bottom: 1px dotted #ccc;
    font-size: 11pt;
}
.toc-list li a {
    color: #333;
    text-decoration: none;
}
/* 章节标题 */
h1.book-title {
    text-align: center;
    font-size: 18pt;
    color: #1a1a2e;
    margin: 2em 0 1em;
    border-bottom: 2px solid #533483;
    padding-bottom: 0.5em;
}
h1 {
    font-size: 16pt;
    color: #16213e;
    margin: 1.5em 0 0.6em;
}
h2 {
    font-size: 13pt;
    color: #0f3460;
    margin: 1.2em 0 0.5em;
    border-left: 4px solid #533483;
    padding-left: 0.6em;
}
h3 {
    font-size: 11.5pt;
    color: #1a1a2e;
    margin: 1em 0 0.4em;
}
p {
    text-indent: 2em;
    margin: 0.5em 0;
}
p:first-of-type {
    text-indent: 0;
}
blockquote {
    margin: 1em 1.5em;
    padding: 0.5em 1em;
    border-left: 4px solid #533483;
    background: #f8f8fc;
    color: #555;
}
blockquote p {
    text-indent: 0;
}
strong, b {
    color: #16213e;
}
code {
    background: #f0f0f5;
    padding: 0.1em 0.3em;
    border-radius: 2px;
    font-family: "SF Mono", "Fira Code", monospace;
    font-size: 9.5pt;
}
pre {
    background: #1a1a2e;
    color: #e0e0e0;
    padding: 0.8em 1em;
    border-radius: 4px;
    font-size: 9pt;
    line-height: 1.5;
    overflow-x: auto;
    page-break-inside: avoid;
}
pre code {
    background: none;
    padding: 0;
    color: inherit;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 10pt;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #ddd;
    padding: 0.4em 0.6em;
    text-align: left;
}
th {
    background: #16213e;
    color: white;
}
tr:nth-child(even) {
    background: #f8f8fc;
}
ul, ol {
    margin: 0.5em 0 0.5em 1.5em;
}
li {
    margin: 0.2em 0;
}
hr {
    border: none;
    border-top: 1px solid #e0e0e0;
    margin: 1.5em 0;
}
a {
    color: #533483;
}
/* 分页控制 */
.chapter-start {
    page-break-before: always;
}
.no-break {
    page-break-inside: avoid;
}
</style>"""

    # 构建目录
    toc_html = '<div class="toc-page">\n<h1 class="toc-title">目　录</h1>\n<ul class="toc-list">\n'
    body_html = ""

    for i, (filename, short_title, full_title, ch_type) in enumerate(CHAPTERS):
        anchor = f"ch{i:02d}"
        toc_html += f'  <li><a href="#{anchor}">{full_title}</a></li>\n'

        md_text, _ = read_chapter(filename)
        if not md_text:
            continue

        print(f"  [{short_title}] 处理中...", end=" ")
        html = md_to_html(md_text, full_title)

        if ch_type in ("preface", "afterword"):
            header = f'<h1 class="book-title">{full_title}</h1>'
        else:
            header = ""

        body_html += f"""
<div class="chapter-start" id="{anchor}">
{header}
{html}
</div>
"""
        print(f"✓")

    toc_html += "</ul>\n</div>\n"

    # 封面
    cover_html = f"""<div class="cover-page">
<div class="cover-title">{BOOK_TITLE}</div>
<div class="cover-subtitle">——让 LLM 和本体推理各司其职</div>
<div class="cover-author">作者：{BOOK_AUTHOR}</div>
<div class="cover-date">2026年6月</div>
</div>
"""

    # 完整 HTML
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>{BOOK_TITLE}</title>
{css}
</head>
<body>
{cover_html}
{toc_html}
{body_html}
</body>
</html>"""

    # 保存 HTML
    html_path = os.path.join(OUTPUT_DIR, f"{BOOK_TITLE}.html")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"\n✅ HTML 中间文件已生成: {html_path}")
    return html_path


def generate_pdf(html_path=None):
    """从 HTML 生成 PDF"""
    if html_path is None:
        html_path = generate_html_for_pdf()

    print("\n" + "=" * 60)
    print("📕 生成 PDF...")

    pdf_path = os.path.join(OUTPUT_DIR, f"{BOOK_TITLE}.pdf")

    # 尝试 pandoc → PDF
    pandoc = "/opt/homebrew/bin/pandoc"
    if os.path.exists(pandoc):
        print("  使用 pandoc + xelatex 生成 PDF...")
        cmd = (
            f'"{pandoc}" "{html_path}" '
            f'-o "{pdf_path}" '
            f'--pdf-engine=/Library/TeX/texbin/xelatex '
            f'-V mainfont="PingFang SC" '
            f'-V CJKmainfont="PingFang SC" '
            f'-V geometry:margin=2.5cm '
            f'--from html '
            f'--to pdf '
            f'2>&1'
        )
    else:
        print("  使用 weasyprint 生成 PDF...")
        # 尝试 weasyprint
        try:
            from weasyprint import HTML

            HTML(filename=html_path).write_pdf(pdf_path)
            size_kb = os.path.getsize(pdf_path) / 1024
            print(f"\n✅ PDF 生成完成: {pdf_path}")
            print(f"   文件大小: {size_kb:.1f} KB")
            return pdf_path
        except ImportError:
            print("  ❌ weasyprint 未安装")
            print("  尝试安装...")
            import subprocess

            subprocess.run(
                [
                    "/Users/siidt/.workbuddy/binaries/python/envs/default/bin/pip",
                    "install",
                    "weasyprint",
                ],
                check=True,
            )
            from weasyprint import HTML

            HTML(filename=html_path).write_pdf(pdf_path)

    # Pandoc 方式
    if os.path.exists(pandoc):
        import subprocess as sp

        result = sp.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=OUTPUT_DIR,
        )
        if result.returncode == 0:
            size_kb = os.path.getsize(pdf_path) / 1024
            print(f"\n✅ PDF 生成完成: {pdf_path}")
            print(f"   文件大小: {size_kb:.1f} KB")
        else:
            print(f"  ❌ Pandoc 生成失败:")
            print(f"  {result.stderr[:500]}")
            print("  尝试备用方案...")
            # Fallback: install weasyprint
            import subprocess

            subprocess.run(
                [
                    "/Users/siidt/.workbuddy/binaries/python/envs/default/bin/pip",
                    "install",
                    "weasyprint",
                ],
                check=True,
            )
            from weasyprint import HTML

            HTML(filename=html_path).write_pdf(pdf_path)
            size_kb = os.path.getsize(pdf_path) / 1024
            print(f"\n✅ PDF 生成完成（via weasyprint）: {pdf_path}")
            print(f"   文件大小: {size_kb:.1f} KB")

    return pdf_path


def main():
    print(f"\n{'='*60}")
    print(f"📖 {BOOK_TITLE}")
    print(f"👤 {BOOK_AUTHOR}")
    print(f"📅 2026年6月")
    print(f"{'='*60}\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 生成 EPUB
    epub_path = generate_epub()

    # 生成 PDF
    pdf_path = generate_pdf()

    print(f"\n{'='*60}")
    print("🎉 电子书生成完毕！")
    print(f"{'='*60}")
    print(f"  EPUB: {epub_path}")
    print(f"  PDF:  {pdf_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

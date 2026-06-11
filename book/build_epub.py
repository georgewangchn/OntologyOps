#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯 Python 标准库 EPUB 3.0 生成器
不依赖 ebooklib/lxml，使用 xml.etree.ElementTree + zipfile
"""

import os
import re
import zipfile
import uuid
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

# === 书籍元数据 ===
BOOK_TITLE = "当LLM不够用了——本体推理的企业决策实践"
BOOK_AUTHOR = "森林瀑布"
BOOK_LANGUAGE = "zh-CN"
BOOK_DESC = (
    "大模型越强，本体越重要。本书从第一性原理出发，论证 LLM 和本体推理的互补关系，"
    "提出 OntologyOps 工程范式。以 Palantir Foundry 和中数睿智为深度案例，"
    "为 CTO、技术 VP、企业架构师提供决策参考。"
)
BOOK_UID = f"urn:uuid:{uuid.uuid4()}"
BOOK_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# === 路径 ===
CHAPS_DIR = os.path.expanduser("~/Documents/code/1petpri-main/ontologyops/chapters")
OUTPUT_DIR = os.path.expanduser("~/Documents/code/1petpri-main/ontologyops/book/output")
COVER_IMG = os.path.join(CHAPS_DIR, "img.png")

CHAPTERS = [
    ("序言-为什么现在是时候了.md", "序言", "序言：为什么现在是时候了"),
    ("第一章-本体论是什么.md", "第一章", "第一章：本体论是什么（以及它不是什么）"),
    ("第二章-企业为什么需要本体推理.md", "第二章", "第二章：企业为什么需要本体推理？"),
    ("第三章-本体落地的认知工程.md", "第三章", "第三章：本体落地——一场不亚于管理咨询的认知工程"),
    ("第四章-本体推理的技术基础设施.md", "第四章", "第四章：本体推理的技术基础设施"),
    ("第五章-企业级本体推理架构设计.md", "第五章", "第五章：企业级本体推理架构设计"),
    ("第六章-Palantir-Foundry深度剖析.md", "第六章", "第六章：Palantir Foundry 深度剖析"),
    ("第七章-中数睿智-动态本体引擎.md", "第七章", "第七章：中数睿智——本体推理的中国答案"),
    ("第八章-GraphRAG与本体增强的大模型应用.md", "第八章", "第八章：GraphRAG 与本体增强的大模型应用"),
    ("第九章-打造你的第一条企业决策推理链.md", "第九章", "第九章：打造你的第一条企业决策推理链"),
    ("第十章-OntologyOps.md", "第十章", "第十章：OntologyOps——让本体像代码一样被管理"),
    ("后记-从工具到思维.md", "后记", "后记：从工具到思维——本体论的方法论意义"),
]

# === CSS 样式 ===
BOOK_CSS = """
body {
    font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    line-height: 1.85;
    color: #333;
    margin: 0;
    padding: 1.5em;
}
h1.book-title {
    text-align: center;
    font-size: 1.8em;
    color: #1a1a2e;
    margin: 1.5em 0 1em;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 0.5em;
}
h1 { font-size: 1.5em; color: #16213e; margin: 1.2em 0 0.6em; }
h2 {
    font-size: 1.25em; color: #0f3460; margin: 1em 0 0.5em;
    border-left: 4px solid #533483; padding-left: 0.6em;
}
h3 { font-size: 1.1em; color: #1a1a2e; margin: 0.8em 0 0.4em; }
p { text-indent: 2em; margin: 0.6em 0; }
p:first-of-type { text-indent: 0; }
blockquote {
    margin: 1em 1.2em; padding: 0.5em 1em;
    border-left: 4px solid #533483; background: #f8f8fc; color: #555;
}
blockquote p { text-indent: 0; }
strong, b { color: #16213e; font-weight: 700; }
code {
    background: #f0f0f5; padding: 0.15em 0.4em; border-radius: 3px;
    font-family: "SF Mono", "Fira Code", "Consolas", monospace; font-size: 0.9em;
}
pre {
    background: #1a1a2e; color: #e0e0e0; padding: 1em 1.2em;
    border-radius: 6px; overflow-x: auto; font-size: 0.85em; line-height: 1.6;
}
pre code { background: none; padding: 0; color: inherit; }
table { width: 100%; border-collapse: collapse; margin: 1em 0; font-size: 0.95em; }
th, td { border: 1px solid #ddd; padding: 0.5em 0.7em; text-align: left; }
th { background: #16213e; color: white; }
tr:nth-child(even) { background: #f8f8fc; }
ul, ol { margin: 0.5em 0 0.5em 1.5em; }
li { margin: 0.3em 0; }
hr { border: none; border-top: 1px solid #e0e0e0; margin: 1.5em 0; }
a { color: #533483; text-decoration: none; }
em, i { color: #0f3460; }
"""


def read_chapter(filename):
    path = os.path.join(CHAPS_DIR, filename)
    if not os.path.exists(path):
        return "", path
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), path


def md_to_html_simple(md_text):
    """简化的 Markdown → HTML 转换器（纯 Python，零依赖）"""
    lines = md_text.strip().split("\n")
    result = []
    in_code = False
    code_buf = []
    in_table = False
    table_buf = []
    table_align = []
    in_quote = False
    quote_buf = []
    in_list = False
    list_buf = []
    list_type = "ul"

    def flush_paragraph(buf):
        """将缓冲区输出为段落"""
        if not buf:
            return
        text = " ".join(buf)
        result.append(f"<p>{text}</p>")

    def flush_code():
        if code_buf:
            code_text = "\n".join(code_buf)
            # 转义 HTML
            code_text = code_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            result.append(f"<pre><code>{code_text}</code></pre>")

    def flush_table():
        if not table_buf:
            return
        result.append("<table>")
        if table_buf:
            header = table_buf[0]
            result.append("<thead><tr>")
            for cell in header:
                result.append(f"<th>{cell}</th>")
            result.append("</tr></thead>")
        if len(table_buf) > 1:
            result.append("<tbody>")
            for row in table_buf[1:]:
                result.append("<tr>")
                for cell in row:
                    result.append(f"<td>{cell}</td>")
                result.append("</tr>")
            result.append("</tbody>")
        result.append("</table>")

    def flush_quote():
        if quote_buf:
            text = "<br/>".join(quote_buf)
            result.append(f"<blockquote><p>{text}</p></blockquote>")

    def flush_list():
        if list_buf:
            result.append(f"<{list_type}>")
            for item in list_buf:
                result.append(f"<li>{item}</li>")
            result.append(f"</{list_type}>")

    def inline_format(text):
        """处理行内格式：**粗体**, *斜体*, `代码`"""
        # 代码
        text = re.sub(r"`([^`]+)`", r'<code>\1</code>', text)
        # 粗体 **text**
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # 斜体 *text*（但要避免在 ** 后误匹配）
        text = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<em>\1</em>", text)
        return text

    para_buf = []

    def flush_all():
        """将所有缓冲区内容输出"""
        nonlocal in_table, in_quote, in_list, table_buf, quote_buf, list_buf, para_buf
        if in_table:
            flush_table()
            table_buf = []
            in_table = False
        elif in_quote:
            flush_quote()
            quote_buf = []
            in_quote = False
        elif in_list:
            flush_list()
            list_buf = []
            in_list = False
        else:
            flush_paragraph(para_buf)
            para_buf = []

    for line in lines:
        # 代码块
        if line.strip().startswith("```"):
            if not in_code:
                flush_paragraph(para_buf)
                para_buf = []
                in_code = True
                code_buf = []
            else:
                flush_code()
                code_buf = []
                in_code = False
            continue

        if in_code:
            code_buf.append(line)
            continue

        # 空行
        if not line.strip():
            if in_table:
                flush_table()
                table_buf = []
                in_table = False
            elif in_quote:
                flush_quote()
                quote_buf = []
                in_quote = False
            elif in_list:
                flush_list()
                list_buf = []
                in_list = False
            else:
                flush_paragraph(para_buf)
                para_buf = []
            continue

        # 引用
        if line.strip().startswith("> "):
            if in_table:
                flush_table()
                table_buf = []
                in_table = False
            if in_list:
                flush_list()
                list_buf = []
                in_list = False
            flush_paragraph(para_buf)
            para_buf = []
            in_quote = True
            content = line.strip()[2:]
            quote_buf.append(inline_format(content))
            continue

        # 标题
        if line.startswith("### "):
            flush_all()
            result.append(f"<h3>{inline_format(line[4:].strip())}</h3>")
            continue
        if line.startswith("## "):
            flush_all()
            result.append(f"<h2>{inline_format(line[3:].strip())}</h2>")
            continue
        if line.startswith("# "):
            flush_all()
            result.append(f"<h1>{inline_format(line[2:].strip())}</h1>")
            continue

        # 分隔线
        if line.strip() in ("---", "***", "___"):
            flush_all()
            result.append("<hr/>")
            continue

        # 表格
        if "|" in line and line.strip().startswith("|"):
            if in_quote:
                flush_quote()
                quote_buf = []
                in_quote = False
            if in_list:
                flush_list()
                list_buf = []
                in_list = False
            flush_paragraph(para_buf)
            para_buf = []

            cells = [c.strip() for c in line.strip().split("|")]
            cells = [c for c in cells if c]  # 去掉首尾空的

            # 分隔行（|----|----|）
            if all(re.match(r"^[-:]+$", c) for c in cells):
                continue

            if not in_table:
                in_table = True
                table_buf = []
            table_buf.append([inline_format(c) for c in cells])
            continue

        # 无序列表
        if re.match(r"^[\s]*[-*+]\s+", line):
            flush_all()
            in_list = True
            list_type = "ul"
            content = re.sub(r"^[\s]*[-*+]\s+", "", line)
            list_buf.append(inline_format(content))
            continue

        # 有序列表
        if re.match(r"^[\s]*\d+\.\s+", line):
            flush_all()
            in_list = True
            list_type = "ol"
            content = re.sub(r"^[\s]*\d+\.\s+", "", line)
            list_buf.append(inline_format(content))
            continue

        # 普通段落
        para_buf.append(inline_format(line))

    # 清理尾部
    if in_code:
        flush_code()
    if in_table:
        flush_table()
    elif in_quote:
        flush_quote()
    elif in_list:
        flush_list()
    else:
        flush_paragraph(para_buf)

    return "\n".join(result)


def xml_decl():
    return '<?xml version="1.0" encoding="utf-8"?>'


def gen_container_xml():
    return (
        xml_decl()
        + '\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        "\n  <rootfiles>"
        '\n    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
        "\n  </rootfiles>"
        "\n</container>"
    )


def gen_content_opf(manifest_items, spine_ids, guide_items=""):
    """生成 content.opf"""
    manifest = ""
    for mid, href, mtype in manifest_items:
        props = ""
        if mid == "cover":
            props = ' properties="cover-image"'
        elif "nav" in mid:
            props = ' properties="nav"'
        manifest += f'\n    <item id="{mid}" href="{href}" media-type="{mtype}"{props}/>'

    spine = ""
    for sid in spine_ids:
        spine += f'\n    <itemref idref="{sid}"/>'

    return (
        xml_decl()
        + '\n<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="book-id" version="3.0">'
        + f'\n  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        + f'\n    <dc:title>{BOOK_TITLE}</dc:title>'
        + f'\n    <dc:creator id="author">{BOOK_AUTHOR}</dc:creator>'
        + f'\n    <dc:language>{BOOK_LANGUAGE}</dc:language>'
        + f'\n    <dc:description>{BOOK_DESC}</dc:description>'
        + f'\n    <dc:date>{BOOK_DATE}</dc:date>'
        + f'\n    <dc:publisher>OntologyOps</dc:publisher>'
        + f'\n    <meta refines="#author" property="role" scheme="marc:relators">aut</meta>'
        + f'\n    <meta property="dcterms:modified">{BOOK_DATE}</meta>'
        + f'\n  </metadata>'
        + f"\n  <manifest>{manifest}\n  </manifest>"
        + f"\n  <spine>{spine}\n  </spine>"
        + f"\n  {guide_items}"
        + "\n</package>"
    )


def gen_toc_ncx(nav_points):
    """生成 toc.ncx（EPUB 2 兼容）"""
    nav = ""
    for i, (pid, title, href) in enumerate(nav_points):
        nav += (
            f'\n    <navPoint id="navPoint-{i}" playOrder="{i+1}">'
            f'\n      <navLabel><text>{title}</text></navLabel>'
            f'\n      <content src="{href}"/>'
            f"\n    </navPoint>"
        )

    return (
        xml_decl()
        + '\n<!DOCTYPE ncx PUBLIC "-//IDPF//DTD EPUB Navigation Control XML Document//EN" '
        '"http://www.idpf.org/2007/ops/dtd/ncx-2005-1.dtd">'
        + '\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        + f"\n  <head><meta name='dtb:uid' content='{BOOK_UID}'/></head>"
        + f"\n  <docTitle><text>{BOOK_TITLE}</text></docTitle>"
        + f"\n  <docAuthor><text>{BOOK_AUTHOR}</text></docAuthor>"
        + f"\n  <navMap>{nav}\n  </navMap>"
        + "\n</ncx>"
    )


def gen_nav_xhtml(toc_items):
    """生成 nav.xhtml（EPUB 3 目录）"""
    items = ""
    for pid, title, href in toc_items:
        items += f'\n      <li><a href="{href}">{title}</a></li>'

    return (
        xml_decl()
        + '\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">'
        + "\n<head><title>目录</title></head>"
        + "\n<body>"
        + '\n  <nav epub:type="toc" id="toc">'
        + "\n    <h1>目 录</h1>"
        + f"\n    <ol>{items}\n    </ol>"
        + "\n  </nav>"
        + "\n</body>"
        + "\n</html>"
    )


def gen_chapter_xhtml(chapter_id, title, body_html):
    """生成章节 XHTML"""
    return (
        xml_decl()
        + f'\n<html xmlns="http://www.w3.org/1999/xhtml" lang="zh-CN">'
        + f"\n<head><title>{title}</title><link rel='stylesheet' type='text/css' href='css/book.css'/></head>"
        + f"\n<body>\n{body_html}\n</body>"
        + "\n</html>"
    )


def gen_cover_xhtml():
    return (
        xml_decl()
        + '\n<html xmlns="http://www.w3.org/1999/xhtml" lang="zh-CN">'
        + "\n<head><title>封面</title></head>"
        + '\n<body style="margin:0; padding:0; text-align:center;">'
        + '\n  <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 600 800" preserveAspectRatio="xMidYMid meet">'
        + '\n    <defs>'
        + '\n      <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">'
        + '\n        <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1"/>'
        + '\n        <stop offset="60%" style="stop-color:#16213e;stop-opacity:1"/>'
        + '\n        <stop offset="100%" style="stop-color:#0f3460;stop-opacity:1"/>'
        + '\n      </linearGradient>'
        + '\n      <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">'
        + '\n        <stop offset="0%" style="stop-color:#533483"/>'
        + '\n        <stop offset="100%" style="stop-color:#e94560"/>'
        + '\n      </linearGradient>'
        + '\n    </defs>'
        + '\n    <rect width="600" height="800" fill="url(#bg)"/>'
        + '\n    <rect x="80" y="70" width="440" height="8" fill="url(#accent)" rx="4"/>'
        + '\n    <text x="300" y="260" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="36" font-weight="700" fill="white">当LLM不够用了</text>'
        + '\n    <text x="300" y="340" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="28" font-weight="600" fill="#e0e0e0">本体推理的企业决策实践</text>'
        + '\n    <rect x="120" y="400" width="360" height="1" fill="#533483" opacity="0.6"/>'
        + '\n    <text x="300" y="480" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="18" fill="#888">森林瀑布 · 著</text>'
        + '\n    <text x="300" y="530" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="14" fill="#666">OntologyOps 工程范式</text>'
        + '\n    <text x="300" y="570" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="14" fill="#666">让本体像代码一样被管理</text>'
        + '\n    <rect x="80" y="720" width="440" height="2" fill="url(#accent)" rx="1"/>'
        + '\n    <text x="300" y="760" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="13" fill="#666">2026年6月</text>'
        + "\n  </svg>"
        + "\n</body>"
        + "\n</html>"
    )


def gen_copyright_xhtml():
    """生成版权页"""
    return (
        xml_decl()
        + '\n<html xmlns="http://www.w3.org/1999/xhtml" lang="zh-CN">'
        + "\n<head><title>版权信息</title><link rel='stylesheet' type='text/css' href='css/book.css'/></head>"
        + f"\n<body>"
        + f"\n<div style='padding-top: 30%;'>"
        + f"\n<h1 class='book-title'>{BOOK_TITLE}</h1>"
        + f"\n<p style='text-align:center; color:#888;'>作者：{BOOK_AUTHOR}</p>"
        + f"\n<p style='text-align:center; color:#888;'>2026年6月 · 第一版</p>"
        + "\n<hr style='margin: 2em 3em;'/>"
        + "\n<p style='font-size:0.9em; color:#666;'><strong>书籍内容许可</strong></p>"
        + "\n<p style='font-size:0.85em; color:#666;'>本书文字内容（含章节、图表、案例分析）采用 <strong>CC BY-NC-SA 4.0</strong> 许可协议——署名 + 非商业性使用 + 相同方式共享。</p>"
        + "\n<p style='font-size:0.85em; color:#666;'>这意味着：你可以自由分享和改编本书内容，但必须署名作者（森林瀑布），不得用于商业目的（如出售、付费培训教材等），且改编作品须使用相同许可协议。</p>"
        + "\n<p style='font-size:0.85em; color:#666;'>完整协议：https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.zh-Hans</p>"
        + "\n<p style='font-size:0.85em; color:#666; margin-top:1em;'><strong>代码许可</strong></p>"
        + "\n<p style='font-size:0.85em; color:#666;'>本书配套的代码、脚本、工具采用 <strong>MIT</strong> 许可协议，可自由使用、修改和商用。</p>"
        + "\n<p style='font-size:0.85em; color:#666;'>源码仓库：https://github.com/georgewangchn/OntologyOps</p>"
        + "\n<hr style='margin: 2em 3em;'/>"
        + "\n<p style='text-align:center; font-size:0.8em; color:#aaa;'>Copyright © 2026 森林瀑布</p>"
        + "\n<p style='text-align:center; font-size:0.8em; color:#aaa;'>保留商业使用的所有权利。商业授权请联系作者。</p>"
        + "\n</div>"
        + "\n</body>"
        + "\n</html>"
    )


def build_epub():
    """主构建流程"""
    print("=" * 60)
    print(f"📚 生成 EPUB 电子书: {BOOK_TITLE}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    epub_path = os.path.join(OUTPUT_DIR, f"{BOOK_TITLE}.epub")

    # ZIP 文件
    with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_DEFLATED) as zf:

        # --- mimetype（必须是第一条，不压缩）---
        mimetype_zipinfo = zipfile.ZipInfo("mimetype")
        mimetype_zipinfo.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype_zipinfo, "application/epub+zip")

        # --- META-INF/container.xml ---
        zf.writestr("META-INF/container.xml", gen_container_xml())

        # --- CSS ---
        zf.writestr("OEBPS/css/book.css", BOOK_CSS)

        # --- 封面（SVG）---
        zf.writestr("OEBPS/cover.xhtml", gen_cover_xhtml())

        # --- 版权页 ---
        zf.writestr("OEBPS/copyright.xhtml", gen_copyright_xhtml())

        # 如果有封面图片
        has_cover_img = os.path.exists(COVER_IMG)
        if has_cover_img:
            with open(COVER_IMG, "rb") as f:
                zf.writestr("OEBPS/cover.png", f.read())
            print("  ✓ 封面图片已嵌入")

        # --- 处理章节 ---
        manifest_items = [
            ("css", "css/book.css", "text/css"),
            ("cover", "cover.xhtml", "application/xhtml+xml"),
            ("copyright", "copyright.xhtml", "application/xhtml+xml"),
            ("nav", "nav.xhtml", "application/xhtml+xml"),
        ]
        if has_cover_img:
            manifest_items.insert(2, ("cover-img", "cover.png", "image/png"))

        spine_ids = ["cover", "copyright", "nav"]
        nav_points = []
        toc_items = []

        for i, (filename, short_title, full_title) in enumerate(CHAPTERS):
            print(f"  [{short_title}] 处理中...", end=" ")
            md_text, filepath = read_chapter(filename)
            if not md_text:
                print("跳过（无内容）")
                continue

            # 去掉第一行的 H1 标题（与章节标题重复）
            lines = md_text.strip().split("\n")
            if lines[0].startswith("# ") and not lines[0].startswith("## "):
                lines = lines[1:]  # 去掉重复的 H1
            md_text = "\n".join(lines)

            html_body = md_to_html_simple(md_text)

            chapter_id = f"ch{i:02d}"
            ch_filename = f"{chapter_id}.xhtml"

            zf.writestr(f"OEBPS/{ch_filename}", gen_chapter_xhtml(chapter_id, full_title, html_body))

            manifest_items.append((chapter_id, ch_filename, "application/xhtml+xml"))
            spine_ids.append(chapter_id)
            nav_points.append((chapter_id, full_title, ch_filename))
            toc_items.append((chapter_id, full_title, ch_filename))
            print(f"✓ ({len(md_text)} 字符)")

        # --- nav.xhtml ---
        zf.writestr("OEBPS/nav.xhtml", gen_nav_xhtml(toc_items))

        # --- toc.ncx ---
        zf.writestr("OEBPS/toc.ncx", gen_toc_ncx(nav_points))

        # --- content.opf ---
        zf.writestr("OEBPS/content.opf", gen_content_opf(manifest_items, spine_ids))

    size_mb = os.path.getsize(epub_path) / (1024 * 1024)
    print(f"\n✅ EPUB 生成完成!")
    print(f"   {epub_path}")
    print(f"   文件大小: {size_mb:.2f} MB")
    print(f"   章节数: {len(toc_items)}")
    return epub_path


if __name__ == "__main__":
    build_epub()

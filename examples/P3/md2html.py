#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md2html.py —— 从 README-ARTICLE.md 自动生成 index.html
使用方法：
    cd /path/to/P1
    python3 md2html.py
"""

import re
import os

# ── HTML 模板（书籍风格）────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="author" content="森林瀑布">
    <title>{title}</title>
    <style>
        /* === 中文排版优化（继承书籍风格）=== */
        body {{
            font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
            font-size: 11pt;
            line-height: 1.9;
            color: #2c2c2c;
            text-align: justify;
            max-width: 800px;
            margin: 0 auto;
            padding: 2cm 1.5cm;
            background: #fafaf8;
        }}

        /* === 文章头部 === */
        .article-header {{
            text-align: center;
            margin-bottom: 2.5cm;
            padding-bottom: 1.5cm;
            border-bottom: 2px solid #e0e0e0;
        }}

        .article-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #533483, #e94560);
            color: white;
            padding: 0.2em 0.8em;
            border-radius: 4px;
            font-size: 10pt;
            font-weight: 600;
            letter-spacing: 0.05em;
            margin-bottom: 1em;
        }}

        .article-title {{
            font-size: 24pt;
            font-weight: 700;
            color: #1a1a2e;
            letter-spacing: 0.03em;
            margin: 0.5em 0;
            line-height: 1.4;
        }}

        .article-subtitle {{
            font-size: 13pt;
            color: #555;
            font-weight: 400;
            margin-bottom: 0.8em;
        }}

        .article-meta {{
            font-size: 10pt;
            color: #888;
            letter-spacing: 0.02em;
        }}

        .article-meta a {{
            color: #533483;
            text-decoration: none;
        }}

        /* === 章节标题 === */
        h1 {{
            font-size: 17pt;
            color: #1a1a2e;
            font-weight: 700;
            margin: 2em 0 0.8em;
            padding-bottom: 0.3em;
            border-bottom: 1px solid #e8e8e8;
            letter-spacing: 0.02em;
        }}

        h2 {{
            font-size: 14pt;
            color: #16213e;
            font-weight: 600;
            margin: 1.5em 0 0.6em;
            border-left: 4px solid #533483;
            padding-left: 0.6em;
        }}

        h3 {{
            font-size: 12pt;
            color: #0f3460;
            font-weight: 600;
            margin: 1.2em 0 0.5em;
        }}

        /* === 段落 === */
        p {{
            text-indent: 2em;
            margin: 0.5em 0;
            orphans: 2;
            widows: 2;
        }}

        p:first-of-type {{
            text-indent: 0;
        }}

        /* === 引用块 === */
        blockquote {{
            margin: 1em 1.5em;
            padding: 0.6em 1.2em;
            border-left: 4px solid #533483;
            background: #f8f8fc;
            color: #555;
            orphans: 3;
            widows: 3;
        }}

        blockquote p {{
            text-indent: 0;
            margin: 0.3em 0;
        }}

        /* === 强调 === */
        strong, b {{
            color: #16213e;
            font-weight: 700;
        }}

        em, i {{
            color: #0f3460;
            font-style: italic;
        }}

        /* === 代码 === */
        code {{
            background: #f0f0f5;
            padding: 0.15em 0.4em;
            border-radius: 3px;
            font-family: "SF Mono", "Fira Code", "Consolas", "Menlo", monospace;
            font-size: 9pt;
            color: #e94560;
        }}

        pre {{
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
            margin: 1em 0;
        }}

        pre code {{
            background: none;
            padding: 0;
            color: inherit;
            font-size: inherit;
        }}

        /* === 表格 === */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
            font-size: 10.5pt;
        }}

        th {{
            background: #1a1a2e;
            color: #eaeaea;
            padding: 0.5em 0.8em;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 0.4em 0.8em;
            border-bottom: 1px solid #e8e8e8;
            color: #333;
        }}

        tr:nth-child(even) td {{
            background: #f8f8fc;
        }}

        /* === 列表 === */
        ul, ol {{
            margin: 0.5em 0;
            padding-left: 2em;
        }}

        li {{
            margin: 0.3em 0;
        }}

        /* === 分割线 === */
        hr {{
            border: none;
            border-top: 1px solid #e0e0e0;
            margin: 2em 0;
        }}

        /* === 底部 === */
        .article-footer {{
            margin-top: 3em;
            padding-top: 1.5em;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #888;
            font-size: 10pt;
        }}

        .article-footer a {{
            color: #533483;
            text-decoration: none;
        }}

        /* === 响应式 === */
        @media (max-width: 600px) {{
            body {{
                padding: 1cm 1cm;
                font-size: 10.5pt;
            }}
            .article-title {{
                font-size: 20pt;
            }}
        }}
    </style>
</head>
<body>

{header}

{content}

{footer}

</body>
</html>"""

# ── Markdown 转 HTML 的核心逻辑 ──────────────────────────

def md_to_html(md_content):
    """将 Markdown 简易转换为 HTML（支持常用语法）"""
    lines = md_content.split('\n')
    html_lines = []
    in_code_block = False
    code_lang = ''
    code_lines = []
    in_table = False
    table_rows = []
    in_blockquote = False
    blockquote_lines = []
    in_list = False
    list_lines = []
    list_tag = 'ul'

    def flush_code():
        nonlocal code_lines, code_lang, in_code_block
        if code_lines:
            code = '\n'.join(code_lines)
            # 转义 HTML 特殊字符
            code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_lines.append(f'<pre><code class="{code_lang}">{code}</code></pre>')
        code_lines = []
        code_lang = ''
        in_code_block = False

    def flush_table():
        nonlocal table_rows, in_table
        if table_rows:
            html_lines.append('<table>')
            for i, row in enumerate(table_rows):
                cells = [c.strip() for c in row.split('|')[1:-1]]  # 去掉首尾空字符串
                if i == 0:
                    html_lines.append('<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>')
                elif i == 1 and all('-' in c for c in cells):
                    continue  # 跳过分隔行
                else:
                    html_lines.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
            html_lines.append('</table>')
        table_rows = []
        in_table = False

    def flush_blockquote():
        nonlocal blockquote_lines, in_blockquote
        if blockquote_lines:
            content = '\n'.join(blockquote_lines)
            # 递归处理 blockquote 内的 Markdown
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
            html_lines.append('<blockquote>' + content + '</blockquote>')
        blockquote_lines = []
        in_blockquote = False

    def flush_list():
        nonlocal list_lines, in_list, list_tag
        if list_lines:
            html_lines.append(f'<{list_tag}>')
            for line in list_lines:
                # 处理加粗、斜体、代码
                line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
                line = re.sub(r'`(.+?)`', r'<code>\1</code>', line)
                html_lines.append(f'<li>{line}</li>')
            html_lines.append(f'</{list_tag}>')
        list_lines = []
        in_list = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 代码块
        if stripped.startswith('```'):
            if not in_code_block:
                flush_blockquote()
                flush_table()
                flush_list()
                in_code_block = True
                code_lang = stripped[3:].strip()
            else:
                flush_code()
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # 表格检测
        if '|' in stripped and stripped.startswith('|'):
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(stripped)
            i += 1
            continue
        else:
            if in_table:
                flush_table()

        # 引用块
        if stripped.startswith('>'):
            if not in_blockquote:
                flush_table()
                flush_list()
                in_blockquote = True
                blockquote_lines = []
            # 去掉 > 和可能的空格
            content = re.sub(r'^>\s?', '', stripped)
            blockquote_lines.append(f'<p>{content}</p>')
            i += 1
            continue
        else:
            if in_blockquote:
                flush_blockquote()

        # 列表
        if re.match(r'^(\d+\.|[-*+])\s', stripped):
            if not in_list:
                flush_table()
                flush_blockquote()
                in_list = True
                list_lines = []
                list_tag = 'ol' if re.match(r'^\d+\.', stripped) else 'ul'
            # 去掉列表标记
            content = re.sub(r'^(\d+\.|[-*+])\s', '', stripped)
            list_lines.append(content)
            i += 1
            continue
        else:
            if in_list:
                flush_list()

        # 标题
        h_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if h_match:
            flush_table()
            flush_blockquote()
            flush_list()
            level = len(h_match.group(1))
            content = h_match.group(2)
            # 处理加粗、斜体
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f'<h{level}>{content}</h{level}>')
            i += 1
            continue

        # 分割线
        if re.match(r'^[-*_]{3,}\s*$', stripped):
            flush_table()
            flush_blockquote()
            flush_list()
            html_lines.append('<hr>')
            i += 1
            continue

        # 空行 → 段落分隔
        if stripped == '':
            flush_table()
            flush_blockquote()
            flush_list()
            html_lines.append('')
            i += 1
            continue

        # 普通段落
        flush_table()
        flush_blockquote()
        flush_list()

        # 处理加粗、斜体、代码、链接
        content = stripped
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
        content = re.sub(r'`(.+?)`', r'<code>\1</code>', content)
        content = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', content)

        html_lines.append(f'<p>{content}</p>')
        i += 1

    # 文件末尾刷新
    flush_code()
    flush_table()
    flush_blockquote()
    flush_list()

    return '\n'.join(html_lines)


def extract_header(md_content):
    """从 Markdown 提取文章头部信息"""
    lines = md_content.split('\n')
    
    # 提取标题（第一个 # 开头的行）
    title = ''
    for line in lines:
        if line.startswith('# '):
            title = line[2:].strip()
            break
    
    # 提取 badge（> 开头的 blockquote）
    badge = ''
    subtitle = ''
    meta = ''
    in_meta_block = False
    
    for line in lines:
        if line.startswith('> ') and badge == '':
            badge = line[2:].strip()
        elif line.startswith('> ') and badge != '' and subtitle == '':
            subtitle = line[2:].strip()
        elif line.startswith('**') and '作者' in line:
            meta = line.strip()
            break
    
    # 构造 HTML 头部
    header_html = f'''<div class="article-header">
    <div class="article-badge">{badge}</div>
    <h1 class="article-title">{title}</h1>
    <p class="article-subtitle">{subtitle}</p>
    <p class="article-meta">{meta}</p>
</div>'''
    
    return header_html, title


def extract_footer(md_content):
    """生成文章底部"""
    footer_html = '''<div class="article-footer">
    <p>« <a href="../">返回 OntologyOps 首页</a> &nbsp;|&nbsp; <a href="../book/">在线阅读全书</a> »</p>
    <p style="margin-top:1em;">作者：森林瀑布 &nbsp;|&nbsp; 项目类型：多范式推理实战营 P3/6</p>
</div>'''
    return footer_html


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(script_dir, 'README-ARTICLE.md')
    html_path = os.path.join(script_dir, 'index.html')

    if not os.path.exists(md_path):
        print(f'❌ 找不到 {md_path}')
        return

    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # 提取头部和底部
    header_html, title = extract_header(md_content)
    footer_html = extract_footer(md_content)

    # 去掉 Markdown 中的元数据行（已经放到 header 中了）
    lines = md_content.split('\n')
    content_start = 0
    for i, line in enumerate(lines):
        if line.startswith('**作者**'):
            content_start = i + 1
            break
    
    content_md = '\n'.join(lines[content_start:]) if content_start > 0 else md_content
    
    # 转换 Markdown 为 HTML
    content_html = md_to_html(content_md)

    # 组装完整 HTML
    html = HTML_TEMPLATE.format(
        title=title + ' — 多范式推理实战营',
        header=header_html,
        content=content_html,
        footer=footer_html
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'✅ 已从 {md_path} 生成 {html_path}')


if __name__ == '__main__':
    main()

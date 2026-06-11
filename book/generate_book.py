#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成单页 HTML 在线书籍阅读器
读取所有 Markdown 章节文件，生成完整的 HTML 文件
"""

import os
import re
import json

# 章节文件列表（按顺序）
CHAPS_DIR = "/Users/siidt/Documents/code/1petpri-main/ontologyops/chapters"

CHAPTERS = [
    (f"{CHAPS_DIR}/序言-为什么现在是时候了.md", "序言", "序言：为什么现在是时候了"),
    (f"{CHAPS_DIR}/第一章-本体论是什么.md", "第一章", "第一章：本体论是什么（以及它不是什么）"),
    (f"{CHAPS_DIR}/第二章-企业为什么需要本体推理.md", "第二章", "第二章：企业为什么需要本体推理？"),
    (f"{CHAPS_DIR}/第三章-本体落地的认知工程.md", "第三章", "第三章：本体落地——一场不亚于管理咨询的认知工程"),
    (f"{CHAPS_DIR}/第四章-本体推理的技术基础设施.md", "第四章", "第四章：本体推理的技术基础设施"),
    (f"{CHAPS_DIR}/第五章-企业级本体推理架构设计.md", "第五章", "第五章：企业级本体推理架构设计"),
    (f"{CHAPS_DIR}/第六章-Palantir-Foundry深度剖析.md", "第六章", "第六章：Palantir Foundry 深度剖析"),
    (f"{CHAPS_DIR}/第七章-中数睿智-动态本体引擎.md", "第七章", "第七章：中数睿智——本体推理的中国答案"),
    (f"{CHAPS_DIR}/第八章-GraphRAG与本体增强的大模型应用.md", "第八章", "第八章：GraphRAG 与本体增强的大模型应用"),
    (f"{CHAPS_DIR}/第九章-打造你的第一条企业决策推理链.md", "第九章", "第九章：打造你的第一条企业决策推理链"),
    (f"{CHAPS_DIR}/第十章-OntologyOps.md", "第十章", "第十章：OntologyOps——让本体像代码一样被管理"),
    (f"{CHAPS_DIR}/后记-从工具到思维.md", "后记", "后记：从工具到思维——本体论的方法论意义"),
]

def read_file(filepath):
    """读取文件内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def md_to_html(md_text):
    """简单的 Markdown 到 HTML 转换器"""
    lines = md_text.split('\n')
    html_lines = []
    in_code_block = False
    code_lines = []
    code_lang = ''
    in_table = False
    table_rows = []
    in_blockquote = False
    blockquote_lines = []
    in_list = False
    list_lines = []
    list_tag = 'ul'
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 代码块
        if line.startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_lang = line[3:].strip()
                code_lines = []
            else:
                # 结束代码块
                code_content = '\n'.join(code_lines)
                code_content = code_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_lines.append(f'<pre><code class="language-{code_lang}">{code_content}</code></pre>')
                in_code_block = False
                code_lines = []
                code_lang = ''
            i += 1
            continue
        
        if in_code_block:
            code_lines.append(line)
            i += 1
            continue
        
        # 空行
        if line.strip() == '':
            if in_blockquote:
                html_lines.append(f'<blockquote>{"<br>".join(blockquote_lines)}</blockquote>')
                in_blockquote = False
                blockquote_lines = []
            if in_list:
                html_lines.append('<' + list_tag + '>' + '\n'.join(list_lines) + '</' + list_tag + '>')
                in_list = False
                list_lines = []
            i += 1
            continue
        
        # 标题
        if line.startswith('# '):
            html_lines.append(f'<h1>{inline_md(line[2:])}</h1>')
        elif line.startswith('## '):
            html_lines.append(f'<h2>{inline_md(line[3:])}</h2>')
        elif line.startswith('### '):
            html_lines.append(f'<h3>{inline_md(line[4:])}</h3>')
        elif line.startswith('#### '):
            html_lines.append(f'<h4>{inline_md(line[5:])}</h4>')
        # 水平线
        elif re.match(r'^---+$', line.strip()) or re.match(r'^\*\*\*+$', line.strip()):
            html_lines.append('<hr>')
        # 表格
        elif '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_rows = [line]
            else:
                table_rows.append(line)
                # 检查下一行是否也是表格行
                if i + 1 >= len(lines) or not lines[i+1].strip().startswith('|'):
                    html_lines.append(parse_table(table_rows))
                    in_table = False
                    table_rows = []
        # 引用
        elif line.startswith('> '):
            if not in_blockquote:
                in_blockquote = True
                blockquote_lines = [inline_md(line[2:])]
            else:
                blockquote_lines.append(inline_md(line[2:]))
        # 无序列表
        elif re.match(r'^[\*\-\+] ', line):
            if not in_list or list_tag != 'ul':
                if in_list:
                    html_lines.append('<' + list_tag + '>' + '\n'.join(list_lines) + '</' + list_tag + '>')
                in_list = True
                list_tag = 'ul'
                list_lines = []
            list_content = line[line.index(' ')+1:]
            list_lines.append(f'<li>{inline_md(list_content)}</li>')
        # 有序列表
        elif re.match(r'^\d+\. ', line):
            if not in_list or list_tag != 'ol':
                if in_list:
                    html_lines.append('<' + list_tag + '>' + '\n'.join(list_lines) + '</' + list_tag + '>')
                in_list = True
                list_tag = 'ol'
                list_lines = []
            list_content = line[line.index(' ')+1:]
            list_lines.append(f'<li>{inline_md(list_content)}</li>')
        # 普通段落
        else:
            html_lines.append(f'<p>{inline_md(line)}</p>')
        
        i += 1
    
    # 处理文件末尾未关闭的块
    if in_blockquote:
        html_lines.append(f'<blockquote>{"<br>".join(blockquote_lines)}</blockquote>')
    if in_list:
        html_lines.append('<' + list_tag + '>' + '\n'.join(list_lines) + '</' + list_tag + '>')
    
    return '\n'.join(html_lines)

def inline_md(text):
    """处理行内 Markdown"""
    # 转义 HTML
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # 粗体 **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 粗体 __text__
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # 斜体 *text*
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # 斜体 _text_
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
    # 行内代码 `code`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # 链接 [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    # 图片 ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', r'<img src="\2" alt="\1">', text)
    return text

def parse_table(rows):
    """解析 Markdown 表格"""
    if len(rows) < 2:
        return ''
    
    html = '<table>\n<thead>\n<tr>\n'
    # 表头
    headers = [c.strip() for c in rows[0].split('|') if c.strip()]
    for h in headers:
        html += f'<th>{h}</th>\n'
    html += '</tr>\n</thead>\n<tbody>\n'
    
    # 跳过分隔行（第二行）
    for row in rows[2:]:
        cells = [c.strip() for c in row.split('|') if c.strip()]
        html += '<tr>\n'
        for cell in cells:
            html += f'<td>{cell}</td>\n'
        html += '</tr>\n'
    
    html += '</tbody>\n</table>'
    return html

def main():
    # 读取所有章节内容并转换为 HTML
    chapters_html = []
    toc_items = []
    
    for i, (filepath, short_title, full_title) in enumerate(CHAPTERS):
        print(f"读取并处理: {filepath}")
        md_content = read_file(filepath)
        html_content = md_to_html(md_content)
        chapters_html.append({
            'index': i,
            'short_title': short_title,
            'full_title': full_title,
            'html': html_content
        })
        # 生成目录项
        display_title = full_title.split('：')[-1] if '：' in full_title else full_title
        toc_items.append(f'<li><a href="#chapter-{i}" data-chapter="{i}">{short_title} {display_title}</a></li>')
    
    # 生成完整的 HTML 文件
    html_output = generate_html(chapters_html, toc_items)
    
    # 写入文件
    output_path = "/Users/siidt/Documents/code/1petpri-main/ontologyops/book/index.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    print(f"\n生成完成: {output_path}")
    print(f"文件大小: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")

def generate_html(chapters_html, toc_items):
    """生成完整的 HTML 内容"""
    
    # 生成章节 HTML 数据（用于 JavaScript）
    js_chapters = []
    for ch in chapters_html:
        # 将 HTML 转义后存入 JS 字符串
        escaped_html = ch['html'].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        js_chapters.append(f'    "{ch["index"]}": {{ short_title: "{ch["short_title"]}", full_title: "{ch["full_title"]}", html: "{escaped_html}" }}')
    
    js_object = "{\n" + ",\n".join(js_chapters) + "\n}"
    
    # 生成目录 HTML
    toc_html = '\n'.join(toc_items)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>当LLM不够用了——本体推理的企业决策实践</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
            display: flex;
            height: 100vh;
            overflow: hidden;
            background: #fafaf8;
        }}

        .sidebar {{
            width: 270px;
            min-width: 270px;
            background: #1c1c1f;
            color: #c4c0b8;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
            border-right: 1px solid #2a2a2e;
            box-shadow: 2px 0 20px rgba(0,0,0,0.15);
            z-index: 10;
        }}

        .sidebar-header {{
            padding: 28px 24px 20px;
            border-bottom: 1px solid #2a2a2e;
        }}

        .sidebar-header h1 {{
            font-size: 15px;
            font-weight: 600;
            color: #e8e0d0;
            line-height: 1.5;
            margin-bottom: 10px;
            letter-spacing: 0.02em;
        }}

        .sidebar-header .author {{
            font-size: 12px;
            color: #8a857c;
            margin-bottom: 10px;
            letter-spacing: 0.03em;
        }}

        .sidebar-header .github-link {{
            font-size: 11px;
            color: #6e6860;
            text-decoration: none;
            display: inline-block;
            transition: color 0.2s;
        }}

        .sidebar-header .github-link:hover {{
            color: #c9a96e;
        }}

        .sidebar-toc {{
            flex: 1;
            overflow-y: auto;
            padding: 12px 0;
        }}

        .sidebar-toc ul {{
            list-style: none;
        }}

        .sidebar-toc li {{
            position: relative;
        }}

        .sidebar-toc li a {{
            display: block;
            padding: 10px 24px;
            color: #9a958b;
            text-decoration: none;
            font-size: 13px;
            line-height: 1.5;
            transition: all 0.2s ease;
            border-left: 2px solid transparent;
            letter-spacing: 0.01em;
        }}

        .sidebar-toc li a:hover {{
            background: #262629;
            color: #d4cfc5;
            border-left-color: #4a4a50;
        }}

        .sidebar-toc li a.active {{
            background: #262629;
            color: #c9a96e;
            border-left-color: #c9a96e;
            font-weight: 500;
        }}

        .sidebar-footer {{
            padding: 16px 24px;
            border-top: 1px solid #2a2a2f;
            text-align: center;
        }}

        .sidebar-toggle {{
            display: none;
            position: fixed;
            top: 16px;
            left: 16px;
            z-index: 1000;
            background: #1c1c1f;
            color: #c9a96e;
            border: 1px solid #3a3a3f;
            padding: 8px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 18px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.3);
        }}

        .content {{
            flex: 1;
            overflow-y: auto;
            background: #fcfbf8;
            padding: 48px 64px;
            max-width: 900px;
            margin: 0 auto;
        }}

        .content h1 {{
            font-size: 26px;
            font-weight: 700;
            color: #1c1c1f;
            margin-bottom: 12px;
            padding-bottom: 16px;
            border-bottom: 2px solid #e0d8c8;
            letter-spacing: 0.02em;
        }}

        .content h2 {{
            font-size: 21px;
            font-weight: 600;
            color: #2a2824;
            margin-top: 36px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e8e4da;
            letter-spacing: 0.01em;
        }}

        .content h3 {{
            font-size: 17px;
            font-weight: 600;
            color: #3d3a34;
            margin-top: 28px;
            margin-bottom: 12px;
        }}

        .content p {{
            font-size: 15px;
            line-height: 1.85;
            color: #3d3a34;
            margin-bottom: 16px;
        }}

        .content strong {{
            color: #1c1c1f;
            font-weight: 600;
        }}

        .content em {{
            color: #6e6860;
            font-style: italic;
        }}

        .content code {{
            background: #f0ede5;
            padding: 2px 7px;
            border-radius: 3px;
            font-family: "SFMono-Regular", "Fira Code", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 13px;
            color: #b5452a;
        }}

        .content pre {{
            background: #1c1c1f;
            color: #d4cfc5;
            padding: 18px 22px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 18px 0;
            font-size: 13px;
            line-height: 1.7;
            border: 1px solid #2a2a2e;
        }}

        .content pre code {{
            background: none;
            color: inherit;
            padding: 0;
        }}

        .content blockquote {{
            border-left: 3px solid #c9a96e;
            padding: 12px 20px;
            margin: 18px 0;
            background: #f7f4ec;
            color: #5a554a;
            border-radius: 0 6px 6px 0;
            font-size: 14px;
        }}

        .content blockquote p {{
            margin-bottom: 8px;
            font-size: 14px;
            line-height: 1.75;
        }}

        .content blockquote p:last-child {{
            margin-bottom: 0;
        }}

        .content ul, .content ol {{
            margin: 16px 0;
            padding-left: 28px;
        }}

        .content li {{
            font-size: 15px;
            line-height: 1.85;
            color: #3d3a34;
            margin-bottom: 8px;
        }}

        .content li::marker {{
            color: #c9a96e;
        }}

        .content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 22px 0;
            font-size: 14px;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }}

        .content th {{
            background: #2d2b26;
            color: #e8e0d0;
            padding: 11px 16px;
            text-align: left;
            font-weight: 500;
            font-size: 13px;
            letter-spacing: 0.02em;
        }}

        .content td {{
            padding: 9px 16px;
            border-bottom: 1px solid #e8e4da;
            color: #3d3a34;
        }}

        .content tr:nth-child(even) td {{
            background: #f8f6f0;
        }}

        .content tr:hover td {{
            background: #f3efe5;
        }}

        .content hr {{
            border: none;
            border-top: 1px solid #e0d8c8;
            margin: 32px 0;
        }}

        .content a {{
            color: #8b6914;
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: border-color 0.2s;
        }}

        .content a:hover {{
            border-bottom-color: #8b6914;
        }}

        .content img {{
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            margin: 18px 0;
        }}

        @media (max-width: 768px) {{
            body {{
                flex-direction: column;
            }}

            .sidebar {{
                position: fixed;
                top: 0;
                left: 0;
                height: 100vh;
                z-index: 999;
                transform: translateX(-100%);
            }}

            .sidebar.open {{
                transform: translateX(0);
            }}

            .sidebar-toggle {{
                display: block;
            }}

            .content {{
                padding: 56px 20px 24px;
                max-width: 100%;
            }}

            .content h1 {{ font-size: 22px; }}
            .content h2 {{ font-size: 18px; }}
            .content h3 {{ font-size: 16px; }}
        }}

        .sidebar-toc::-webkit-scrollbar {{
            width: 4px;
        }}
        .sidebar-toc::-webkit-scrollbar-track {{
            background: transparent;
        }}
        .sidebar-toc::-webkit-scrollbar-thumb {{
            background: #3a3a3f;
            border-radius: 2px;
        }}

        .content::-webkit-scrollbar {{
            width: 6px;
        }}
        .content::-webkit-scrollbar-track {{
            background: transparent;
        }}
        .content::-webkit-scrollbar-thumb {{
            background: #d0ccc0;
            border-radius: 3px;
        }}
        .content::-webkit-scrollbar-thumb:hover {{
            background: #b0aca0;
        }}

        @media print {{
            .sidebar, .sidebar-toggle {{ display: none; }}
            .content {{ max-width: 100%; padding: 0; }}
        }}
    </style>
</head>
<body>
    <button class="sidebar-toggle" onclick="toggleSidebar()">☰</button>
    
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h1>当LLM不够用了<br>——本体推理的企业决策实践</h1>
            <div class="author">作者：森林瀑布</div>
            <a class="github-link" href="https://github.com/georgewangchn/OntologyOps" target="_blank">📖 GitHub: georgewangchn/OntologyOps</a>
        </div>
        <nav class="sidebar-toc">
            <ul id="toc-list">
                {toc_html}
            </ul>
        </nav>
        <div class="sidebar-footer">
            <a href="https://github.com/georgewangchn/OntologyOps/blob/main/LICENSE-BOOK" target="_blank" style="font-size:12px; color:#6e6860;">📜 书籍 CC BY-NC-SA 4.0 · 代码 MIT</a>
        </div>
    </div>

    <div class="content" id="content">
        <div id="chapter-content">
            <p>加载中...</p>
        </div>
    </div>

    <script>
        // 章节数据
        const chapters = {js_object};

        // 加载章节
        function loadChapter(index) {{
            const chapter = chapters[index];
            if (!chapter) return;
            
            // 更新目录高亮
            document.querySelectorAll(".sidebar-toc a").forEach(a => {{
                a.classList.remove("active");
            }});
            const activeLink = document.querySelector(`.sidebar-toc a[data-chapter="${{index}}"]`);
            if (activeLink) activeLink.classList.add("active");
            
            // 渲染内容
            document.getElementById("chapter-content").innerHTML = chapter.html;
            
            // 更新 URL hash
            window.location.hash = `chapter-${{index}}`;
            
            // 滚动到顶部
            document.getElementById("content").scrollTop = 0;
            
            // 关闭移动端侧边栏
            if (window.innerWidth <= 768) {{
                document.getElementById("sidebar").classList.remove("open");
            }}
        }}

        // 切换侧边栏（移动端）
        function toggleSidebar() {{
            document.getElementById("sidebar").classList.toggle("open");
        }}

        // 初始化
        function init() {{
            // 检查 URL hash
            const hash = window.location.hash;
            if (hash && hash.startsWith("#chapter-")) {{
                const index = parseInt(hash.substring(9));
                if (!isNaN(index) && chapters[index]) {{
                    loadChapter(index);
                    return;
                }}
            }}
            // 默认加载序言
            loadChapter(0);
        }}

        // 页面加载完成后初始化
        document.addEventListener("DOMContentLoaded", init);
        
        // 监听 hash 变化
        window.addEventListener("hashchange", function() {{
            const hash = window.location.hash;
            if (hash && hash.startsWith("#chapter-")) {{
                const index = parseInt(hash.substring(9));
                if (!isNaN(index) && chapters[index]) {{
                    loadChapter(index);
                }}
            }}
        }});
    </script>
</body>
</html>'''
    
    return html

if __name__ == "__main__":
    main()

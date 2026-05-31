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
CHAPTERS = [
    ("/Users/siidt/Documents/code/1petpri-main/序言-为什么现在是时候了.md", "序言", "序言：为什么现在是时候了"),
    ("/Users/siidt/Documents/code/1petpri-main/第一章-本体论是什么.md", "第一章", "第一章：本体论是什么（以及它不是什么）"),
    ("/Users/siidt/Documents/code/1petpri-main/第二章-企业为什么需要本体推理.md", "第二章", "第二章：企业为什么需要本体推理？"),
    ("/Users/siidt/Documents/code/1petpri-main/第三章-本体落地的认知工程.md", "第三章", "第三章：本体落地——一场不亚于管理咨询的认知工程"),
    ("/Users/siidt/Documents/code/1petpri-main/第四章-本体推理的技术基础设施.md", "第四章", "第四章：本体推理的技术基础设施"),
    ("/Users/siidt/Documents/code/1petpri-main/第五章-企业级本体推理架构设计.md", "第五章", "第五章：企业级本体推理架构设计"),
    ("/Users/siidt/Documents/code/1petpri-main/第六章-Palantir-Foundry深度剖析.md", "第六章", "第六章：Palantir Foundry 深度剖析"),
    ("/Users/siidt/Documents/code/1petpri-main/第七章-优锘科技与本体神经网络.md", "第七章", "第七章：国内实践——优锘科技与本体神经网络"),
    ("/Users/siidt/Documents/code/1petpri-main/第八章-GraphRAG与本体增强的大模型应用.md", "第八章", "第八章：GraphRAG 与本体增强的大模型应用"),
    ("/Users/siidt/Documents/code/1petpri-main/第九章-打造你的第一条企业决策推理链.md", "第九章", "第九章：打造你的第一条企业决策推理链"),
    ("/Users/siidt/Documents/code/1petpri-main/ontologyops/docs/OntologyOps方案.md", "第十章", "第十章：OntologyOps——让本体像代码一样被管理"),
    ("/Users/siidt/Documents/code/1petpri-main/后记-从工具到思维.md", "后记", "后记：从工具到思维——本体论的方法论意义"),
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
            background: #f5f5f5;
        }}

        /* 左侧边栏 */
        .sidebar {{
            width: 260px;
            min-width: 260px;
            background: #1a1a2e;
            color: #e0e0e0;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: transform 0.3s ease;
        }}

        .sidebar-header {{
            padding: 20px;
            border-bottom: 1px solid #2a2a4e;
        }}

        .sidebar-header h1 {{
            font-size: 16px;
            font-weight: 600;
            color: #ffffff;
            line-height: 1.4;
            margin-bottom: 8px;
        }}

        .sidebar-header .author {{
            font-size: 12px;
            color: #8888aa;
        }}

        .sidebar-header .github-link {{
            font-size: 11px;
            color: #6666aa;
            text-decoration: none;
            display: inline-block;
            margin-top: 6px;
        }}

        .sidebar-header .github-link:hover {{
            color: #8888ff;
        }}

        .sidebar-toc {{
            flex: 1;
            overflow-y: auto;
            padding: 10px 0;
        }}

        .sidebar-toc ul {{
            list-style: none;
        }}

        .sidebar-toc li a {{
            display: block;
            padding: 8px 20px;
            color: #aaaacc;
            text-decoration: none;
            font-size: 13px;
            transition: all 0.2s;
            border-left: 3px solid transparent;
        }}

        .sidebar-toc li a:hover {{
            background: #2a2a4e;
            color: #ffffff;
        }}

        .sidebar-toc li a.active {{
            background: #2a2a4e;
            color: #6c63ff;
            border-left-color: #6c63ff;
            font-weight: 500;
        }}

        /* 移动端侧边栏切换按钮 */
        .sidebar-toggle {{
            display: none;
            position: fixed;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: #1a1a2e;
            color: #ffffff;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 18px;
        }}

        /* 右侧内容区 */
        .content {{
            flex: 1;
            overflow-y: auto;
            background: #ffffff;
            padding: 40px 60px;
        }}

        .content h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 10px;
            padding-bottom: 15px;
            border-bottom: 2px solid #6c63ff;
        }}

        .content h2 {{
            font-size: 22px;
            font-weight: 600;
            color: #2a2a4e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .content h3 {{
            font-size: 18px;
            font-weight: 600;
            color: #3a3a5e;
            margin-top: 25px;
            margin-bottom: 12px;
        }}

        .content p {{
            font-size: 15px;
            line-height: 1.8;
            color: #333333;
            margin-bottom: 15px;
        }}

        .content strong {{
            color: #1a1a2e;
            font-weight: 600;
        }}

        .content em {{
            color: #555577;
            font-style: italic;
        }}

        .content code {{
            background: #f0f0f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 13px;
            color: #d63384;
        }}

        .content pre {{
            background: #1a1a2e;
            color: #e0e0e0;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 15px 0;
            font-size: 13px;
            line-height: 1.6;
        }}

        .content pre code {{
            background: none;
            color: inherit;
            padding: 0;
        }}

        .content blockquote {{
            border-left: 4px solid #6c63ff;
            padding: 10px 20px;
            margin: 15px 0;
            background: #f8f8ff;
            color: #555577;
            font-style: italic;
        }}

        .content blockquote p {{
            margin-bottom: 8px;
        }}

        .content blockquote p:last-child {{
            margin-bottom: 0;
        }}

        .content ul, .content ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}

        .content li {{
            font-size: 15px;
            line-height: 1.8;
            color: #333333;
            margin-bottom: 8px;
        }}

        .content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}

        .content th {{
            background: #1a1a2e;
            color: #ffffff;
            padding: 10px 15px;
            text-align: left;
            font-weight: 600;
            border: 1px solid #2a2a4e;
        }}

        .content td {{
            padding: 8px 15px;
            border: 1px solid #e0e0e0;
        }}

        .content tr:nth-child(even) td {{
            background: #f8f8ff;
        }}

        .content tr:hover td {{
            background: #f0f0ff;
        }}

        .content hr {{
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 30px 0;
        }}

        .content a {{
            color: #6c63ff;
            text-decoration: none;
        }}

        .content a:hover {{
            text-decoration: underline;
        }}

        .content img {{
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            margin: 15px 0;
        }}

        /* 响应式设计 */
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
                padding: 60px 20px 20px;
            }}
        }}

        /* 滚动条样式 */
        .sidebar-toc::-webkit-scrollbar,
        .content::-webkit-scrollbar {{
            width: 6px;
        }}

        .sidebar-toc::-webkit-scrollbar-track,
        .content::-webkit-scrollbar-track {{
            background: transparent;
        }}

        .sidebar-toc::-webkit-scrollbar-thumb,
        .content::-webkit-scrollbar-thumb {{
            background: #3a3a5e;
            border-radius: 3px;
        }}

        .content::-webkit-scrollbar-thumb {{
            background: #c0c0c0;
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

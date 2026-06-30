#!/usr/bin/env python3
"""
CSDN博客自动发布脚本
用法: python csdn_publish.py
首次使用需要先通过浏览器抓取Cookie，填入 .csdn_cookie 文件
"""

import json
import os
import time
import glob
import re
import requests
from pathlib import Path

# ============================================================
# 配置区域
# ============================================================
COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".csdn_cookie")
CHAPTERS_DIR = "/Users/siidt/Documents/code/1petpri-main/ontologyops/chapters"
PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".csdn_progress")
DELAY_SECONDS = 5  # 每篇发布间隔(秒)

# CSDN API
CSDN_SAVE_URL = "https://bizapi.csdn.net/blog-console-api/v3/mdeditor/saveArticle"

# 发布顺序
PUBLISH_ORDER = [
    "序言-为什么现在是时候了.md",
    "第一章-本体论是什么.md",
    "第二章-企业为什么需要本体推理.md",
    "第三章-本体落地的认知工程.md",
    "第四章-本体推理的技术基础设施.md",
    "第五章-企业级本体推理架构设计.md",
    "第六章-Palantir-Foundry深度剖析.md",
    "第七章-优锘科技与本体神经网络.md",
    "第八章-GraphRAG与本体增强的大模型应用.md",
    "第九章-打造你的第一条企业决策推理链.md",
    "第十章-OntologyOps.md",
    "后记-从工具到思维.md",
]

# 每章的标签
CHAPTER_TAGS = {
    "序言": "前沿,本体论,LLM,OntologyOps,AI架构",
    "第一章": "本体论,OWL,知识图谱,AI,语义网",
    "第二章": "企业架构,本体推理,知识工程,数字化转型,AI",
    "第三章": "认知工程,本体建模,知识管理,企业落地,OWL",
    "第四章": "OWL,推理机,RDF,SPARQL,知识图谱",
    "第五章": "架构设计,本体推理,企业架构,微服务,知识中台",
    "第六章": "Palantir,Foundry,本体,数据分析,企业AI",
    "第七章": "优锘科技,本体神经网络,知识图谱,AI,数字孪生",
    "第八章": "GraphRAG,LLM,本体增强,知识图谱,RAG",
    "第九章": "推理链,实战教程,供应链,SWRL,OWL",
    "第十章": "OntologyOps,LLM,本体运维,工程化,自动化",
    "后记": "思维方式,本体论,方法论,技术展望,AI",
}


def load_cookie():
    """从文件加载Cookie"""
    if not os.path.exists(COOKIE_FILE):
        print("❌ 未找到Cookie文件!")
        print(f"请创建 {COOKIE_FILE} 文件，内容为你的CSDN登录Cookie字符串")
        print("\n获取方法:")
        print("1. 用浏览器登录 https://www.csdn.net")
        print("2. 按F12打开开发者工具 → Network标签")
        print("3. 访问 https://mp.csdn.net/mp_blog/creation/editor")
        print("4. 找到任意请求，复制Cookie请求头的值")
        print(f"5. 粘贴到 {COOKIE_FILE} 文件中")
        return None
    with open(COOKIE_FILE, "r") as f:
        cookie = f.read().strip()
    if not cookie:
        print("❌ Cookie文件为空!")
        return None
    return cookie


def load_progress():
    """加载已发布进度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"published": []}


def save_progress(progress):
    """保存发布进度"""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def extract_chapter_key(filename):
    """从文件名提取章节key，用于匹配标签"""
    if "序言" in filename:
        return "序言"
    if "后记" in filename:
        return "后记"
    # 提取 "第X章" 部分
    match = re.search(r"第[一二三四五六七八九十]+章", filename)
    if match:
        return match.group()
    return None


def get_tags(filename):
    """获取章节对应的标签"""
    key = extract_chapter_key(filename)
    if key and key in CHAPTER_TAGS:
        return CHAPTER_TAGS[key]
    return "技术,AI,本体论,知识图谱"


def build_csdn_title(filename, content):
    """
    构建CSDN文章标题
    CSDN标题限制100字符，比小红书宽松很多，可以用完整标题
    """
    # 从文件内容提取一级标题
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            # 去掉markdown加粗标记
            title = re.sub(r"\*\*(.+?)\*\*", r"\1", title)
            return title[:100]
    
    # 从文件名构造标题
    base = Path(filename).stem
    return base[:100]


def build_description(content, max_len=200):
    """从内容生成文章摘要"""
    # 去掉markdown标记，取前200字
    text = re.sub(r"#{1,6}\s+", "", content)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"[-*]\s+", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = text.strip()
    return text[:max_len] + "..." if len(text) > max_len else text


def publish_article(cookie, title, markdown_content, tags, description):
    """调用CSDN API发布文章"""
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/json;charset=UTF-8",
        "Cookie": cookie,
        "Origin": "https://mp.csdn.net",
        "Referer": "https://mp.csdn.net/mp_blog/creation/editor",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }

    payload = {
        "title": title,
        "markdowncontent": markdown_content,
        "content": markdown_content,  # CSDN编辑器会自动渲染markdown
        "htmlcontent": "",  # 留空让CSDN自行处理
        "readType": "public",  # 公开
        "tags": tags,
        "description": description,
        "status": 0,  # 0=发布
        "type": "original",  # 原创
        "source": "pc_mdeditor",
        "pubStatus": "publish",
        "art_id": 0,  # 新文章
        "cover_url": "",  # 无封面
        "cover_type": 1,
        "is_new": 1,
        "vote_id": 0,
        "resource_id": "",
    }

    try:
        resp = requests.post(CSDN_SAVE_URL, headers=headers, json=payload, timeout=30)
        result = resp.json()
        
        if result.get("code") == 200:
            data = result.get("data", {})
            article_id = data.get("art_id", "")
            article_url = data.get("url", "")
            print(f"  ✅ 发布成功! ID: {article_id}")
            if article_url:
                print(f"  🔗 {article_url}")
            return True, article_id
        else:
            error_msg = result.get("message", "未知错误")
            print(f"  ❌ 发布失败: {error_msg}")
            print(f"  📋 响应: {json.dumps(result, ensure_ascii=False)[:300]}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ 网络错误: {e}")
        return False, None


def main():
    print("=" * 60)
    print("📚 CSDN博客自动发布 - 当LLM不够用了")
    print("=" * 60)
    
    # 加载Cookie
    cookie = load_cookie()
    if not cookie:
        return
    
    # 加载进度
    progress = load_progress()
    published = progress.get("published", [])
    print(f"\n📋 已发布: {len(published)} 篇")
    
    # 扫描章节
    chapters_to_publish = []
    for filename in PUBLISH_ORDER:
        filepath = os.path.join(CHAPTERS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"⚠️  文件不存在: {filename}")
            continue
        if filename in published:
            print(f"⏭️  已发布,跳过: {filename}")
            continue
        chapters_to_publish.append((filename, filepath))
    
    if not chapters_to_publish:
        print("\n🎉 全部已发布!")
        return
    
    print(f"\n📝 待发布: {len(chapters_to_publish)} 篇\n")
    
    success_count = 0
    for i, (filename, filepath) in enumerate(chapters_to_publish):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        title = build_csdn_title(filename, content)
        tags = get_tags(filename)
        description = build_description(content)
        
        print(f"[{i+1}/{len(chapters_to_publish)}] 发布: {title}")
        print(f"  📁 {filename}")
        print(f"  🏷️  标签: {tags}")
        
        ok, article_id = publish_article(cookie, title, content, tags, description)
        
        if ok:
            success_count += 1
            published.append(filename)
            progress["published"] = published
            save_progress(progress)
        else:
            print(f"\n⚠️  发布中断，可重新运行脚本继续未完成的章节")
            break
        
        if i < len(chapters_to_publish) - 1:
            print(f"  ⏳ 等待 {DELAY_SECONDS} 秒...\n")
            time.sleep(DELAY_SECONDS)
    
    print("\n" + "=" * 60)
    print(f"📊 完成: {success_count}/{len(chapters_to_publish)} 篇发布成功")
    print(f"📋 总进度: {len(published)}/{len(PUBLISH_ORDER)} 篇")
    print("=" * 60)


if __name__ == "__main__":
    main()

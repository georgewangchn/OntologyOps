# -*- coding: utf-8 -*-
"""
工具函数模块
"""

import json
import os


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def format_results(results, top_n=5):
    lines = []
    lines.append("─" * 50)
    lines.append("  📋 诊断结果（Prolog 规则推理 · CWA）")
    lines.append("─" * 50)
    for i, (name, conf, confirmed, did) in enumerate(results[:top_n], 1):
        tag = " ✅确诊" if confirmed else " ⚠️疑似"
        bar = "█" * int(conf * 10)
        lines.append(f"  {i}. {name:<16} 置信度：{conf:.2f}  {bar}{tag}")
    lines.append("─" * 50)
    return "\n".join(lines)

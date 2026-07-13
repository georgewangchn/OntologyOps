# -*- coding: utf-8 -*-
"""
工具函数模块
"""

import json
import os


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def format_results(results, top_n=5):
    lines = []
    lines.append("─" * 60)
    lines.append("  📋 诊断结果（多范式分层仲裁推理）")
    lines.append("─" * 60)
    for i, r in enumerate(results[:top_n], 1):
        bar = "█" * int(r["confidence"] * 10)
        conflict_tag = " ⚠️冲突" if r["conflict"] else ""
        lines.append(f"  {i}. {r['disease']:<16} {r['confidence']:.2%}  {bar} [{r['level']}]{conflict_tag}")
        lines.append(f"     仲裁：{r['arbitration_note']}")
        for engine, info in r["engine_results"].items():
            lines.append(f"     {engine}: {info['confidence']:.2f} [{info['level']}]")
    lines.append("─" * 60)
    return "\n".join(lines)

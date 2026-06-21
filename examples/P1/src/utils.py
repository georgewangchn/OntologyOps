# -*- coding: utf-8 -*-
"""
工具函数模块
"""

import json
import os


def load_json(path):
    """加载 JSON 文件"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    """保存为 JSON 文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def format_results(results, top_n=5):
    """
    将诊断结果格式化为可读字符串
    :param results: [(cls, confidence), ...] 列表
    """
    lines = []
    lines.append("─" * 50)
    lines.append("  📋 诊断结果（按置信度排序）")
    lines.append("─" * 50)
    for i, (cls, conf) in enumerate(results[:top_n], 1):
        name = cls.label[0] if cls.label else cls.name
        bar  = "█" * int(conf * 10)
        lines.append(f"  {i}. {name:<20} 置信度：{conf:.2f}  {bar}")
    if len(results) > top_n:
        lines.append(f"  ...（共 {len(results)} 个匹配疾病）")
    lines.append("─" * 50)
    return "\n".join(lines)


def symptom_match_rate(disease_cls, symptoms):
    """
    计算某病的必要症状匹配率（用于置信度计算）
    """
    necessary = list(disease_cls.necessary) if hasattr(disease_cls, "necessary") else []
    if not necessary:
        return 0.1
    match = sum(1 for s in symptoms if s in [x.name for x in necessary])
    return min(0.99, match / len(necessary) + 0.1)


def check_species_match(disease_cls, pet_type):
    """
    检查疾病是否与宠物物种匹配
    （简化版：通过类名关键词判断）
    """
    name = disease_cls.name.lower()
    if pet_type == "cat" and "dog" in name:
        return False
    if pet_type == "dog" and "cat" in name:
        return False
    return True

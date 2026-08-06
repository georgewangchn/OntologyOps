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
    从 is_a 中的 necessary.value 限制解析
    """
    necessary_symptoms = []
    for res in getattr(disease_cls, "is_a", []):
        try:
            if hasattr(res, "property") and hasattr(res, "value") and res.value is not None:
                necessary_symptoms.append(res.value.name)
        except Exception:
            pass
    if not necessary_symptoms:
        return 0.1
    match = sum(1 for s in symptoms if s in necessary_symptoms)
    return min(0.99, match / len(necessary_symptoms) + 0.1)


def check_species_match(disease_cls, pet_type):
    """
    检查疾病是否与宠物物种匹配
    通过 comment 注解中的 species: 标记判断
    """
    for comment in getattr(disease_cls, "comment", []):
        if isinstance(comment, str) and comment.startswith("species:"):
            species = comment[8:].strip()
            if species == "pet":
                return True
            return species == pet_type
    return True

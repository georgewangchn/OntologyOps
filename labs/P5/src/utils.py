# -*- coding: utf-8 -*-
"""
工具函数模块
对比 P1-P3 的 utils.py：数据加载/格式化功能相同
对比 P4 的 utils.py：P4 新增症状严重度计算（模糊化），P5 不需要（贝叶斯用二元症状）
"""

import json
import os
import pandas as pd

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")


def load_json(path):
    """加载 JSON 文件"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    """保存为 JSON 文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_symptom_baselines(symptoms_csv=None):
    """从 symptoms.csv 加载症状基线严重度"""
    if symptoms_csv is None:
        symptoms_csv = os.path.join(SHARED_DATA_DIR, "symptoms.csv")
    df = pd.read_csv(symptoms_csv, encoding="utf-8-sig")
    return dict(zip(df["症状名称"], df["严重度"].astype(float)))


def format_results(results, top_n=5):
    """将诊断结果格式化为可读字符串"""
    lines = []
    lines.append("─" * 50)
    lines.append("  📋 诊断结果（贝叶斯推理 · 后验概率）")
    lines.append("─" * 50)
    for i, (name, prob, level, did) in enumerate(results[:top_n], 1):
        bar = "█" * int(prob * 10)
        lines.append(f"  {i}. {name:<16} P(D|S)={prob:.2%}  {bar} [{level}]")
    lines.append("─" * 50)
    return "\n".join(lines)

# -*- coding: utf-8 -*-
"""
工具函数模块
对比 P1-P3 的 utils.py：数据加载/格式化功能相同，新增症状严重度计算

核心差异：
  P1-P3：症状是二元的（有/无），不需要严重度
  P4：症状是模糊的（连续严重度 0-1），需要从病例详情中计算

  P4 双输入设计：覆盖率（有多少必要症状出现）+ 强度（已出现症状的严重程度）
  对比旧设计：匹配度（覆盖率×强度混合）无法区分"全在但轻"和"缺很多但有一个很重"
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
    """
    从 symptoms.csv 加载症状基线严重度
    :return: {症状名称: 严重度} 字典
    """
    if symptoms_csv is None:
        symptoms_csv = os.path.join(SHARED_DATA_DIR, "symptoms.csv")
    df = pd.read_csv(symptoms_csv, encoding="utf-8-sig")
    return dict(zip(df["症状名称"], df["严重度"].astype(float)))


def compute_symptom_severity(symptom_name, case, baselines):
    """
    计算某症状的严重度（0-1 连续值）

    对比 P1-P3：症状只有"有/无"（1/0），不关心严重程度
    P4：症状有严重程度，从 symptom_details 中提取连续值

    优先级：
      1. 如果症状不在病例的 symptoms 列表中 → 0（未出现）
      2. 如果有 symptom_details，从中计算严重度
      3. 否则使用 symptoms.csv 中的基线严重度
    """
    symptoms = case.get("symptoms", [])
    if symptom_name not in symptoms:
        return 0.0

    details = case.get("symptom_details", {})
    detail = details.get(symptom_name, {})

    # ── 发热：根据体温值映射 ─────────────────────
    if symptom_name == "发热" and "value" in detail:
        temp = float(detail["value"])
        if temp >= 40.0:
            return 1.0
        elif temp >= 39.5:
            return 0.8
        elif temp >= 39.0:
            return 0.6
        else:
            return 0.3

    # ── 呕吐：根据频率映射 ───────────────────────
    if "frequency" in detail:
        freq = detail["frequency"]
        if freq in ("频繁", "持续"):
            return 0.9
        elif freq == "多次":
            return 0.7
        elif freq == "偶尔":
            return 0.4
        else:
            return 0.5

    # ── 腹泻：根据类型和颜色映射 ─────────────────
    if "type" in detail or "color" in detail:
        dtype = detail.get("type", "")
        color = detail.get("color", "")
        base = 0.5
        if "水样" in dtype:
            base = 0.6
        elif "软便" in dtype:
            base = 0.4
        elif "成型" in dtype:
            base = 0.2
        if "血" in color or "暗红" in color:
            base = min(1.0, base + 0.3)
        return base

    # ── 通用：根据 degree 字段映射 ───────────────
    if "degree" in detail:
        degree = detail["degree"]
        if degree == "高":
            return 0.8
        elif degree == "中":
            return 0.5
        elif degree == "低":
            return 0.3

    # ── 默认：使用基线严重度 ─────────────────────
    return baselines.get(symptom_name, 0.5)


def compute_coverage(disease_necessary, case):
    """
    计算疾病必要症状的覆盖率（0-1）

    覆盖率 = 已出现症状数 / 必要症状总数
    与 P1-P3 的匹配率语义一致：只关心"有几个症状在"，不关心严重程度

    例：猫瘟 necessary=[发热, 呕吐, 腹泻]，病例有发热+呕吐+腹泻
      覆盖率 = 3/3 = 1.0

    例：猫艾滋 necessary=[发热, 淋巴结肿大]，病例只有发热
      覆盖率 = 1/2 = 0.5
    """
    if not disease_necessary:
        return 0.0
    case_symptoms = case.get("symptoms", [])
    matched = [s for s in disease_necessary if s in case_symptoms]
    return len(matched) / len(disease_necessary)


def compute_intensity(disease_necessary, case, baselines):
    """
    计算疾病必要症状的强度（0-1）

    强度 = 已出现症状的严重度均值（仅统计已出现的症状，缺失症状不计入）
    与覆盖率正交：只关心"出现的症状有多严重"，不关心"覆盖了多少"

    例：猫瘟 necessary=[发热, 呕吐, 腹泻]，3 个都在，严重度 0.8/0.7/0.9
      强度 = (0.8+0.7+0.9)/3 = 0.80

    例：猫艾滋 necessary=[发热, 淋巴结肿大]，只有发热(0.8)
      强度 = 0.8/1 = 0.80（只算已出现的，不因缺失症状拉低）

    对比旧设计的匹配度（覆盖率×强度混合）：
      旧：3/3全在低烧 → 匹配度=0.3（低）  ← 不合理，症状都在
      新：3/3全在低烧 → 覆盖率=1.0(高), 强度=0.3(低) → 合理区分两个维度
    """
    if not disease_necessary:
        return 0.0
    case_symptoms = case.get("symptoms", [])
    matched = [s for s in disease_necessary if s in case_symptoms]
    if not matched:
        return 0.0
    severities = [compute_symptom_severity(s, case, baselines) for s in matched]
    return sum(severities) / len(severities)


def compute_exclusion_degree(disease_exclusion, case, baselines):
    """
    计算疾病排除症状的模糊排除度（0-1）

    模糊 OR（取最大值）：只要有一个排除症状出现，排除度就高

    对比 P1-P3：排除是二元的——命中排除症状 → 完全排除
    P4：排除是模糊的——排除症状严重度越高，排除度越高（但不完全归零）

    例：猫肠炎 exclusion=[发热, 咳嗽]，病例有发热(0.8)
      P1-P3: 发热命中 → 完全排除（不出现在结果中）
      P4:    max(0.8, 0) = 0.8 → 高排除度（置信度降低，但仍出现在结果中）
    """
    if not disease_exclusion:
        return 0.0
    severities = [
        compute_symptom_severity(s, case, baselines)
        for s in disease_exclusion
    ]
    return max(severities)


def format_results(results, top_n=5):
    """
    将诊断结果格式化为可读字符串
    :param results: [(name, confidence, fuzzy_level, did), ...] 列表
    """
    lines = []
    lines.append("─" * 50)
    lines.append("  📋 诊断结果（模糊推理 · 连续置信度）")
    lines.append("─" * 50)
    for i, (name, conf, level, did) in enumerate(results[:top_n], 1):
        bar = "█" * int(conf * 10)
        lines.append(f"  {i}. {name:<16} 置信度：{conf:.2f}  {bar} [{level}]")
    lines.append("─" * 50)
    return "\n".join(lines)

# -*- coding: utf-8 -*-
"""
模糊推理机模块 —— scikit-fuzzy Mamdani 推理
对比 P1 的 reasoner.py：owlready2 调用 HermiT 做 OWL 分类（Tableau 算法）
对比 P2 的 reasoner.py：pyswip 调用 SWI-Prolog 做目标驱动推理（SLD 归结）
对比 P3 的 reasoner.py：SPARQL 查询 Jena 前向链预计算结果

核心差异：
  P1：HermiT 做 OWL 分类（equivalent_to 双向推理）→ 二元结果（是/否）
  P2：Prolog 做目标驱动推理（SLD 归结）→ 二元结果（是/否）
  P3：Jena 做前向链预计算，SPARQL 查询 → 二元结果（是/否）
  P4：Mamdani 模糊推理（隶属度 → 规则触发 → 去模糊化）→ 连续结果（0-1）

  P1-P3：症状有/无（二元）→ 疾病是/否（二元）
  P4：症状严重度（连续 0-1）→ 疾病置信度（连续 0-1）

  P1-P3：排除症状命中 → 完全排除（不出现在结果中）
  P4：排除症状命中 → 降低置信度（仍出现在结果中，但排名低）

Mamdani 推理流程：
  ① 模糊化：将连续输入（匹配度、排除度）映射到模糊集合（低/中/高）
  ② 规则触发：每条 IF-THEN 规则的激活强度 = min(条件隶属度)
  ③ 合成：所有规则的输出模糊集合取 max（聚合）
  ④ 去模糊化：重心法（centroid）将输出模糊集合转为连续值
"""

import json
import os
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from utils import (
    load_symptom_baselines,
    compute_symptom_severity,
    compute_coverage,
    compute_intensity,
    compute_exclusion_degree,
)

LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")
KB_JSON = os.path.join(LOCAL_DATA_DIR, "fuzzy_kb.json")

# 模糊变量论域
UNIVERSE = np.arange(0, 1.01, 0.01)

# 全局缓存
_kb = None
_controller = None


def load_knowledge_base():
    """加载模糊知识库"""
    global _kb
    if _kb is not None:
        return _kb

    if not os.path.exists(KB_JSON):
        raise FileNotFoundError(
            f"未找到模糊知识库：{KB_JSON}\n请先运行 kb_builder.py 生成。"
        )
    with open(KB_JSON, encoding="utf-8") as f:
        _kb = json.load(f)
    print(f"✅ 模糊知识库已加载（{len(_kb['diseases'])} 种疾病）")
    return _kb


def _build_membership(var_name, mf_defs):
    """构建单个模糊变量的隶属度函数"""
    var = ctrl.Antecedent(UNIVERSE, var_name) if var_name != "置信度" \
        else ctrl.Consequent(UNIVERSE, var_name)
    for label, params in mf_defs.items():
        var[label] = fuzz.trapmf(var.universe, params)
    return var


def build_fuzzy_controller():
    """
    构建 Mamdani 模糊控制器（三输入：覆盖率 + 强度 + 排除度 → 置信度）

    对比 P1：HermiT 推理机（JVM 进程，Tableau 算法）
    对比 P2：SWI-Prolog 推理引擎（C 进程，SLD 归结）
    对比 P3：Jena GenericRuleReasoner（JVM 进程，前向链）
    P4：scikit-fuzzy ControlSystem（纯 Python，Mamdani 推理）
    """
    global _controller
    if _controller is not None:
        return _controller

    kb = load_knowledge_base()
    mf_defs = kb["membership_functions"]
    rules_defs = kb["fuzzy_rules"]

    # ── ① 构建模糊变量（3 个前件 + 1 个后件）──
    coverage_var = _build_membership("覆盖率", mf_defs["覆盖率"])
    intensity_var = _build_membership("强度", mf_defs["强度"])
    exclude_var = _build_membership("排除度", mf_defs["排除度"])
    confidence_var = _build_membership("置信度", mf_defs["置信度"])

    # ── ② 构建模糊规则 ──────────────────────────
    rules = []
    for rd in rules_defs:
        conditions = rd["if"]
        consequence = rd["then"]["置信度"]

        # 根据条件数量构建规则
        cond_parts = []
        if "覆盖率" in conditions:
            cond_parts.append(coverage_var[conditions["覆盖率"]])
        if "强度" in conditions:
            cond_parts.append(intensity_var[conditions["强度"]])
        if "排除度" in conditions:
            cond_parts.append(exclude_var[conditions["排除度"]])

        if not cond_parts:
            continue

        # 用 & 连接所有条件
        antecedent = cond_parts[0]
        for part in cond_parts[1:]:
            antecedent = antecedent & part

        rule = ctrl.Rule(antecedent, confidence_var[consequence])
        rules.append(rule)

    # ── ③ 构建控制器 ────────────────────────────
    _controller = ctrl.ControlSystem(rules)
    print(f"✅ Mamdani 模糊控制器已构建（{len(rules)} 条规则，3 输入）")
    return _controller


def _defuzzify_level(confidence):
    """将连续置信度映射到模糊等级标签"""
    if confidence >= 0.65:
        return "高"
    elif confidence >= 0.35:
        return "中"
    else:
        return "低"


def diagnose(kb, case_dict):
    """
    对一个病例执行模糊推理诊断

    推理流程：
      1. 对每种疾病计算覆盖率（必要症状出现比例）和强度（已出现症状严重度均值）
      2. 计算排除度（排除症状严重度最大值）
      3. 物种过滤：跳过不匹配的疾病
      4. Mamdani 模糊推理：覆盖率 + 强度 + 排除度 → 置信度
      5. 去模糊化：重心法 → 连续置信度值
      6. 按置信度降序排序

    :return: 排序后的 (疾病名, 置信度, 模糊等级, 疾病ID) 列表
    """
    controller = build_fuzzy_controller()
    baselines = kb["symptom_baselines"]
    pet_type = case_dict.get("pet_type", "pet")

    results = []
    for disease in kb["diseases"]:
        # 物种过滤（与 P1-P3 一致）
        species = disease["species"]
        if species != "pet" and species != pet_type:
            continue

        necessary = disease["necessary_symptoms"]
        exclusion = disease["exclusion_symptoms"]

        if not necessary:
            continue

        # ── 计算三个模糊输入 ─────────────────────
        coverage = compute_coverage(necessary, case_dict)
        intensity = compute_intensity(necessary, case_dict, baselines)
        exclusion_degree = compute_exclusion_degree(exclusion, case_dict, baselines)

        # 无覆盖 → 跳过（与 P1-P3 一致：无必要症状匹配不进入候选）
        if coverage < 0.01:
            continue

        # ── Mamdani 模糊推理 ─────────────────────
        sim = ctrl.ControlSystemSimulation(controller)
        sim.input["覆盖率"] = coverage
        sim.input["强度"] = intensity
        sim.input["排除度"] = exclusion_degree

        try:
            sim.compute()
            confidence = float(sim.output["置信度"])
        except Exception:
            # 如果规则未触发（输入在所有规则的盲区），使用线性回退
            confidence = coverage * intensity * (1.0 - exclusion_degree * 0.8)

        fuzzy_level = _defuzzify_level(confidence)
        results.append((disease["name"], confidence, fuzzy_level, disease["id"]))

    # ── 按置信度降序排序 ─────────────────────────
    results.sort(key=lambda x: -x[1])
    return results


def explain(kb, case_dict):
    """
    生成模糊推理链解释（可追溯的诊断依据）

    对比 P1-P3 的解释：
      P1：equivalent_to 匹配 + SWRL 排除
      P2：matched/missing/excluded 列表
      P3：suspected/excluded 三元组
    P4：每个症状的严重度 + 覆盖率/强度/排除度计算过程 + 模糊规则触发
    """
    baselines = kb["symptom_baselines"]
    pet_type = case_dict.get("pet_type", "pet")
    case_symptoms = case_dict.get("symptoms", [])

    explanations = []
    for disease in kb["diseases"]:
        species = disease["species"]
        if species != "pet" and species != pet_type:
            continue

        necessary = disease["necessary_symptoms"]
        exclusion = disease["exclusion_symptoms"]
        if not necessary:
            continue

        # 收集必要症状严重度
        nec_details = []
        for s in necessary:
            sev = compute_symptom_severity(s, case_dict, baselines)
            present = s in case_symptoms
            nec_details.append({
                "symptom": s,
                "present": present,
                "severity": round(sev, 2),
            })

        # 收集排除症状严重度
        exc_details = []
        for s in exclusion:
            sev = compute_symptom_severity(s, case_dict, baselines)
            present = s in case_symptoms
            exc_details.append({
                "symptom": s,
                "present": present,
                "severity": round(sev, 2),
            })

        coverage = compute_coverage(necessary, case_dict)
        intensity = compute_intensity(necessary, case_dict, baselines)
        exclusion_degree = compute_exclusion_degree(exclusion, case_dict, baselines)

        if coverage < 0.01:
            continue

        explanations.append({
            "disease_id": disease["id"],
            "disease_name": disease["name"],
            "necessary_symptoms": nec_details,
            "exclusion_symptoms": exc_details,
            "coverage": round(coverage, 2),
            "intensity": round(intensity, 2),
            "exclusion_degree": round(exclusion_degree, 2),
        })

    return explanations


def print_diagnosis(results):
    """格式化打印诊断结果"""
    print("\n" + "─" * 50)
    print("  📋 诊断结果（模糊推理 · Mamdani · 连续置信度）")
    print("─" * 50)
    for i, (name, conf, level, did) in enumerate(results[:5], 1):
        bar = "█" * int(conf * 10)
        print(f"  {i}. {name:<16} 置信度：{conf:.2f}  {bar} [{level}]")
    print("─" * 50)

    # 打印与 P1-P3 的关键差异说明
    if results:
        print("\n  💡 与 P1-P3 确定性推理的区别：")
        print("     · 置信度是连续值（0-1），不是二元（确诊/排除）")
        print("     · 排除症状不完全排除疾病，而是降低置信度")
        print("     · 症状严重度影响推理结果（高烧 > 低烧）")


# ── CLI 入口 ──────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="宠物疾病诊断（模糊推理）")
    parser.add_argument(
        "--input",
        default=os.path.join(SHARED_DATA_DIR, "sample_case.json"),
        help="病例 JSON 文件路径",
    )
    args = parser.parse_args()

    print("🏥 宠物疾病诊断推理系统（模糊推理 · Mamdani）")
    print("=" * 50)

    with open(args.input, encoding="utf-8") as f:
        case = json.load(f)
    print(f"📋 病例：{case.get('note', args.input)}")
    print(f"   症状：{', '.join(case.get('symptoms', []))}")
    print(f"   物种：{case.get('pet_type', '未知')}")

    # 打印症状严重度
    baselines = load_symptom_baselines()
    print(f"\n   症状严重度（模糊化输入）：")
    for s in case.get("symptoms", []):
        sev = compute_symptom_severity(s, case, baselines)
        print(f"     {s}: {sev:.2f}")
    print()

    kb = load_knowledge_base()
    results = diagnose(kb, case)
    print_diagnosis(results)

    # 打印推理链
    print("\n  🔗 推理链解释：")
    explanations = explain(kb, case)
    for exp in explanations[:3]:
        print(f"\n  [{exp['disease_name']}]")
        print(f"    覆盖率：{exp['coverage']}  强度：{exp['intensity']}  排除度：{exp['exclusion_degree']}")
        print(f"    必要症状：")
        for s in exp["necessary_symptoms"]:
            tag = "✅" if s["present"] else "❌"
            print(f"      {s['symptom']}: 严重度={s['severity']} {tag}")
        if exp["exclusion_symptoms"]:
            print(f"    排除症状：")
            for s in exp["exclusion_symptoms"]:
                tag = "⚠️命中" if s["present"] else "✅未命中"
                print(f"      {s['symptom']}: 严重度={s['severity']} {tag}")

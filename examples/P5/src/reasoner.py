# -*- coding: utf-8 -*-
"""
推理机模块 —— 朴素贝叶斯概率推理
对比 P1 的 reasoner.py：owlready2 调用 HermiT 做 OWL 分类（Tableau 算法）
对比 P2 的 reasoner.py：pyswip 调用 SWI-Prolog 做目标驱动推理（SLD 归结）
对比 P3 的 reasoner.py：SPARQL 查询 Jena 前向链预计算结果
对比 P4 的 reasoner.py：scikit-fuzzy Mamdani 推理（隶属度→规则→去模糊化）

核心差异：
  P1：HermiT 做 OWL 分类（equivalent_to 双向推理）→ 二元结果（是/否）
  P2：Prolog 做目标驱动推理（SLD 归结）→ 二元结果（是/否）
  P3：Jena 做前向链预计算，SPARQL 查询 → 二元结果（是/否）
  P4：Mamdani 模糊推理（隶属度 → 规则触发 → 去模糊化）→ 连续结果（0-1）
  P5：朴素贝叶斯推理（先验 × 似然 → 归一化后验）→ 连续结果（0-1）

  P1-P3：症状有/无（二元）→ 疾病是/否（二元），确定性推理
  P4：症状严重度（连续 0-1）→ 疾病置信度（连续 0-1），模糊推理
  P5：症状有/无（二元）→ 疾病后验概率（连续 0-1），概率推理

  P4 vs P5 关键区别：
    P4 置信度 = f(覆盖率, 强度, 排除度) —— 模糊匹配程度
    P5 置信度 = P(D|S) = P(D)×∏P(Sᵢ|D) / Z —— 后验概率（有概率论保证）
    P4 的 0.8 和 P5 的 0.8 语义不同：P4="匹配度高"，P5="概率80%"

贝叶斯推理流程：
  ① 对每种疾病，计算先验 × 似然的乘积
  ② 归一化所有疾病的乘积，得到后验概率分布
  ③ 按后验概率降序排序
"""

import json
import os
import math

LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")
KB_JSON = os.path.join(LOCAL_DATA_DIR, "bayesian_kb.json")

# 全局缓存
_kb = None


def load_knowledge_base():
    """加载贝叶斯知识库"""
    global _kb
    if _kb is not None:
        return _kb

    if not os.path.exists(KB_JSON):
        raise FileNotFoundError(
            f"未找到贝叶斯知识库：{KB_JSON}\n请先运行 kb_builder.py 生成。"
        )
    with open(KB_JSON, encoding="utf-8") as f:
        _kb = json.load(f)
    print(f"✅ 贝叶斯知识库已加载（{len(_kb['diseases'])} 种疾病）")
    return _kb


def _compute_posterior(disease, case_symptoms):
    """
    计算单个疾病的后验概率（未归一化）

    P(D|S₁,...,Sₙ) ∝ P(D) × ∏ P(Sᵢ|D) × ∏ P(¬Sⱼ|D)

    其中 Sᵢ 是已出现的症状，Sⱼ 是未出现但在 CPT 中的症状。

    朴素贝叶斯假设：在给定疾病 D 的条件下，症状之间条件独立。
    """
    prior = disease.get("prior", 0.05)
    cpt = disease.get("cpt", {})

    if not cpt:
        return prior

    likelihood = prior

    for symptom, probs in cpt.items():
        p_present = probs["present"]   # P(S|D)
        p_absent = probs["absent"]     # P(S|¬D)

        if symptom in case_symptoms:
            # 症状出现：乘以 P(S|D)
            likelihood *= p_present
        else:
            # 症状未出现：乘以 P(¬S|D) = 1 - P(S|D)
            likelihood *= (1.0 - p_present)

    return likelihood


def diagnose(kb, case_dict):
    """
    对一个病例执行贝叶斯推理诊断

    推理流程：
      1. 物种过滤
      2. 对每种疾病计算先验×似然
      3. 归一化得到后验概率分布
      4. 按后验概率降序排序

    :return: 排序后的 (疾病名, 后验概率, 概率等级, 疾病ID) 列表
    """
    pet_type = case_dict.get("pet_type", "pet")
    case_symptoms = case_dict.get("symptoms", [])

    raw_posteriors = []

    for disease in kb["diseases"]:
        species = disease["species"]
        if species != "pet" and species != pet_type:
            continue

        posterior = _compute_posterior(disease, case_symptoms)
        if posterior > 0:
            raw_posteriors.append((disease, posterior))

    # 归一化：将所有疾病的似然值归一化为概率分布
    total = sum(p for _, p in raw_posteriors)
    if total == 0:
        return []

    results = []
    for disease, posterior in raw_posteriors:
        normalized = posterior / total
        level = _probability_level(normalized)
        results.append((disease["name"], normalized, level, disease["id"]))

    # 按后验概率降序
    results.sort(key=lambda x: -x[1])
    return results


def _probability_level(prob):
    """将后验概率映射到等级标签"""
    if prob >= 0.50:
        return "高概率"
    elif prob >= 0.15:
        return "中概率"
    else:
        return "低概率"


def explain(kb, case_dict):
    """
    生成贝叶斯推理链解释（可追溯的诊断依据）

    对比 P1-P4 的解释：
      P1：equivalent_to 匹配 + SWRL 排除
      P2：matched/missing/excluded 列表 + CWA 说明
      P3：suspected/excluded 三元组 + OWA 说明
      P4：覆盖率/强度/排除度 + 模糊规则触发
    P5：先验概率 + 每个症状的似然贡献 + 后验概率
    """
    pet_type = case_dict.get("pet_type", "pet")
    case_symptoms = case_dict.get("symptoms", [])

    explanations = []
    results = diagnose(kb, case_dict)

    for name, posterior, level, did in results[:5]:
        disease = next((d for d in kb["diseases"] if d["id"] == did), None)
        if not disease:
            continue

        prior = disease.get("prior", 0.05)
        cpt = disease.get("cpt", {})

        symptom_contributions = []
        for symptom, probs in cpt.items():
            p_present = probs["present"]
            p_absent = probs["absent"]
            present = symptom in case_symptoms

            if present:
                contribution = p_present
                role = "支持" if p_present > 0.3 else "弱支持"
            else:
                contribution = 1.0 - p_present
                role = "不支持" if p_present > 0.3 else "无关"

            symptom_contributions.append({
                "symptom": symptom,
                "present": present,
                "p_given_d": p_present,
                "p_given_not_d": p_absent,
                "contribution": round(contribution, 3),
                "role": role,
            })

        # 计算似然比（Bayes factor）
        likelihood_ratio = posterior / prior if prior > 0 else float("inf")

        explanations.append({
            "disease_id": did,
            "disease_name": name,
            "prior": round(prior, 4),
            "posterior": round(posterior, 4),
            "level": level,
            "likelihood_ratio": round(likelihood_ratio, 2),
            "symptom_contributions": symptom_contributions,
        })

    return explanations


def print_diagnosis(results):
    """格式化打印诊断结果"""
    print("\n" + "─" * 50)
    print("  📋 诊断结果（贝叶斯推理 · 后验概率）")
    print("─" * 50)
    for i, (name, prob, level, did) in enumerate(results[:5], 1):
        bar = "█" * int(prob * 10)
        print(f"  {i}. {name:<16} P(D|S)={prob:.2%}  {bar} [{level}]")
    print("─" * 50)

    if results:
        print("\n  💡 与 P1-P4 的关键区别：")
        print("     · 结果是后验概率（有概率论保证），不是匹配度或模糊值")
        print("     · 先验概率影响结果（罕见病需要更强证据）")
        print("     · 未出现的症状也参与推理（P(¬S|D) 降低后验）")


# ── CLI 入口 ──────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="宠物疾病诊断（贝叶斯推理）")
    parser.add_argument(
        "--input",
        default=os.path.join(SHARED_DATA_DIR, "sample_case.json"),
        help="病例 JSON 文件路径",
    )
    args = parser.parse_args()

    print("🏥 宠物疾病诊断推理系统（贝叶斯推理 · 朴素贝叶斯）")
    print("=" * 50)

    with open(args.input, encoding="utf-8") as f:
        case = json.load(f)
    print(f"📋 病例：{case.get('note', args.input)}")
    print(f"   症状：{', '.join(case.get('symptoms', []))}")
    print(f"   物种：{case.get('pet_type', '未知')}")
    print()

    kb = load_knowledge_base()
    results = diagnose(kb, case)
    print_diagnosis(results)

    print("\n  🔗 推理链解释：")
    explanations = explain(kb, case)
    for exp in explanations[:3]:
        print(f"\n  [{exp['disease_name']}]")
        print(f"    先验 P(D)={exp['prior']:.2%} → 后验 P(D|S)={exp['posterior']:.2%}")
        print(f"    似然比 = {exp['likelihood_ratio']}x")
        print(f"    症状贡献：")
        for s in exp["symptom_contributions"]:
            tag = "✅" if s["present"] else "❌"
            print(f"      {s['symptom']}: P(S|D)={s['p_given_d']:.2f} {tag} [{s['role']}]")

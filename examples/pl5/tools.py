"""
PL5 工具集 —— 8 个 LangChain @tool 函数

对比 PL1: 7 个工具（OWL）
对比 PL2: 8 个工具（Prolog + query_transmit_chain）
对比 PL3: 8 个工具（SPARQL + query_transitive_closure）
对比 PL4: 8 个工具（Fuzzy + get_symptom_severity）

PL5 独有工具：query_prior_and_likelihood — 查询疾病先验概率和症状似然比
"""

import os
import sys
import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# P5 模块路径
_P5_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P5", "src"
)
if _P5_DIR not in sys.path:
    sys.path.insert(0, _P5_DIR)


def create_pl5_tools(state, diagnose_fn, report_builder):
    """创建 PL5 工具集（闭包工厂模式，与 PL1-PL4 一致）"""

    @tool
    def lookup_symptom_bayesian(symptom_name: str) -> str:
        """在贝叶斯知识库中查找症状，返回关联疾病和条件概率。"""
        try:
            from reasoner import load_knowledge_base
            kb = load_knowledge_base()
        except Exception as e:
            return f"知识库加载失败：{e}"

        related = []
        for disease in kb["diseases"]:
            cpt = disease.get("cpt", {})
            if symptom_name in cpt:
                probs = cpt[symptom_name]
                related.append({
                    "disease": disease["name"],
                    "disease_id": disease["id"],
                    "p_given_d": probs["present"],
                    "p_given_not_d": probs["absent"],
                    "likelihood_ratio": round(probs["present"] / probs["absent"], 2) if probs["absent"] > 0 else float("inf"),
                })

        if not related:
            return f"未找到与症状「{symptom_name}」相关的疾病。"

        lines = [f"症状「{symptom_name}」关联的疾病："]
        for r in related:
            lines.append(
                f"  · {r['disease']}({r['disease_id']}): "
                f"P(S|D)={r['p_given_d']:.2f}, "
                f"P(S|¬D)={r['p_given_not_d']:.2f}, "
                f"似然比={r['likelihood_ratio']}x"
            )
        return "\n".join(lines)

    @tool
    def lookup_disease_bayesian(disease_name: str) -> str:
        """查找疾病，返回先验概率、条件概率表（CPT）和物种约束。"""
        try:
            from reasoner import load_knowledge_base
            kb = load_knowledge_base()
        except Exception as e:
            return f"知识库加载失败：{e}"

        for disease in kb["diseases"]:
            if disease_name in disease["name"] or disease_name.upper() in disease["id"]:
                lines = [
                    f"疾病：{disease['name']} ({disease['id']})",
                    f"物种：{disease['species']}",
                    f"先验概率 P(D)：{disease.get('prior', 0.05):.2%}",
                    f"必要症状：{', '.join(disease.get('necessary_symptoms', []))}",
                    f"排除症状：{', '.join(disease.get('exclusion_symptoms', []))}",
                    f"条件概率表（CPT）：",
                ]
                for symptom, probs in disease.get("cpt", {}).items():
                    lr = probs["present"] / probs["absent"] if probs["absent"] > 0 else float("inf")
                    lines.append(
                        f"  {symptom}: P(S|D)={probs['present']:.2f}, "
                        f"P(S|¬D)={probs['absent']:.2f}, 似然比={lr:.1f}x"
                    )
                return "\n".join(lines)

        return f"未找到疾病「{disease_name}」。"

    @tool
    def add_observation(symptom_name: str, severity: str = "中度") -> str:
        """记录观察到的症状。severity 可选：轻度/中度/重度。"""
        state.add_observation(symptom_name, severity)
        return f"已记录症状：{symptom_name}（{severity}）。当前已记录 {len(state.observations)} 个症状。"

    @tool
    def set_pet_info(species: str, breed: str = "", age: str = "", sex: str = "") -> str:
        """设置宠物基本信息。species 必填（猫/狗），其他可选。"""
        state.set_subject(species=species, breed=breed, age=age, sex=sex)
        return f"已设置宠物信息：{species}，{breed}，{age}岁，{sex}。"

    @tool
    def run_bayesian_reasoning() -> str:
        """运行贝叶斯推理，返回后验概率分布。需要先设置宠物信息和至少2个症状。"""
        if not state.is_ready_for_reasoning():
            return "信息不足，请先设置宠物信息并记录至少2个症状。"

        case_dict = state.to_case_dict()
        try:
            results = diagnose_fn(case_dict)
        except Exception as e:
            return f"推理失败：{e}"

        if not results:
            return "推理完成，但未找到匹配的疾病。"

        report = report_builder(state, results)
        return report.format_for_user()

    @tool
    def explain_bayesian_reasoning() -> str:
        """解释贝叶斯推理链：先验概率、似然贡献、后验概率。"""
        if not state.is_ready_for_reasoning():
            return "信息不足，请先设置宠物信息和至少2个症状。"

        case_dict = state.to_case_dict()
        try:
            from reasoner import load_knowledge_base, explain
            kb = load_knowledge_base()
            explanations = explain(kb, case_dict)
        except Exception as e:
            return f"推理链解释失败：{e}"

        if not explanations:
            return "无推理链可解释。"

        lines = ["贝叶斯推理链解释："]
        for exp in explanations[:3]:
            lines.append(f"\n[{exp['disease_name']}]")
            lines.append(f"  先验 P(D)={exp['prior']:.2%} → 后验 P(D|S)={exp['posterior']:.2%}")
            lines.append(f"  似然比 = {exp['likelihood_ratio']}x")
            lines.append(f"  症状贡献：")
            for s in exp["symptom_contributions"]:
                tag = "✅" if s["present"] else "❌"
                lines.append(
                    f"    {s['symptom']}: P(S|D)={s['p_given_d']:.2f} "
                    f"{tag} [{s['role']}]"
                )
        return "\n".join(lines)

    @tool
    def query_prior_and_likelihood(disease_name: str) -> str:
        """查询某疾病的先验概率和各症状的似然比（PL5 独有）。"""
        try:
            from reasoner import load_knowledge_base
            kb = load_knowledge_base()
        except Exception as e:
            return f"知识库加载失败：{e}"

        for disease in kb["diseases"]:
            if disease_name in disease["name"] or disease_name.upper() in disease["id"]:
                prior = disease.get("prior", 0.05)
                cpt = disease.get("cpt", {})
                lines = [
                    f"疾病：{disease['name']} ({disease['id']})",
                    f"先验概率 P(D) = {prior:.2%}",
                    f"各症状似然比（LR = P(S|D) / P(S|¬D)）：",
                ]
                for symptom, probs in cpt.items():
                    lr = probs["present"] / probs["absent"] if probs["absent"] > 0 else float("inf")
                    interpretation = ""
                    if lr > 10:
                        interpretation = "（强支持证据）"
                    elif lr > 3:
                        interpretation = "（中等支持证据）"
                    elif lr < 0.3:
                        interpretation = "（强反对证据）"
                    elif lr < 1:
                        interpretation = "（弱反对证据）"
                    lines.append(
                        f"  {symptom}: LR = {lr:.1f}x {interpretation}"
                    )
                return "\n".join(lines)

        return f"未找到疾病「{disease_name}」。"

    @tool
    def get_case_summary() -> str:
        """返回当前病例摘要。"""
        if not state.subject.species:
            return "信息不足：尚未设置宠物信息。"
        if len(state.observations) < 2:
            return f"信息不足：已记录 {len(state.observations)} 个症状（至少需要2个）。"
        return state.get_summary()

    return [
        lookup_symptom_bayesian,
        lookup_disease_bayesian,
        add_observation,
        set_pet_info,
        run_bayesian_reasoning,
        explain_bayesian_reasoning,
        query_prior_and_likelihood,
        get_case_summary,
    ]

"""
PL6 报告构建器 —— 多范式贝叶斯元推理报告

对比 PL1-PL5 的 reasoning_engine：
  PL1: "OWL-DL (HermiT) + SWRL"
  PL2: "Prolog (SWI-Prolog) + SLD"
  PL3: "Jena Fuseki + SPARQL (前向链)"
  PL4: "scikit-fuzzy Mamdani (模糊推理)"
  PL5: "Naive Bayes (贝叶斯网络)"
  PL6: "Bayesian Meta-Reasoner (似然比融合)"
"""

from agent_core import DiagnosisReport, DiagnosisItem


def build_pl6_report(state, results: list) -> DiagnosisReport:
    """构建 PL6 诊断报告。"""
    items = []
    for r in results:
        items.append(DiagnosisItem(
            disease=r["disease"],
            confidence=r["confidence"],
            level=r["level"],
            disease_id=r.get("disease_id", ""),
            evidence=r.get("evidence", []),
            missing=r.get("missing", []),
        ))

    report = DiagnosisReport(
        subject=state.subject,
        observations=state.observations,
        results=items,
        reasoning_engine="Bayesian Meta-Reasoner (似然比融合)",
        reasoning_path=_build_reasoning_path(results),
        disclaimer=(
            "本报告由贝叶斯元推理引擎生成。"
            "P2(Prolog)、P4(模糊)、P5(贝叶斯) 三个引擎并行推理，"
            "各自输出转为似然比(LR)，以贝叶斯乘法融合后归一化。"
            "标注「冲突」的疾病表示各引擎似然比方向不一致。"
        ),
    )
    return report


def _build_reasoning_path(results: list) -> str:
    """构建推理路径描述。"""
    if not results:
        return "无推理结果"

    lines = [
        "贝叶斯元推理路径：",
        "  引擎选择：P2(Prolog/CWA) + P4(Mamdani) + P5(Naive Bayes)",
        "  P1/P3 不运行：与 P2 共享同一知识源，消除冗余",
        "",
        "似然比转换：",
        "  P2: 确诊->LR=5.0, 疑似->LR=1.5, 排除->LR=0.1",
        "  P4: LR = exp(3.0 * (conf - 0.5))",
        "  P5: LR = posterior / prior",
        "",
        "贝叶斯乘法融合：",
        "  P_final(D) proportional to P_prior(D) x LR_struct x LR_fuzzy x LR_bayesian",
        "  归一化后得到最终后验概率分布",
    ]

    top = results[0]
    conflict_tag = " [冲突]" if top.get("conflict") else ""
    lines.append(f"\n  Top-1: {top['disease']} {top['confidence']:.2%} [{top['level']}]{conflict_tag}")
    lines.append(f"  融合说明：{top.get('arbitration_note', '')}")

    return "\n".join(lines)

"""
PL6 报告构建器 —— 多范式仲裁推理报告

对比 PL1-PL5 的 reasoning_engine：
  PL1: "OWL-DL (HermiT) + SWRL"
  PL2: "Prolog (SWI-Prolog) + SLD"
  PL3: "Jena Fuseki + SPARQL (前向链)"
  PL4: "scikit-fuzzy Mamdani (模糊推理)"
  PL5: "Naive Bayes (贝叶斯网络)"
  PL6: "Multi-Engine Arbiter (P1-P5 分层仲裁)"
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
        reasoning_engine="Multi-Engine Arbiter (P1-P5 分层仲裁)",
        reasoning_path=_build_reasoning_path(results),
        disclaimer=(
            "本报告由多范式分层仲裁推理引擎生成。"
            "第一层（P1+P2+P3）确定性推理先行，第二层（P4）模糊量化，"
            "第三层（P5）概率校准，仲裁器综合三层结果裁决。"
            "标注「冲突」的疾病表示各引擎意见不一致，以贝叶斯后验概率为准。"
        ),
    )
    return report


def _build_reasoning_path(results: list) -> str:
    """构建推理路径描述。"""
    if not results:
        return "无推理结果"

    lines = [
        "多范式分层仲裁推理路径：",
        "  第一层：P1(OWL) + P2(Prolog) + P3(SPARQL) 确定性推理",
        "  第二层：P4(Mamdani) 模糊量化",
        "  第三层：P5(贝叶斯) 概率校准",
        "  仲裁器：综合三层裁决",
        "",
        "仲裁规则：",
        "  · 确定性一致确诊 → 置信度=1.0",
        "  · 确定性一致排除 → 置信度=0.0",
        "  · 确定性冲突 → 概率优先，标注冲突",
        "  · 加权融合：贝叶斯×0.6 + 模糊×0.4",
    ]

    top = results[0]
    conflict_tag = " ⚠️冲突" if top.get("conflict") else ""
    lines.append(f"\n  Top-1: {top['disease']} {top['confidence']:.2%} [{top['level']}]{conflict_tag}")
    lines.append(f"  仲裁说明：{top.get('arbitration_note', '')}")

    return "\n".join(lines)

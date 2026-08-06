"""
PL5 报告构建器 —— 将推理结果格式化为 DiagnosisReport

对比 PL1: reasoning_engine = "OWL-DL (HermiT) + SWRL"
对比 PL2: reasoning_engine = "Prolog (SWI-Prolog) + SLD"
对比 PL3: reasoning_engine = "Jena Fuseki + SPARQL (前向链)"
对比 PL4: reasoning_engine = "scikit-fuzzy Mamdani (模糊推理)"
PL5:       reasoning_engine = "Naive Bayes (贝叶斯网络)"
"""

from agent_core import DiagnosisReport, DiagnosisItem


def build_pl5_report(state, results: list) -> DiagnosisReport:
    """构建 PL5 诊断报告。"""
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
        reasoning_engine="Naive Bayes (贝叶斯网络)",
        reasoning_path=_build_reasoning_path(results),
        disclaimer=(
            "本报告由朴素贝叶斯推理引擎生成。后验概率基于先验概率和条件概率表计算，"
            "具有严格的概率论语义。结果表示'给定症状时疾病的概率'，"
            "而非症状匹配程度。先验概率基于发病率统计，"
            "未出现的症状也通过 P(¬S|D) 参与推理。"
        ),
    )
    return report


def _build_reasoning_path(results: list) -> str:
    """构建推理路径描述。"""
    if not results:
        return "无推理结果"

    lines = [
        "贝叶斯推理路径：",
        "  1. 对每种疾病计算先验概率 P(D) × 似然 ∏ P(Sᵢ|D) × ∏ P(¬Sⱼ|D)",
        "  2. 归一化所有疾病的后验值，得到概率分布",
        "  3. 按后验概率降序排序",
        "",
        "关键特性：",
        "  · 先验概率让常见病天然占优",
        "  · 未出现的症状通过 P(¬S|D) 降低后验（负证据）",
        "  · 后验概率有严格的概率论保证",
    ]

    top = results[0]
    lines.append(f"\n  Top-1: {top['disease']} P(D|S)={top['confidence']:.2%} [{top['level']}]")

    return "\n".join(lines)

"""
PL3 报告构建 —— 将 Jena/SPARQL 推理结果格式化为 DiagnosisReport。

输入：
  - state: ConversationState（包含宠物信息 + 已收集的观测）
  - results: pl3_diagnose() 的输出（List[Dict]）

输出：
  - DiagnosisReport（agent_core 统一报告结构）
"""

from agent_core.conversation import DiagnosisReport, DiagnosisItem


def build_pl3_report(state, results: list) -> DiagnosisReport:
    """
    构建 PL3 诊断报告。

    将 Jena 前向链 + SPARQL 推理结果转换为统一的 DiagnosisReport 格式，
    包含推理路径说明（前向链 + SPARQL 查询一体化 + OWA）。
    """
    items = []

    for r in results:
        item = DiagnosisItem(
            disease=r.get("disease", "未知"),
            confidence=r.get("confidence", 0.0),
            level=r.get("level", ""),
            disease_id=r.get("disease_id", ""),
            evidence=r.get("evidence", []),
            missing=r.get("missing", []),
        )
        items.append(item)

    # 构建推理路径说明
    reasoning_path = _build_reasoning_path(state, items)

    report = DiagnosisReport(
        subject=state.subject,
        observations=state.observations,
        results=items,
        reasoning_engine="Jena Fuseki + SPARQL (前向链)",
        reasoning_path=reasoning_path,
        disclaimer="本结果由 Jena 前向链推理引擎生成（开放世界假设），仅供参考，"
                    "不能替代执业兽医的诊断。如宠物情况紧急，请立即就医。",
    )

    return report


def _build_reasoning_path(state, items: list) -> str:
    """
    生成人类可读的推理路径。

    说明：
      1. 前向链规则推理（数据驱动）
      2. SPARQL 查询推理一体化
      3. 开放世界假设（OWA）
      4. 传递闭包预计算
    """
    lines = [
        "### 推理路径说明",
        "",
        "本推理基于以下 Jena/RDF 机制：",
        "",
        "1. **前向链规则推理**",
        "   - 规则2：has + necessary → suspected（疑似推断，含物种过滤）",
        "   - 规则3：has + nos → excluded（排除推断）",
        "   - 规则4：suspected + 无 excluded → diagnosed（确诊推断）",
        "",
        "2. **SPARQL 查询推理一体化**",
        "   推理结果（suspected/excluded/diagnosed）由 Jena 前向链预计算，",
        "   SPARQL 查询时自动包含，无需运行时计算。",
        "",
        "3. **开放世界假设（OWA）**",
        "   未断言的症状 ≠ 不存在，只是尚未检查。",
        "   这与 P2/PL2 的封闭世界假设（CWA）相反。",
        "   因此未观测的症状不会自动排除疾病。",
        "",
        "4. **传递闭包预计算**",
        "   TransitiveProperty（:contain）的传递闭包在数据加载时预计算，",
        "   查询时直接读取，无需递归。",
        "",
    ]

    # 添加 top diagnosis 的详细解释
    if items:
        top = items[0]
        if top.level in ("确诊", "疑似"):
            lines.append(f"### 关于「{top.disease}」的推理依据")
            lines.append("")
            if top.evidence:
                lines.append(f"**匹配症状**：{', '.join(top.evidence)}")
                lines.append("")
            if top.missing:
                lines.append(f"**未观测症状**：{', '.join(top.missing)}")
                lines.append("   （OWA 下视为尚未检查，不排除疾病）")
                lines.append("")

    lines.append("---")
    lines.append("*推理引擎：Jena Fuseki / rdflib | 前向链 + SPARQL + OWA*")

    return "\n".join(lines)


def format_confidence_bar(confidence: float, width: int = 20) -> str:
    """生成置信度条形图（文本）。"""
    filled = int(confidence * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {confidence:.0%}"

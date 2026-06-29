"""
PL1 报告构建 —— 将 OWL 推理结果格式化为 DiagnosisReport。

输入：
  - state: ConversationState（包含宠物信息 + 已收集的观测）
  - results: pl1_diagnose() 的输出（List[Dict]）

输出：
  - DiagnosisReport（agent_core 统一报告结构）
"""

from agent_core.conversation import DiagnosisReport, DiagnosisItem


def build_pl1_report(state, results: list) -> DiagnosisReport:
    """
    构建 PL1 诊断报告。

    将 OWL DL 推理结果转换为统一的 DiagnosisReport 格式，
    包含推理路径说明（OWL 等价类 + SWRL 规则）。
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
        reasoning_engine="OWL-DL (HermiT) + SWRL",
        reasoning_path=reasoning_path,
        disclaimer="本结果由 OWL 本体推理引擎生成，仅供参"
                    "考，不能替代执业兽医的诊断。如宠物情况紧急，请立即就医。",
    )

    return report


def _build_reasoning_path(state, items: list) -> str:
    """
    生成人类可读的推理路径。

    说明：
      1. OWL 等价类匹配（equivalent_to）
      2. SWRL 规则（necessary / nos）
      3. 物种过滤
    """
    lines = [
        "### 推理路径说明",
        "",
        "本推理基于以下 OWL 本体机制：",
        "",
        "1. **OWL 等价类（Equivalent Class）**",
        "   当病例症状满足某疾病的等价类定义时，",
        "    HermiT 推理机自动将病例分类为该疾病。",
        "",
        "2. **SWRL 规则**",
        "   - necessary 规则：出现任一必要症状 → 标记「疑似」",
        "   - nos 规则：出现排除症状 → 标记「排除」",
        "",
        "3. **物种过滤**",
        f"   仅保留物种为「{state.subject.species or '未知'}」的疾病。",
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
                lines.append(f"**未收集症状**：{', '.join(top.missing)}")
                lines.append("   （收集这些症状有助于提升置信度）")
                lines.append("")

    lines.append("---");
    lines.append("*推理引擎：HermiT 1.4 | OWL 2 DL*");

    return "\n".join(lines)


def format_confidence_bar(confidence: float, width: int = 20) -> str:
    """生成置信度条形图（文本）。"""
    filled = int(confidence * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {confidence:.0%}"

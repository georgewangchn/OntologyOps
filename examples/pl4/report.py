"""
PL4 报告构建 —— 将 Mamdani 模糊推理结果格式化为 DiagnosisReport。

输入：
  - state: ConversationState（包含宠物信息 + 已收集的观测）
  - results: pl4_diagnose() 的输出（List[Dict]）

输出：
  - DiagnosisReport（agent_core 统一报告结构）
"""

from agent_core.conversation import DiagnosisReport, DiagnosisItem


def build_pl4_report(state, results: list) -> DiagnosisReport:
    """
    构建 PL4 诊断报告。

    将 Mamdani 模糊推理结果转换为统一的 DiagnosisReport 格式，
    包含推理路径说明（模糊化 + 规则触发 + 去模糊化）。
    """
    items = []

    for r in results:
        item = DiagnosisItem(
            disease=r.get("disease", "未知"),
            confidence=r.get("confidence", 0.0),
            level=r.get("level", ""),  # 高/中/低（模糊等级）
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
        reasoning_engine="scikit-fuzzy Mamdani (模糊推理)",
        reasoning_path=reasoning_path,
        disclaimer="本结果由 Mamdani 模糊推理引擎生成（连续置信度），仅供参考，"
                    "不能替代执业兽医的诊断。如宠物情况紧急，请立即就医。",
    )

    return report


def _build_reasoning_path(state, items: list) -> str:
    """
    生成人类可读的推理路径。

    说明：
      1. 模糊化（Fuzzification）
      2. Mamdani 规则推理
      3. 去模糊化（Defuzzification）
      4. 与确定性推理的区别
    """
    lines = [
        "### 推理路径说明",
        "",
        "本推理基于 Mamdani 模糊逻辑：",
        "",
        "1. **模糊化（Fuzzification）**",
        "   将症状详情映射为连续严重度（0-1）：",
        "   - 发热 39.5°C → 严重度 0.80",
        "   - 呕吐多次 → 严重度 0.70",
        "   然后将严重度映射到模糊集合（低/中/高）。",
        "",
        "2. **三维模糊输入**",
        "   - 覆盖率：已出现必要症状数 / 总数（有多少症状在）",
        "   - 强度：已出现症状的严重度均值（有多严重）",
        "   - 排除度：排除症状严重度最大值（模糊 OR）",
        "",
        "3. **Mamdani 规则推理**",
        "   12 条 IF-THEN 规则，三输入（覆盖率 × 强度 × 排除度）→ 置信度。",
        "   激活强度 = min(条件隶属度)。",
        "   所有规则输出取 max（聚合）。",
        "",
        "4. **去模糊化（Defuzzification）**",
        "   重心法（centroid）将输出模糊集合转为连续置信度（0-1）。",
        "",
        "5. **与 P1-P3 确定性推理的区别**",
        "   - P1-P3：症状有/无（二元）→ 疾病是/否（二元）",
        "   - P4：症状严重度（连续 0-1）→ 疾病置信度（连续 0-1）",
        "   - 排除症状不完全排除疾病，而是降低置信度",
        "   - 症状严重度直接影响推理结果（高烧 > 低烧）",
        "",
    ]

    # 添加 top diagnosis 的详细解释
    if items:
        top = items[0]
        lines.append(f"### 关于「{top.disease}」的推理依据")
        lines.append("")
        lines.append(f"**置信度**：{top.confidence:.2f}（等级：{top.level}）")
        lines.append("")
        if top.evidence:
            lines.append(f"**匹配症状**：{', '.join(top.evidence)}")
            lines.append("")
        if top.missing:
            lines.append(f"**未观测症状**：{', '.join(top.missing)}")
            lines.append("   （在模糊推理中，未观测症状严重度为 0，但不会完全排除疾病）")
            lines.append("")

    lines.append("---")
    lines.append("*推理引擎：scikit-fuzzy | Mamdani 模糊推理 + 重心法去模糊化*")

    return "\n".join(lines)


def format_confidence_bar(confidence: float, width: int = 20) -> str:
    """生成置信度条形图（文本）。"""
    filled = int(confidence * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {confidence:.0%}"

"""
PL2 报告构建 —— 将 Prolog 推理结果格式化为 DiagnosisReport。

输入：
  - state: ConversationState（包含宠物信息 + 已收集的观测）
  - results: pl2_diagnose() 的输出（List[Dict]）

输出：
  - DiagnosisReport（agent_core 统一报告结构）
"""

from agent_core.conversation import DiagnosisReport, DiagnosisItem


def build_pl2_report(state, results: list) -> DiagnosisReport:
    """
    构建 PL2 诊断报告。

    将 Prolog SLD 归结推理结果转换为统一的 DiagnosisReport 格式，
    包含推理路径说明（Horn 子句 + CWA + SLD 归结）。
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
        reasoning_engine="Prolog (SWI-Prolog) + SLD",
        reasoning_path=reasoning_path,
        disclaimer="本结果由 Prolog 逻辑推理引擎生成（封闭世界假设），仅供参考，"
                    "不能替代执业兽医的诊断。如宠物情况紧急，请立即就医。",
    )

    return report


def _build_reasoning_path(state, items: list) -> str:
    """
    生成人类可读的推理路径。

    说明：
      1. Horn 子句规则推理
      2. SLD 归结（目标驱动）
      3. 封闭世界假设（CWA）：未断言 = 不存在
      4. 物种过滤
    """
    lines = [
        "### 推理路径说明",
        "",
        "本推理基于以下 Prolog 逻辑机制：",
        "",
        "1. **Horn 子句规则**",
        "   - diagnose/2：必要症状全匹配 + 排除症状未命中 → 确诊",
        "   - suspect/3：部分匹配 + 置信度 = 匹配数 / 总数",
        "   - excluded/2：命中排除症状 → 排除",
        "",
        "2. **SLD 归结**",
        "   Prolog 从目标出发，自顶向下归结，",
        "   逐条尝试规则体中的子目标。",
        "",
        "3. **封闭世界假设（CWA）**",
        "   未断言的症状 = 不存在。",
        "   `\\+ has(case, '咳嗽')` 在未记录咳嗽时即为 true。",
        "   这与 P1/PL1 的开放世界假设（OWA）相反。",
        "",
        "4. **物种过滤**",
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
                lines.append("   （CWA 下视为不存在，因此无法确诊）")
                lines.append("")

    lines.append("---")
    lines.append("*推理引擎：SWI-Prolog 9.x | Horn 子句 + SLD 归结 + CWA*")

    return "\n".join(lines)


def format_confidence_bar(confidence: float, width: int = 20) -> str:
    """生成置信度条形图（文本）。"""
    filled = int(confidence * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {confidence:.0%}"

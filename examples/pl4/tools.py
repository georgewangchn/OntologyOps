"""
PL4 工具集 —— 包装 P4 的模糊逻辑推理能力，供 OntologyAgent 调用。

工具列表（由 create_pl4_tools 统一创建）：

  1. lookup_symptom_fuzzy(symptom_name)
       在模糊知识库中查找症状，返回关联疾病 + 基线严重度。
  2. lookup_disease_fuzzy(disease_name)
       查找疾病，返回必要症状、排除症状、物种约束。
  3. add_observation(symptom_name, severity, details)
       向 ConversationState 添加一条观测记录（含严重度详情）。
  4. set_pet_info(species, breed, age, sex)
       设置宠物基本信息。
  5. run_fuzzy_reasoning()
       基于当前 state 收集的信息，运行 Mamdani 模糊推理，返回诊断报告。
  6. explain_fuzzy_reasoning(disease_name)
       解释某个疾病的模糊推理链（覆盖率/强度/排除度 + 规则触发）。
  7. get_symptom_severity(symptom_name)
       查询某症状的当前严重度（模糊化输入）。
  8. get_case_summary()
       返回当前病例摘要。

依赖：
  - scikit-fuzzy（Mamdani 模糊推理）
  - P4 的 reasoner / kb_builder / utils 模块
  - 知识库文件：ontologyops/examples/P4/data/fuzzy_kb.json
"""

import os
import sys
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# P4 模块路径
_P4_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P4", "src"
)
if _P4_DIR not in sys.path:
    sys.path.insert(0, _P4_DIR)

_P4_DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P4", "data"
)

# 模块级缓存
_kb = None


def _get_kb():
    """懒加载模糊知识库。"""
    global _kb
    if _kb is None:
        try:
            from reasoner import load_knowledge_base
            _kb = load_knowledge_base()
            logger.info("模糊知识库已加载")
        except Exception as e:
            logger.error(f"加载模糊知识库失败：{e}")
            raise
    return _kb


def create_pl4_tools(state, diagnose_fn, report_builder):
    """
    PL4 工具工厂，供 OntologyAgent 调用。

    Args:
        state: ConversationState 实例
        diagnose_fn: 诊断函数（PL4 中即 pl4_diagnose）
        report_builder: 报告构建函数（PL4 中即 build_pl4_report）

    Returns:
        list[Tool]: LangChain Tool 列表
    """

    # ============================================================
    # 工具 1: 查找症状（模糊版）
    # ============================================================

    @tool
    def lookup_symptom_fuzzy(symptom_name: str) -> str:
        """
        在模糊知识库中查找症状。
        返回症状关联的疾病列表 + 基线严重度。

        与 PL1-PL3 不同：模糊知识库中每个症状都有基线严重度（0-1）。

        示例:
            lookup_symptom_fuzzy("发热") → 返回发热关联的疾病 + 基线严重度
        """
        kb = _get_kb()
        baselines = kb.get("symptom_baselines", {})

        matched_diseases = []
        for disease in kb["diseases"]:
            necessary = disease.get("necessary_symptoms", [])
            exclusion = disease.get("exclusion_symptoms", [])

            if symptom_name in necessary:
                matched_diseases.append(f"{disease['name']}（必要症状）")
            if symptom_name in exclusion:
                matched_diseases.append(f"{disease['name']}（排除症状）")

        baseline = baselines.get(symptom_name)

        if matched_diseases:
            lines = [f"症状「{symptom_name}」关联以下疾病："]
            for d in matched_diseases[:10]:
                lines.append(f"  - {d}")
            if baseline is not None:
                lines.append(f"\n基线严重度：{baseline:.2f}")
            return "\n".join(lines)

        # 模糊匹配
        candidates = []
        for s in baselines:
            if symptom_name in s or s in symptom_name:
                candidates.append(s)

        if candidates:
            return (
                f"未找到「{symptom_name}」的精确匹配。\n"
                f"相关症状：{', '.join(candidates[:5])}？"
            )

        return f"未找到症状「{symptom_name}」，请检查名称是否正确。"

    # ============================================================
    # 工具 2: 查找疾病（模糊版）
    # ============================================================

    @tool
    def lookup_disease_fuzzy(disease_name: str) -> str:
        """
        在模糊知识库中查找疾病。
        返回疾病的必要症状、排除症状、物种约束。

        示例:
            lookup_disease_fuzzy("猫瘟") → 返回 D001 的详细信息
        """
        kb = _get_kb()

        target = None
        for disease in kb["diseases"]:
            dname = disease["name"]
            if disease_name in dname or dname in disease_name:
                target = disease
                break

        if target is None:
            return f"未找到疾病「{disease_name}」。"

        lines = [
            f"疾病：{target['name']}（{target['id']}）",
            f"  必要症状：{', '.join(target.get('necessary_symptoms', []))}",
        ]
        if target.get("exclusion_symptoms"):
            lines.append(f"  排除症状：{', '.join(target['exclusion_symptoms'])}")
        lines.append(f"  物种约束：{target.get('species', '通用')}")

        return "\n".join(lines)

    # ============================================================
    # 工具 3: 添加观测（含严重度详情）
    # ============================================================

    @tool
    def add_observation(symptom_name: str, severity: str = "", details: dict = None) -> str:
        """
        向病例添加一条观测记录。
        PL4 特有：可以记录症状的严重度详情（体温、频率等），影响模糊推理结果。

        参数:
            symptom_name: 症状名称（如"发热"、"呕吐"）
            severity: 严重度（如"重度"、"中度"、"轻度"），可选
            details: 附加详情，PL4 中直接影响模糊推理：
                - 发热：{"value": 39.5}（体温值，°C）
                - 呕吐：{"frequency": "频繁"}（偶尔/多次/频繁）
                - 腹泻：{"type": "水样", "color": "暗红"}

        示例:
            add_observation("发热", severity="重度", details={"value": 40.2})
            add_observation("呕吐", details={"frequency": "频繁"})
            add_observation("腹泻")
        """
        state.add_observation(symptom_name, severity=severity, details=details)
        return f"已记录：{symptom_name}" + (f"（{severity}）" if severity else "")

    # ============================================================
    # 工具 4: 设置宠物信息
    # ============================================================

    @tool
    def set_pet_info(species: str, breed: str = "", age: int = None, sex: str = "") -> str:
        """
        设置宠物基本信息。

        参数:
            species: 物种（"猫" 或 "犬"）
            breed: 品种（如"英短"、"金毛"），可选
            age: 年龄（岁），可选
            sex: 性别（"公" 或 "母"），可选
        """
        state.set_subject(species=species, breed=breed, age=age, sex=sex)
        parts = [f"物种：{species}"]
        if breed:
            parts.append(f"品种：{breed}")
        if age is not None:
            parts.append(f"年龄：{age}岁")
        if sex:
            parts.append(f"性别：{sex}")
        return "已设置宠物信息：" + "，".join(parts)

    # ============================================================
    # 工具 5: 运行模糊推理
    # ============================================================

    @tool
    def run_fuzzy_reasoning() -> str:
        """
        基于当前病例信息，运行 Mamdani 模糊推理，返回诊断报告。

        该工具会：
          1. 将 state 中的信息转换为 P4 诊断函数所需的格式
          2. 计算每个疾病的覆盖率、强度、排除度
          3. 执行 Mamdani 模糊推理（12 条 IF-THEN 规则）
          4. 去模糊化（重心法）得到连续置信度
          5. 返回格式化的诊断报告

        注意：需要至少设置宠物物种和 2 条以上症状才能推理。
        PL4 特有：症状的严重度详情会直接影响推理结果。
        """
        if not state.is_ready_for_reasoning():
            missing = []
            if not state.subject.is_complete():
                missing.append("宠物物种")
            if len(state.observations) < state.min_observations_for_reasoning:
                missing.append(f"至少 {state.min_observations_for_reasoning} 条症状")
            return (
                f"信息不足，无法推理。缺少：{', '.join(missing)}。\n"
                f"当前已收集：{len(state.observations)} 条症状。"
            )

        try:
            case_dict = state.to_case_dict()
            results = diagnose_fn(case_dict)

            if not results:
                return "推理未返回结果。请检查症状输入是否正确。"

            report = report_builder(state, results)
            return report.format_for_user()

        except Exception as e:
            logger.error(f"推理失败：{e}")
            return f"推理引擎出错：{e}。请检查输入信息是否正确。"

    # ============================================================
    # 工具 6: 解释模糊推理链
    # ============================================================

    @tool
    def explain_fuzzy_reasoning(disease_name: str) -> str:
        """
        解释某个疾病的模糊推理链。
        展示覆盖率、强度、排除度的计算过程 + 触发的模糊规则。

        与 PL1-PL3 的解释不同：
        - PL1-PL3：二元结果（确诊/排除）+ 匹配/未匹配列表
        - PL4：连续置信度 + 三维模糊输入（覆盖率/强度/排除度）

        示例:
            explain_fuzzy_reasoning("猫瘟")
        """
        kb = _get_kb()

        target = None
        for disease in kb["diseases"]:
            dname = disease["name"]
            if disease_name in dname or dname in disease_name:
                target = disease
                break

        if target is None:
            return f"未找到疾病「{disease_name}」。"

        # 收集必要症状的严重度
        from utils import compute_symptom_severity, compute_coverage, compute_intensity, compute_exclusion_degree, load_symptom_baselines

        case_dict = state.to_case_dict()
        baselines = load_symptom_baselines()

        necessary = target.get("necessary_symptoms", [])
        exclusion = target.get("exclusion_symptoms", [])

        lines = [
            f"### 疾病：{target['name']}",
            "",
            "**必要症状**：",
        ]

        for s in necessary:
            sev = compute_symptom_severity(s, case_dict, baselines)
            present = s in case_dict.get("observations", [])
            tag = f"严重度={sev:.2f}" if present else "未观测"
            lines.append(f"  {'✅' if present else '❓'} {s}（{tag}）")

        if exclusion:
            lines.append("")
            lines.append("**排除症状**：")
            for s in exclusion:
                sev = compute_symptom_severity(s, case_dict, baselines)
                present = s in case_dict.get("observations", [])
                tag = f"严重度={sev:.2f}" if present else "未命中"
                lines.append(f"  {'⚠️' if present else '✅'} {s}（{tag}）")

        # 计算三个模糊输入
        coverage = compute_coverage(necessary, case_dict)
        intensity = compute_intensity(necessary, case_dict, baselines)
        exclusion_degree = compute_exclusion_degree(exclusion, case_dict, baselines)

        lines.append("")
        lines.append("**模糊推理输入**：")
        lines.append(f"  覆盖率：{coverage:.2f}（已出现必要症状比例）")
        lines.append(f"  强度：{intensity:.2f}（已出现症状的严重度均值）")
        lines.append(f"  排除度：{exclusion_degree:.2f}（排除症状严重度最大值）")

        lines.append("")
        lines.append("**Mamdani 推理流程**：")
        lines.append("  1. 模糊化：将覆盖率/强度/排除度映射到模糊集合（低/中/高）")
        lines.append("  2. 规则触发：12 条 IF-THEN 规则，激活强度 = min(条件隶属度)")
        lines.append("  3. 合成：所有规则输出取 max（聚合）")
        lines.append("  4. 去模糊化：重心法 → 连续置信度（0-1）")

        lines.append("")
        lines.append("**与 P1-P3 确定性推理的区别**：")
        lines.append("  · 置信度是连续值（0-1），不是二元（确诊/排除）")
        lines.append("  · 排除症状不完全排除疾病，而是降低置信度")
        lines.append("  · 症状严重度影响推理结果（高烧 > 低烧）")

        return "\n".join(lines)

    # ============================================================
    # 工具 7: 查询症状严重度
    # ============================================================

    @tool
    def get_symptom_severity(symptom_name: str) -> str:
        """
        查询某症状的当前严重度（模糊化输入值）。

        PL4 独有工具：展示症状如何从自然语言详情转换为连续严重度。

        示例:
            get_symptom_severity("发热") → 返回当前发热的严重度
        """
        from utils import compute_symptom_severity, load_symptom_baselines

        kb = _get_kb()
        baselines = load_symptom_baselines()
        case_dict = state.to_case_dict()

        observations = case_dict.get("observations", [])
        if symptom_name not in observations:
            baseline = baselines.get(symptom_name, "未知")
            return f"症状「{symptom_name}」尚未观测。基线严重度：{baseline}"

        sev = compute_symptom_severity(symptom_name, case_dict, baselines)
        baseline = baselines.get(symptom_name, "未知")

        # 查找该症状的详情
        obs = None
        for o in state.observations:
            if o.name == symptom_name:
                obs = o
                break

        lines = [
            f"### 症状：{symptom_name}",
            f"  当前严重度：{sev:.2f}",
            f"  基线严重度：{baseline}",
        ]

        if obs and obs.details:
            details_str = ", ".join(f"{k}={v}" for k, v in obs.details.items())
            lines.append(f"  详情：{details_str}")

        if obs and obs.severity:
            lines.append(f"  严重度标签：{obs.severity}")

        return "\n".join(lines)

    # ============================================================
    # 工具 8: 获取病例摘要
    # ============================================================

    @tool
    def get_case_summary() -> str:
        """
        返回当前病例的摘要，包括宠物信息和已收集的症状。
        PL4 特有：摘要中包含症状的严重度详情。
        """
        parts = [
            f"宠物信息：{state.subject.summary()}",
            f"已收集症状（{len(state.observations)} 条）："
        ]
        for i, obs in enumerate(state.observations, 1):
            line = f"  {i}. {obs.name}"
            if obs.severity:
                line += f"（{obs.severity}）"
            if obs.details:
                details_str = ", ".join(f"{k}={v}" for k, v in obs.details.items())
                line += f" [{details_str}]"
            parts.append(line)

        parts.append("")
        if state.is_ready_for_reasoning():
            parts.append("✅ 信息已足够，可以运行推理。")
        else:
            parts.append("⚠️ 信息不足，建议继续收集信息。")

        return "\n".join(parts)

    # ============================================================
    # 返回工具列表
    # ============================================================

    return [
        lookup_symptom_fuzzy,
        lookup_disease_fuzzy,
        add_observation,
        set_pet_info,
        run_fuzzy_reasoning,
        explain_fuzzy_reasoning,
        get_symptom_severity,
        get_case_summary,
    ]

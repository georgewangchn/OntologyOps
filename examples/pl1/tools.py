"""
PL1 工具集 —— 包装 P1 的 OWL 本体推理能力，供 OntologyAgent 调用。

工具列表（由 create_pl1_tools 统一创建）：

  1. lookup_symptom_owl(symptom_name)
       在 OWL 本体中查找症状，返回名称、ID、常见于哪些疾病。
  2. lookup_disease_owl(disease_name)
       在 OWL 本体中查找疾病，返回必要症状、排除症状、置信度计算方式。
  3. add_observation(symptom_name, severity, details)
       向 ConversationState 添加一条观测记录。
  4. set_pet_info(species, breed, age, sex)
       设置宠物基本信息。
  5. run_dl_reasoning()
       基于当前 state 收集的信息，运行 HermiT DL 推理，返回诊断报告。
  6. explain_subsumption(disease_name)
       解释为什么某个疾病被推理出来（哪些症状匹配了必要条件）。
  7. get_case_summary()
       返回当前病例摘要（宠物信息 + 已收集的症状）。

依赖：
  - owlready2-Chinese（fork 版本，支持中文 IRI）
  - P1 的 onto_builder / reasoner / diagnosis 模块
  - 本体文件：ontologyops/examples/P1/data/pet_ontology.owl
"""

import os
import sys
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# P1 模块路径
_P1_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P1", "src"
)
if _P1_DIR not in sys.path:
    sys.path.insert(0, _P1_DIR)

_ONTO_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P1", "data", "pet_ontology.owl"
)

# 模块级缓存：避免每次工具调用都重新加载本体
_ONTO = None


def _get_onto():
    """懒加载 OWL 本体（进程内缓存）。"""
    global _ONTO
    if _ONTO is None:
        try:
            from reasoner import load_ontology
            _ONTO = load_ontology(_ONTO_PATH)
            logger.info(f"OWL 本体已加载：{len(list(_ONTO.classes()))} 个类")
        except Exception as e:
            logger.error(f"加载 OWL 本体失败：{e}")
            raise
    return _ONTO


def create_pl1_tools(state, diagnose_fn, report_builder):
    """
    PL1 工具工厂，供 OntologyAgent 调用。

    Args:
        state: ConversationState 实例（由 OntologyAgent._rebuild 创建）
        diagnose_fn: 诊断函数（PL1 中即 pl1_diagnose）
        report_builder: 报告构建函数（PL1 中即 build_pl1_report）

    Returns:
        list[Tool]: LangChain Tool 列表
    """

    # ============================================================
    # 工具 1: 查找症状
    # ============================================================

    @tool
    def lookup_symptom_owl(symptom_name: str) -> str:
        """
        在 OWL 本体中查找症状。
        返回症状的名称、ID、以及常见于哪些疾病。

        示例:
            lookup_symptom_owl("发热") → 返回 S001 的详细信息
            lookup_symptom_owl("发烧") → 模糊匹配，提示"是否指「发热」？"
        """
        onto = _get_onto()

        # 精确匹配（按 label 或 name）
        matched = []
        candidates = []
        for s in onto.search(type=onto.症状):
            label = s.label[0] if s.label else s.name
            name = s.name
            if symptom_name in label or symptom_name in name:
                matched.append(s)
            elif symptom_name in label or symptom_name == label:
                matched.append(s)
            else:
                # 模糊匹配：计算编辑距离（简单版：检查是否包含关键词）
                keywords = symptom_name.replace(" ", "")
                if keywords in label or keywords in name:
                    candidates.append(label or name)

        if matched:
            results = []
            for s in matched[:5]:
                label = s.label[0] if s.label else s.name
                # 查找该症状出现在哪些疾病中
                # 疾病-症状关系在 is_a 中通过 necessary.value() 表达
                # 同时也存在于疾病 KB 个体（D001_kb 等）
                diseases_with_symptom = []
                for d in onto.search(type=onto.疾病):
                    # 跳过 KB 个体（以 _kb 结尾）
                    if d.name.endswith("_kb"):
                        continue
                    d_label = d.label[0] if d.label else d.name
                    found = False
                    # 检查 is_a 中的 necessary 限制
                    for res in d.is_a:
                        if hasattr(res, "property") and res.property is onto.necessary:
                            if res.value is s:
                                found = True
                                break
                    if found and d_label not in diseases_with_symptom:
                        diseases_with_symptom.append(d_label)
                results.append(
                    f"症状：{label}（{s.name}）\n"
                    f"  常见于：{', '.join(diseases_with_symptom[:5]) if diseases_with_symptom else '未知'}"
                )
            return "\n\n".join(results)

        if candidates:
            return (
                f"未找到「{symptom_name}」的精确匹配。\n"
                f"您是否指：{', '.join(candidates[:5])}？"
            )

        return f"未找到症状「{symptom_name}」，请检查名称是否正确。"

    # ============================================================
    # 工具 2: 查找疾病
    # ============================================================

    @tool
    def lookup_disease_owl(disease_name: str) -> str:
        """
        在 OWL 本体中查找疾病。
        返回疾病的必要症状、排除症状、物种约束。

        示例:
            lookup_disease_owl("猫瘟") → 返回 D001 的详细信息
        """
        onto = _get_onto()

        matched = []
        for d in onto.search(type=onto.疾病):
            label = d.label[0] if d.label else d.name
            if disease_name in label or disease_name in d.name:
                matched.append(d)

        if not matched:
            return f"未找到疾病「{disease_name}」。"

        results = []
        for d in matched[:3]:
            label = d.label[0] if d.label else d.name

            # 必要症状
            necessary = []
            for res in d.is_a:
                if hasattr(res, 'property') and res.property is onto.necessary:
                    necessary.append(res.value.label[0] if res.value.label else res.value.name)

            # 排除症状（从 comment 解析）
            nos = []
            for c in d.comment:
                if isinstance(c, str) and c.startswith("nos:"):
                    nos = c[4:].split(";")

            # 物种约束
            species_constraint = []
            for res in d.is_a:
                if hasattr(res, 'property') and res.property is onto.hasSpecies:
                    s_label = res.value.label[0] if res.value.label else res.value.name
                    species_constraint.append(s_label)

            result = f"疾病：{label}（{d.name}）\n"
            if necessary:
                result += f"  必要症状：{', '.join(necessary)}\n"
            if nos:
                result += f"  排除症状：{', '.join(nos)}\n"
            if species_constraint:
                result += f"  物种约束：{', '.join(species_constraint)}\n"

            results.append(result.strip())

        return "\n\n".join(results)

    # ============================================================
    # 工具 3: 添加观测
    # ============================================================

    @tool
    def add_observation(symptom_name: str, severity: str = "", details: dict = None) -> str:
        """
        向病例添加一条观测记录。
        如果症状不在本体中，会提示并仍保留记录。

        参数:
            symptom_name: 症状名称（如"发热"、"呕吐"）
            severity: 严重度（如"重度"、"中度"、"轻度"），可选
            details: 附加详情（如 {"体温": 40.2}），可选

        示例:
            add_observation("发热", severity="重度", details={"体温": 40.2})
            add_observation("呕吐")
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

        示例:
            set_pet_info(species="猫", breed="英短", age=3, sex="公")
            set_pet_info(species="犬")
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
    # 工具 5: 运行 DL 推理
    # ============================================================

    @tool
    def run_dl_reasoning() -> str:
        """
        基于当前病例信息，运行 OWL DL 推理（HermiT），返回诊断报告。

        该工具会：
          1. 将 state 中的信息转换为 P1 诊断函数所需的格式
          2. 运行 HermiT 推理
          3. 计算置信度
          4. 返回格式化的诊断报告

        注意：需要至少设置宠物物种和 2 条以上症状才能推理。
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
    # 工具 6: 解释推理路径
    # ============================================================

    @tool
    def explain_subsumption(disease_name: str) -> str:
        """
        解释为什么某个疾病被推理出来。
        列出匹配的必要症状、未匹配的必要症状、以及任何排除症状。

        示例:
            explain_subsumption("猫瘟")
        """
        onto = _get_onto()

        # 查找疾病
        target = None
        for d in onto.search(type=onto.疾病):
            label = d.label[0] if d.label else d.name
            if disease_name in label or disease_name in d.name:
                target = d
                break

        if target is None:
            return f"未找到疾病「{disease_name}」。"

        d_label = target.label[0] if target.label else target.name

        # 收集必要症状
        necessary = []
        for res in target.is_a:
            if hasattr(res, 'property') and res.property is onto.necessary:
                necessary.append(res.value)

        # 收集排除症状
        nos = []
        for c in target.comment:
            if isinstance(c, str) and c.startswith("nos:"):
                nos_names = c[4:].split(";")
                nos = [n.strip() for n in nos_names]

        # 匹配当前症状
        matched = []
        unmatched = []
        for s in necessary:
            s_label = s.label[0] if s.label else s.name
            if any(s_label in obs.name or obs.name in s_label for obs in state.observations):
                matched.append(s_label)
            else:
                unmatched.append(s_label)

        # 检查排除症状
        excluded_by = []
        for n in nos:
            if any(n in obs.name or obs.name in n for obs in state.observations):
                excluded_by.append(n)

        lines = [
            f"### 疾病：{d_label}",
            "",
            f"**必要症状（共 {len(necessary)} 项）**：",
        ]
        for s_label in matched:
            lines.append(f"  ✅ {s_label}（已观测）")
        for s_label in unmatched:
            lines.append(f"  ❌ {s_label}（未观测）")

        if excluded_by:
            lines.append("")
            lines.append(f"**排除症状（已观测，可排除该病）**：")
            for n in excluded_by:
                lines.append(f"  ⚠️ {n}")

        if not necessary:
            lines.append("（该疾病未定义必要症状）")

        return "\n".join(lines)

    # ============================================================
    # 工具 7: 获取病例摘要
    # ============================================================

    @tool
    def get_case_summary() -> str:
        """
        返回当前病例的摘要，包括宠物信息和已收集的症状。
        用于检查当前状态，决定是否需要继续追问。
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
        lookup_symptom_owl,
        lookup_disease_owl,
        add_observation,
        set_pet_info,
        run_dl_reasoning,
        explain_subsumption,
        get_case_summary,
    ]

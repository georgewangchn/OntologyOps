"""
PL2 工具集 —— 包装 P2 的 Prolog 逻辑推理能力，供 OntologyAgent 调用。

工具列表（由 create_pl2_tools 统一创建）：

  1. lookup_symptom_prolog(symptom_name)
       在 Prolog 知识库中查找症状，返回名称、关联疾病。
  2. lookup_disease_prolog(disease_name)
       在 Prolog 知识库中查找疾病，返回必要症状、排除症状、物种约束。
  3. add_observation(symptom_name, severity, details)
       向 ConversationState 添加一条观测记录。
  4. set_pet_info(species, breed, age, sex)
       设置宠物基本信息。
  5. run_prolog_reasoning()
       基于当前 state 收集的信息，运行 Prolog SLD 推理，返回诊断报告。
  6. explain_reasoning_chain(disease_name)
       解释某个疾病的推理链（匹配/缺失/排除症状）。
  7. query_transmit_chain(disease_name)
       查询疾病传播链（Prolog 递归推理独有能力）。
  8. get_case_summary()
       返回当前病例摘要。

依赖：
  - pyswip（Python ↔ SWI-Prolog 桥接）
  - P2 的 reasoner / kb_builder 模块
  - 知识库文件：ontologyops/examples/P2/data/pet_kb.pl
"""

import os
import sys
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# P2 模块路径
_P2_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P2", "src"
)
if _P2_DIR not in sys.path:
    sys.path.insert(0, _P2_DIR)

_RULES_PL = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P2", "src", "rules.pl"
)

_KB_PL = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P2", "data", "pet_kb.pl"
)

# 模块级缓存：Prolog 实例
_PROLOG = None


def _get_prolog():
    """懒加载 Prolog 引擎（进程内缓存）。"""
    global _PROLOG
    if _PROLOG is None:
        try:
            from reasoner import load_knowledge_base
            _PROLOG = load_knowledge_base()
            logger.info("Prolog 知识库已加载")
        except Exception as e:
            logger.error(f"加载 Prolog 知识库失败：{e}")
            raise
    return _PROLOG


def create_pl2_tools(state, diagnose_fn, report_builder):
    """
    PL2 工具工厂，供 OntologyAgent 调用。

    Args:
        state: ConversationState 实例
        diagnose_fn: 诊断函数（PL2 中即 pl2_diagnose）
        report_builder: 报告构建函数（PL2 中即 build_pl2_report）

    Returns:
        list[Tool]: LangChain Tool 列表
    """

    # ============================================================
    # 工具 1: 查找症状（Prolog 版）
    # ============================================================

    @tool
    def lookup_symptom_prolog(symptom_name: str) -> str:
        """
        在 Prolog 知识库中查找症状。
        返回症状关联的疾病列表。

        示例:
            lookup_symptom_prolog("发热") → 返回发热关联的疾病
            lookup_symptom_prolog("发烧") → 模糊匹配，提示"是否指「发热」？"
        """
        prolog = _get_prolog()

        # 查询所有疾病，检查其必要症状和排除症状
        all_diseases = list(prolog.query("disease(DID, Name, Species)"))

        matched_diseases = []
        candidates = []

        for d in all_diseases:
            did = d["DID"]
            dname = d["Name"]

            # 检查必要症状
            nec_results = list(prolog.query(f"necessary({did}, S)"))
            for r in nec_results:
                s_name = str(r["S"])
                if symptom_name == s_name:
                    matched_diseases.append(f"{dname}（必要症状）")
                elif symptom_name in s_name or s_name in symptom_name:
                    if dname not in [m.split("（")[0] for m in matched_diseases]:
                        candidates.append(f"{dname}（症状：{s_name}）")

            # 检查排除症状
            nos_results = list(prolog.query(f"nos({did}, S)"))
            for r in nos_results:
                s_name = str(r["S"])
                if symptom_name == s_name:
                    matched_diseases.append(f"{dname}（排除症状）")

        if matched_diseases:
            return f"症状「{symptom_name}」关联以下疾病：\n" + "\n".join(f"  - {m}" for m in matched_diseases[:10])

        if candidates:
            return (
                f"未找到「{symptom_name}」的精确匹配。\n"
                f"相关：{', '.join(candidates[:5])}？"
            )

        return f"未找到症状「{symptom_name}」，请检查名称是否正确。"

    # ============================================================
    # 工具 2: 查找疾病（Prolog 版）
    # ============================================================

    @tool
    def lookup_disease_prolog(disease_name: str) -> str:
        """
        在 Prolog 知识库中查找疾病。
        返回疾病的必要症状、排除症状、物种约束。

        示例:
            lookup_disease_prolog("猫瘟") → 返回 d001 的详细信息
        """
        prolog = _get_prolog()

        all_diseases = list(prolog.query("disease(DID, Name, Species)"))

        target = None
        for d in all_diseases:
            dname = str(d["Name"])
            if disease_name in dname or dname in disease_name:
                target = d
                break

        if target is None:
            return f"未找到疾病「{disease_name}」。"

        did = target["DID"]
        dname = target["Name"]
        species = target["Species"]

        # 必要症状
        nec_results = list(prolog.query(f"necessary({did}, S)"))
        necessary = [str(r["S"]) for r in nec_results]

        # 排除症状
        nos_results = list(prolog.query(f"nos({did}, S)"))
        nos = [str(r["S"]) for r in nos_results]

        lines = [f"疾病：{dname}（{did}）"]
        if necessary:
            lines.append(f"  必要症状：{', '.join(necessary)}")
        if nos:
            lines.append(f"  排除症状：{', '.join(nos)}")
        lines.append(f"  物种约束：{species}")

        return "\n".join(lines)

    # ============================================================
    # 工具 3: 添加观测
    # ============================================================

    @tool
    def add_observation(symptom_name: str, severity: str = "", details: dict = None) -> str:
        """
        向病例添加一条观测记录。
        如果症状不在知识库中，会提示并仍保留记录。

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
    # 工具 5: 运行 Prolog 推理
    # ============================================================

    @tool
    def run_prolog_reasoning() -> str:
        """
        基于当前病例信息，运行 Prolog SLD 归结推理，返回诊断报告。

        该工具会：
          1. 将 state 中的信息转换为 P2 诊断函数所需的格式
          2. 断言症状到 Prolog，执行 diagnose/suspect/excluded 查询
          3. 计算置信度（匹配率）
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
    # 工具 6: 解释推理链
    # ============================================================

    @tool
    def explain_reasoning_chain(disease_name: str) -> str:
        """
        解释某个疾病的推理链。
        列出匹配的必要症状、未匹配的必要症状、以及任何排除症状。

        与 PL1 的 explain_subsumption 不同：
        - PL1 基于 OWL 等价类匹配
        - PL2 基于 Prolog SLD 归结 + CWA（未断言 = 不存在）

        示例:
            explain_reasoning_chain("猫瘟")
        """
        prolog = _get_prolog()

        # 查找疾病
        all_diseases = list(prolog.query("disease(DID, Name, Species)"))
        target = None
        for d in all_diseases:
            dname = str(d["Name"])
            if disease_name in dname or dname in disease_name:
                target = d
                break

        if target is None:
            return f"未找到疾病「{disease_name}」。"

        did = target["DID"]
        dname = target["Name"]

        # 收集必要症状
        nec_results = list(prolog.query(f"necessary({did}, S)"))
        necessary = [str(r["S"]) for r in nec_results]

        # 收集排除症状
        nos_results = list(prolog.query(f"nos({did}, S)"))
        nos = [str(r["S"]) for r in nos_results]

        # 匹配当前症状
        current_symptoms = [obs.name for obs in state.observations]
        matched = []
        unmatched = []
        for nec in necessary:
            if any(nec in s or s in nec for s in current_symptoms):
                matched.append(nec)
            else:
                unmatched.append(nec)

        # 检查排除症状
        excluded_by = []
        for n in nos:
            if any(n in s or s in n for s in current_symptoms):
                excluded_by.append(n)

        lines = [
            f"### 疾病：{dname}",
            "",
            f"**必要症状（共 {len(necessary)} 项）**：",
        ]
        for s in matched:
            lines.append(f"  ✅ {s}（已观测）")
        for s in unmatched:
            lines.append(f"  ❌ {s}（未观测）")

        if excluded_by:
            lines.append("")
            lines.append(f"**排除症状（已观测，可排除该病）**：")
            for n in excluded_by:
                lines.append(f"  ⚠️ {n}")

        # CWA 说明
        if unmatched:
            lines.append("")
            lines.append("**CWA 说明**：在封闭世界假设下，未观测 = 不存在。")
            lines.append("因此这些未观测症状将导致该疾病无法确诊。")

        if not necessary:
            lines.append("（该疾病未定义必要症状）")

        return "\n".join(lines)

    # ============================================================
    # 工具 7: 查询传播链（Prolog 递归独有能力）
    # ============================================================

    @tool
    def query_transmit_chain(disease_name: str) -> str:
        """
        查询疾病传播链。
        利用 Prolog 的递归推理能力，追踪疾病之间的传播关系。

        这是 Prolog 独有的能力 —— OWL/SWRL 只能做传递闭包，
        无法表达条件递归。

        示例:
            query_transmit_chain("猫感冒") → 可能继发猫瘟
        """
        prolog = _get_prolog()

        # 查找疾病 ID
        all_diseases = list(prolog.query("disease(DID, Name, Species)"))
        source_id = None
        source_name = disease_name
        for d in all_diseases:
            dname = str(d["Name"])
            if disease_name in dname or dname in disease_name:
                source_id = d["DID"]
                source_name = dname
                break

        if source_id is None:
            return f"未找到疾病「{disease_name}」。"

        # 查询传播链
        from reasoner import query_transmit
        try:
            chain = query_transmit(prolog, source_id)
        except Exception as e:
            return f"查询传播链失败：{e}"

        if not chain:
            return f"「{source_name}」没有已知的传播链路。"

        lines = [f"### 传播链：{source_name}"]
        for item in chain:
            lines.append(f"  → {item['to_name']}（{item['to']}）")

        lines.append("")
        lines.append("*传播链由 Prolog 递归推理生成（can_transmit/2）*")

        return "\n".join(lines)

    # ============================================================
    # 工具 8: 获取病例摘要
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
        lookup_symptom_prolog,
        lookup_disease_prolog,
        add_observation,
        set_pet_info,
        run_prolog_reasoning,
        explain_reasoning_chain,
        query_transmit_chain,
        get_case_summary,
    ]

"""
PL3 工具集 —— 包装 P3 的 Jena/SPARQL 三元组推理能力，供 OntologyAgent 调用。

工具列表（由 create_pl3_tools 统一创建）：

  1. lookup_symptom_sparql(symptom_name)
       在 RDF 三元组知识库中查找症状，返回关联疾病。
  2. lookup_disease_sparql(disease_name)
       查找疾病，返回必要症状、排除症状、物种约束。
  3. add_observation(symptom_name, severity, details)
       向 ConversationState 添加一条观测记录。
  4. set_pet_info(species, breed, age, sex)
       设置宠物基本信息。
  5. run_sparql_reasoning()
       基于当前 state 收集的信息，运行 SPARQL 前向链推理，返回诊断报告。
  6. explain_reasoning_chain(disease_name)
       解释某个疾病的推理链（suspected/excluded/diagnosed 三元组）。
  7. query_transitive_closure()
       查询疾病传播的传递闭包（Jena 前向链预计算独有能力）。
  8. get_case_summary()
       返回当前病例摘要。

依赖：
  - rdflib（本地推理降级）或 SPARQLWrapper（连接 Jena Fuseki）
  - P3 的 reasoner / local_reasoner / kb_builder 模块
  - 知识库文件：ontologyops/examples/P3/data/pet.ttl
"""

import os
import sys
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# P3 模块路径
_P3_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P3", "src"
)
if _P3_DIR not in sys.path:
    sys.path.insert(0, _P3_DIR)

_P3_DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P3", "data"
)

# 模块级缓存
_graph = None


def _get_graph():
    """懒加载 rdflib Graph（本地推理模式，无需 Docker/Fuseki）。"""
    global _graph
    if _graph is None:
        try:
            from local_reasoner import get_graph
            _graph = get_graph()
            logger.info("RDF 知识库已加载（rdflib 本地模式）")
        except Exception as e:
            logger.error(f"加载 RDF 知识库失败：{e}")
            raise
    return _graph


def create_pl3_tools(state, diagnose_fn, report_builder):
    """
    PL3 工具工厂，供 OntologyAgent 调用。

    Args:
        state: ConversationState 实例
        diagnose_fn: 诊断函数（PL3 中即 pl3_diagnose）
        report_builder: 报告构建函数（PL3 中即 build_pl3_report）

    Returns:
        list[Tool]: LangChain Tool 列表
    """

    # ============================================================
    # 工具 1: 查找症状（SPARQL/RDF 版）
    # ============================================================

    @tool
    def lookup_symptom_sparql(symptom_name: str) -> str:
        """
        在 RDF 三元组知识库中查找症状。
        返回症状关联的疾病列表（必要症状 / 排除症状）。

        示例:
            lookup_symptom_sparql("发热") → 返回发热关联的疾病
        """
        graph = _get_graph()

        from rdflib import URIRef
        from rdflib.namespace import RDFS

        PET_NS = "http://petbps.com/ontology/pet_disease#"
        symptom_uri = URIRef(PET_NS + symptom_name)

        # 查询以该症状为必要症状的疾病
        nec_diseases = []
        for disease, _, _ in graph.triples((None, URIRef(PET_NS + "necessary"), symptom_uri)):
            label = str(disease).split("#")[-1]
            for _, _, l in graph.triples((disease, RDFS.label, None)):
                label = str(l)
                break
            nec_diseases.append(f"{label}（必要症状）")

        # 查询以该症状为排除症状的疾病
        nos_diseases = []
        for disease, _, _ in graph.triples((None, URIRef(PET_NS + "nos"), symptom_uri)):
            label = str(disease).split("#")[-1]
            for _, _, l in graph.triples((disease, RDFS.label, None)):
                label = str(l)
                break
            nos_diseases.append(f"{label}（排除症状）")

        if nec_diseases or nos_diseases:
            lines = [f"症状「{symptom_name}」关联以下疾病："]
            for d in nec_diseases[:10]:
                lines.append(f"  - {d}")
            for d in nos_diseases[:10]:
                lines.append(f"  - {d}")
            return "\n".join(lines)

        return f"未找到症状「{symptom_name}」，请检查名称是否正确。"

    # ============================================================
    # 工具 2: 查找疾病（SPARQL/RDF 版）
    # ============================================================

    @tool
    def lookup_disease_sparql(disease_name: str) -> str:
        """
        在 RDF 三元组知识库中查找疾病。
        返回疾病的必要症状、排除症状、物种约束。

        示例:
            lookup_disease_sparql("猫瘟") → 返回 d001 的详细信息
        """
        graph = _get_graph()

        from rdflib import URIRef
        from rdflib.namespace import RDFS

        PET_NS = "http://petbps.com/ontology/pet_disease#"

        # 遍历所有疾病个体，匹配名称
        target = None
        target_label = ""
        for disease, _, label in graph.triples((None, RDFS.label, None)):
            label_str = str(label)
            if disease_name in label_str or label_str in disease_name:
                target = disease
                target_label = label_str
                break

        if target is None:
            return f"未找到疾病「{disease_name}」。"

        # 必要症状
        necessary = []
        for _, _, sym in graph.triples((target, URIRef(PET_NS + "necessary"), None)):
            sym_label = str(sym).split("#")[-1]
            for _, _, l in graph.triples((sym, RDFS.label, None)):
                sym_label = str(l)
                break
            necessary.append(sym_label)

        # 排除症状
        nos = []
        for _, _, sym in graph.triples((target, URIRef(PET_NS + "nos"), None)):
            sym_label = str(sym).split("#")[-1]
            for _, _, l in graph.triples((sym, RDFS.label, None)):
                sym_label = str(l)
                break
            nos.append(sym_label)

        # 物种
        species = ""
        for _, _, sp in graph.triples((target, URIRef(PET_NS + "has_species"), None)):
            species = str(sp).split("#")[-1]
            break

        lines = [f"疾病：{target_label}"]
        if necessary:
            lines.append(f"  必要症状：{', '.join(necessary)}")
        if nos:
            lines.append(f"  排除症状：{', '.join(nos)}")
        lines.append(f"  物种约束：{species or '通用'}")

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
    # 工具 5: 运行 SPARQL 推理
    # ============================================================

    @tool
    def run_sparql_reasoning() -> str:
        """
        基于当前病例信息，运行 Jena 前向链 + SPARQL 推理，返回诊断报告。

        该工具会：
          1. 将 state 中的信息转换为 P3 诊断函数所需的格式
          2. 断言症状三元组，执行前向链规则（suspected/excluded/diagnosed）
          3. SPARQL 查询推理结果
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

        与 PL2 的 CWA 解释不同：
        - PL2 基于 Prolog SLD 归结 + 封闭世界假设
        - PL3 基于 Jena 前向链 + RDF 三元组 + OWA

        示例:
            explain_reasoning_chain("猫瘟")
        """
        graph = _get_graph()

        from rdflib import URIRef
        from rdflib.namespace import RDFS

        PET_NS = "http://petbps.com/ontology/pet_disease#"

        # 查找疾病
        target = None
        target_label = ""
        for disease, _, label in graph.triples((None, RDFS.label, None)):
            label_str = str(label)
            if disease_name in label_str or label_str in disease_name:
                target = disease
                target_label = label_str
                break

        if target is None:
            return f"未找到疾病「{disease_name}」。"

        # 收集必要症状
        necessary = []
        for _, _, sym in graph.triples((target, URIRef(PET_NS + "necessary"), None)):
            sym_label = str(sym).split("#")[-1]
            for _, _, l in graph.triples((sym, RDFS.label, None)):
                sym_label = str(l)
                break
            necessary.append(sym_label)

        # 收集排除症状
        nos = []
        for _, _, sym in graph.triples((target, URIRef(PET_NS + "nos"), None)):
            sym_label = str(sym).split("#")[-1]
            for _, _, l in graph.triples((sym, RDFS.label, None)):
                sym_label = str(l)
                break
            nos.append(sym_label)

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
            f"### 疾病：{target_label}",
            "",
            f"**必要症状（共 {len(necessary)} 项）**：",
        ]
        for s in matched:
            lines.append(f"  ✅ {s}（已观测）")
        for s in unmatched:
            lines.append(f"  ❓ {s}（未观测）")

        if excluded_by:
            lines.append("")
            lines.append("**排除症状（已观测，可排除该病）**：")
            for n in excluded_by:
                lines.append(f"  ⚠️ {n}")

        # OWA 说明
        if unmatched:
            lines.append("")
            lines.append("**OWA 说明**：在开放世界假设下，未观测 ≠ 不存在。")
            lines.append("未观测的症状可能是尚未检查，因此该疾病仍可能为疑似。")

        if not necessary:
            lines.append("（该疾病未定义必要症状）")

        return "\n".join(lines)

    # ============================================================
    # 工具 7: 查询传递闭包（Jena 前向链独有能力）
    # ============================================================

    @tool
    def query_transitive_closure() -> str:
        """
        查询疾病传播的传递闭包。
        利用 Jena 前向链的 TransitiveProperty 预计算能力，
        展示疾病之间的传播关系链。

        这是 Jena/RDF 独有的能力 —— Prolog 的递归是查询时计算，
        Jena 的传递闭包是数据加载时预计算。

        示例:
            query_transitive_closure()
        """
        graph = _get_graph()

        from rdflib import URIRef
        from rdflib.namespace import RDFS

        PET_NS = "http://petbps.com/ontology/pet_disease#"
        contain_prop = URIRef(PET_NS + "contain")

        # 查询所有 contain 三元组（含传递闭包）
        lines = ["### 疾病传播闭包（Jena 前向链预计算）", ""]

        count = 0
        for a, _, b in graph.triples((None, contain_prop, None)):
            a_label = str(a).split("#")[-1]
            for _, _, l in graph.triples((a, RDFS.label, None)):
                a_label = str(l)
                break
            b_label = str(b).split("#")[-1]
            for _, _, l in graph.triples((b, RDFS.label, None)):
                b_label = str(l)
                break
            lines.append(f"  {a_label} → {b_label}")
            count += 1

        if count == 0:
            lines.append("  无传播关系数据。")
        else:
            lines.append("")
            lines.append(f"*共 {count} 条传播关系（含传递闭包）*")
            lines.append("*传递闭包由 Jena GenericRuleReasoner 预计算*")

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
        lookup_symptom_sparql,
        lookup_disease_sparql,
        add_observation,
        set_pet_info,
        run_sparql_reasoning,
        explain_reasoning_chain,
        query_transitive_closure,
        get_case_summary,
    ]

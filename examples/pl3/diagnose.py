"""
PL3 诊断函数 —— 包装 P3 的 Jena/SPARQL 前向链推理引擎。

P3 的 diagnose(case_dict) 返回：
  (results, excluded)
  results: List[Tuple[disease_name, confidence, is_confirmed, disease_uri]]
  excluded: List[disease_name]

PL3 的 diagnose_fn 需要返回 agent_core 能消费的格式：
  List[Dict[str, Any]]
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

# P3 模块路径
_P3_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P3", "src"
)
if _P3_DIR not in sys.path:
    sys.path.insert(0, _P3_DIR)

# 物种映射
_SPECIES_MAP = {
    "猫": "cat", "喵": "cat", "猫咪": "cat",
    "狗": "dog", "犬": "dog", "狗狗": "dog",
}


def pl3_diagnose(case_dict: dict) -> list:
    """
    PL3 诊断入口，供 OntologyAgent 调用。

    Args:
        case_dict: 由 ConversationState.to_case_dict() 生成，格式：
            {
                "subject_type": "猫",
                "observations": ["发热", "呕吐"],
                "breed": "英短",
                "age": 2,
            }

    Returns:
        list[dict]: 诊断结果列表，每项包含：
            {
                "disease": "猫瘟",
                "confidence": 1.0,
                "level": "确诊",
                "disease_id": "d001",
                "evidence": ["发热", "呕吐", "腹泻"],
                "missing": [],
            }
    """
    # 转换为 P3 期望的格式
    p3_case = _convert_case_dict(case_dict)

    # 优先使用 Fuseki，降级到本地 rdflib
    try:
        from reasoner import load_knowledge_base, diagnose as p3_diagnose
        load_knowledge_base()
        raw_results, excluded = p3_diagnose(p3_case)
    except Exception as e:
        logger.warning(f"Fuseki 不可用，降级为本地推理：{e}")
        from local_reasoner import diagnose_local
        raw_results, excluded = diagnose_local(p3_case)

    # 转换为 agent_core 标准格式
    return _format_results(raw_results, excluded, p3_case)


def _convert_case_dict(case_dict: dict) -> dict:
    """将 agent_core 的通用 case_dict 转换为 P3 期望的格式。"""
    p3_case = {}

    raw_type = case_dict.get("subject_type", "")
    p3_case["pet_type"] = _SPECIES_MAP.get(raw_type, raw_type)

    p3_case["symptoms"] = case_dict.get("observations", [])

    for key in ["breed", "age"]:
        if key in case_dict:
            p3_case[key] = case_dict[key]

    return p3_case


def _format_results(raw_results: list, excluded: list, case_dict: dict) -> list:
    """
    将 P3 的原始结果转换为 agent_core 标准格式。

    P3 返回:
      results: List[Tuple[disease_name, confidence, is_confirmed, disease_uri]]
      excluded: List[disease_name]
    """
    formatted = []
    symptoms = case_dict.get("symptoms", [])

    for disease_name, confidence, is_confirmed, disease_uri in raw_results:
        # 判断等级
        if is_confirmed:
            level = "确诊"
        elif confidence >= 0.50:
            level = "疑似"
        else:
            level = "排除"

        # 从 URI 提取 disease_id
        disease_id = str(disease_uri).split("#")[-1] if disease_uri else ""

        # 收集证据（匹配的症状）
        evidence = _collect_evidence(disease_uri, symptoms)

        # 收集缺失症状
        missing = _collect_missing(disease_uri, symptoms)

        formatted.append({
            "disease": disease_name,
            "confidence": round(confidence, 3),
            "level": level,
            "disease_id": disease_id,
            "evidence": evidence,
            "missing": missing,
        })

    # 添加被排除的疾病
    for ex_name in excluded:
        formatted.append({
            "disease": ex_name,
            "confidence": 0.0,
            "level": "排除",
            "disease_id": "",
            "evidence": [],
            "missing": [],
        })

    return formatted


def _collect_evidence(disease_uri, symptoms: list) -> list:
    """收集支持该疾病诊断的证据（已匹配的症状）。"""
    if not disease_uri:
        return []

    try:
        from rdflib import URIRef
        from rdflib.namespace import RDFS

        PET_NS = "http://petbps.com/ontology/pet_disease#"
        from local_reasoner import get_graph
        graph = get_graph()

        evidence = []
        for _, _, sym in graph.triples((URIRef(str(disease_uri)), URIRef(PET_NS + "necessary"), None)):
            sym_label = str(sym).split("#")[-1]
            for _, _, l in graph.triples((sym, RDFS.label, None)):
                sym_label = str(l)
                break
            if any(sym_label in s or s in sym_label for s in symptoms):
                evidence.append(sym_label)

        return evidence
    except Exception:
        return []


def _collect_missing(disease_uri, symptoms: list) -> list:
    """收集该疾病未匹配到的必要症状。"""
    if not disease_uri:
        return []

    try:
        from rdflib import URIRef
        from rdflib.namespace import RDFS

        PET_NS = "http://petbps.com/ontology/pet_disease#"
        from local_reasoner import get_graph
        graph = get_graph()

        missing = []
        for _, _, sym in graph.triples((URIRef(str(disease_uri)), URIRef(PET_NS + "necessary"), None)):
            sym_label = str(sym).split("#")[-1]
            for _, _, l in graph.triples((sym, RDFS.label, None)):
                sym_label = str(l)
                break
            if not any(sym_label in s or s in sym_label for s in symptoms):
                missing.append(sym_label)

        return missing
    except Exception:
        return []


def _fallback_diagnose(case_dict: dict) -> tuple:
    """降级诊断：使用 rdflib 本地推理。"""
    from local_reasoner import diagnose_local
    return diagnose_local(case_dict)

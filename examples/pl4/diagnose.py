"""
PL4 诊断函数 —— 包装 P4 的 Mamdani 模糊推理引擎。

P4 的 diagnose(kb, case_dict) 返回：
  List[Tuple[disease_name, confidence, fuzzy_level, disease_id]]

PL4 的 diagnose_fn 需要返回 agent_core 能消费的格式：
  List[Dict[str, Any]]
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

# P4 模块路径
_P4_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P4", "src"
)
if _P4_DIR not in sys.path:
    sys.path.insert(0, _P4_DIR)

# 物种映射
_SPECIES_MAP = {
    "猫": "cat", "喵": "cat", "猫咪": "cat",
    "狗": "dog", "犬": "dog", "狗狗": "dog",
}


def pl4_diagnose(case_dict: dict) -> list:
    """
    PL4 诊断入口，供 OntologyAgent 调用。

    Args:
        case_dict: 由 ConversationState.to_case_dict() 生成，格式：
            {
                "subject_type": "猫",
                "observations": ["发热", "呕吐"],
                "breed": "英短",
                "age": 2,
                "symptom_details": {
                    "发热": {"value": 39.5},
                    "呕吐": {"frequency": "多次"},
                }
            }

    Returns:
        list[dict]: 诊断结果列表，每项包含：
            {
                "disease": "猫瘟",
                "confidence": 0.85,
                "level": "高",
                "disease_id": "D001",
                "evidence": ["发热", "呕吐", "腹泻"],
                "missing": [],
            }
    """
    # 转换为 P4 期望的格式
    p4_case = _convert_case_dict(case_dict)

    # 加载知识库并执行推理
    from reasoner import load_knowledge_base, diagnose as p4_diagnose

    kb = load_knowledge_base()
    raw_results = p4_diagnose(kb, p4_case)

    # 转换为 agent_core 标准格式
    return _format_results(raw_results, p4_case, kb)


def _convert_case_dict(case_dict: dict) -> dict:
    """
    将 agent_core 的通用 case_dict 转换为 P4 期望的格式。

    P4 特有：需要 symptom_details（症状严重度详情）。
    ConversationState 的 observations 中包含 details 字段，
    需要提取为 P4 期望的 symptom_details 格式。
    """
    p4_case = {}

    raw_type = case_dict.get("subject_type", "")
    p4_case["pet_type"] = _SPECIES_MAP.get(raw_type, raw_type)

    p4_case["symptoms"] = case_dict.get("observations", [])

    for key in ["breed", "age"]:
        if key in case_dict:
            p4_case[key] = case_dict[key]

    # 从 observations 的 details 构建 symptom_details
    # ConversationState.to_case_dict() 可能不包含 details，
    # 所以从原始 observations 中提取
    p4_case["symptom_details"] = case_dict.get("symptom_details", {})

    return p4_case


def _format_results(raw_results: list, case_dict: dict, kb: dict) -> list:
    """
    将 P4 的原始结果转换为 agent_core 标准格式。

    P4 返回:
      List[Tuple[disease_name, confidence, fuzzy_level, disease_id]]

    agent_core 期望:
      List[Dict]
    """
    formatted = []
    symptoms = case_dict.get("symptoms", [])

    for disease_name, confidence, fuzzy_level, disease_id in raw_results:
        # 收集证据（匹配的必要症状）
        evidence = _collect_evidence(disease_id, symptoms, kb)

        # 收集缺失症状
        missing = _collect_missing(disease_id, symptoms, kb)

        formatted.append({
            "disease": disease_name,
            "confidence": round(confidence, 3),
            "level": fuzzy_level,  # 高/中/低（模糊等级）
            "disease_id": disease_id,
            "evidence": evidence,
            "missing": missing,
        })

    return formatted


def _collect_evidence(disease_id: str, symptoms: list, kb: dict) -> list:
    """收集支持该疾病诊断的证据（已匹配的必要症状）。"""
    for disease in kb["diseases"]:
        if disease["id"] == disease_id:
            necessary = disease.get("necessary_symptoms", [])
            return [s for s in necessary if any(s in sym or sym in s for sym in symptoms)]
    return []


def _collect_missing(disease_id: str, symptoms: list, kb: dict) -> list:
    """收集该疾病未匹配到的必要症状。"""
    for disease in kb["diseases"]:
        if disease["id"] == disease_id:
            necessary = disease.get("necessary_symptoms", [])
            return [s for s in necessary if not any(s in sym or sym in s for sym in symptoms)]
    return []

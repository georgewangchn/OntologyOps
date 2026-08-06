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

    # 加载知识库
    kb = _load_kb()

    # 尝试调用 P4 的模糊推理引擎
    try:
        from reasoner import diagnose as p4_diagnose
        raw_results = p4_diagnose(kb, p4_case)
    except Exception as e:
        logger.error(f"P4 模糊推理引擎执行失败：{e}")
        raw_results = _fallback_diagnose(kb, p4_case)

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


def _load_kb():
    """懒加载 P4 知识库，带缓存。"""
    global _KB_CACHE
    if _KB_CACHE is not None:
        return _KB_CACHE
    try:
        from reasoner import load_knowledge_base
        _KB_CACHE = load_knowledge_base()
    except Exception as e:
        logger.error(f"加载 P4 知识库失败：{e}")
        _KB_CACHE = _load_kb_fallback()
    return _KB_CACHE


_KB_CACHE = None


def _load_kb_fallback() -> dict:
    """
    当 reasoner.load_knowledge_base 失败时（如 scikit-fuzzy 未安装），
    直接从 JSON 文件加载知识库结构（不含模糊控制器）。
    """
    import json
    kb_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "P4", "data", "fuzzy_kb.json"
    )
    with open(kb_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fallback_diagnose(kb: dict, case_dict: dict) -> list:
    """
    降级诊断：当 P4 的 Mamdani 模糊推理引擎失败时，
    基于知识库中的疾病定义和症状基线严重度进行简化模糊匹配。

    代替完整的 Mamdani 推理流程，使用以下简化策略：
    1. 覆盖率 = matched_necessary / total_necessary
    2. 强度 = 平均症状基线严重度（0-1）
    3. 排除度 = 1.0 if 存在排除症状 else 0.0
    4. 置信度 = coverage * 0.5 + intensity * 0.3 + (1 - exclusion) * 0.2
    """
    logger.warning("使用降级诊断策略（简化模糊匹配）")

    pet_type = case_dict.get("pet_type", "pet")
    symptoms = case_dict.get("symptoms", [])
    baselines = kb.get("symptom_baselines", {})

    results = []

    for disease in kb.get("diseases", []):
        did = disease["id"]
        dname = disease["name"]
        species = disease.get("species", "pet")

        # 物种过滤
        if species != "pet" and species != pet_type:
            continue

        necessary = disease.get("necessary_symptoms", [])
        if not necessary:
            continue

        # 覆盖率
        matched = 0
        for nec in necessary:
            if any(nec in s or s in nec for s in symptoms):
                matched += 1
        coverage = matched / len(necessary)

        if coverage == 0:
            continue

        # 强度（平均基线严重度）
        intensities = []
        for nec in necessary:
            if any(nec in s or s in nec for s in symptoms):
                intensities.append(baselines.get(nec, 0.5))
        intensity = sum(intensities) / len(intensities) if intensities else 0.5

        # 排除度
        exclusion_symptoms = disease.get("exclusion_symptoms", [])
        has_exclusion = False
        for exs in exclusion_symptoms:
            if any(exs in s or s in exs for s in symptoms):
                has_exclusion = True
                break
        exclusion = 1.0 if has_exclusion else 0.0

        # 简化置信度计算
        confidence = coverage * 0.5 + intensity * 0.3 + (1 - exclusion) * 0.2
        confidence = min(0.99, confidence)

        # 模糊等级
        if confidence >= 0.65:
            level = "高"
        elif confidence >= 0.35:
            level = "中"
        else:
            level = "低"

        results.append((dname, confidence, level, did))

    # 按置信度降序
    results.sort(key=lambda x: -x[1])
    return results


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

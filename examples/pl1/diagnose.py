"""
PL1 诊断函数 —— 包装 P1 的 OWL 推理引擎。

P1 的 diagnose(onto, case_dict) 返回：
  List[Tuple[owlready2.ThingClass, float]]
  e.g. [(猫瘟, 0.99), (猫肠炎, 0.65), ...]

PL1 的 diagnose_fn 需要返回 agent_core 能消费的格式：
  List[Dict[str, Any]]
  e.g. [{"disease": "猫瘟", "confidence": 0.99, "level": "确诊", ...}, ...]
"""

import os
import sys
import logging

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

# 模块级缓存
_ONTO = None


def _get_onto():
    global _ONTO
    if _ONTO is None:
        try:
            from reasoner import load_ontology
            _ONTO = load_ontology(_ONTO_PATH)
            logger.info(f"OWL 本体已加载（diagnose 模块）")
        except Exception as e:
            logger.error(f"加载 OWL 本体失败：{e}")
            raise
    return _ONTO


def _run_hermit_if_needed(onto):
    """按需运行 HermiT 推理。"""
    try:
        from reasoner import run_reasoner
        run_reasoner(onto, reasoner="hermit")
        logger.info("HermiT 推理完成")
    except Exception as e:
        logger.warning(f"HermiT 推理失败（将使用规则推理）：{e}")


def pl1_diagnose(case_dict: dict) -> list:
    """
    PL1 诊断入口，供 OntologyAgent 调用。

    Args:
        case_dict: 由 ConversationState.to_case_dict() 生成的字典，格式：
            {
                "subject_type": "猫",       # 原 pet_type
                "observations": ["发热", "呕吐"],
                "breed": "英短",            # 可选
                "age": 2,                    # 可选
                "observation_details": {...}   # 可选
            }

    Returns:
        list[dict]: 诊断结果列表，每项包含：
            {
                "disease": "猫瘟",
                "confidence": 0.99,
                "level": "确诊",
                "disease_id": "D001",
                "evidence": ["发热", "呕吐", "腹泻"],
                "missing": [],
            }
    """
    onto = _get_onto()

    # 将通用 case_dict 转换为 P1 期望的格式
    p1_case = _convert_case_dict(case_dict)

    # 运行 HermiT 推理
    _run_hermit_if_needed(onto)

    # 调用 P1 的诊断函数
    from diagnosis import diagnose as p1_diagnose

    try:
        raw_results = p1_diagnose(onto, p1_case)
    except Exception as e:
        logger.error(f"P1 诊断函数执行失败：{e}")
        # 降级：手动计算匹配度
        raw_results = _fallback_diagnose(onto, p1_case)

    # 转换为 agent_core 标准格式
    return _format_results(onto, raw_results, p1_case)


_SPECIES_MAP = {
    "猫": "cat", "喵": "cat", "猫咪": "cat",
    "狗": "dog", "犬": "dog", "狗狗": "dog",
}


def _convert_case_dict(case_dict: dict) -> dict:
    """
    将 agent_core 的通用 case_dict 转换为 P1 期望的格式。

    agent_core 使用通用术语（subject_type / observations），
    P1 使用兽医术语（pet_type / symptoms）并期望英文物种名。
    """
    p1_case = {}

    # subject_type → pet_type，中文映射为英文
    raw_type = case_dict.get("subject_type", "")
    p1_case["pet_type"] = _SPECIES_MAP.get(raw_type, raw_type)

    # observations → symptoms
    p1_case["symptoms"] = case_dict.get("observations", [])

    # 透传可选字段
    for key in ["breed", "age"]:
        if key in case_dict:
            p1_case[key] = case_dict[key]

    return p1_case


def _format_results(onto, raw_results: list, case_dict: dict) -> list:
    """
    将 P1 的原始结果（List[Tuple[class, confidence]]）
    转换为 agent_core 标准格式（List[Dict]）。
    """
    formatted = []

    for disease_cls, confidence in raw_results:
        # 获取疾病名称
        disease_name = (
            disease_cls.label[0]
            if hasattr(disease_cls, "label") and disease_cls.label
            else disease_cls.name
        )

        # 获取疾病 ID
        disease_id = disease_cls.name  # e.g. "D001"

        # 判断等级
        level = _determine_level(confidence)

        # 收集证据（匹配的必要症状）
        evidence = _collect_evidence(onto, disease_cls, case_dict)

        # 收集缺失症状
        missing = _collect_missing(onto, disease_cls, case_dict)

        formatted.append({
            "disease": disease_name,
            "confidence": round(confidence, 3),
            "level": level,
            "disease_id": disease_id,
            "evidence": evidence,
            "missing": missing,
        })

    return formatted


def _determine_level(confidence: float) -> str:
    """根据置信度判断等级。"""
    if confidence >= 0.85:
        return "确诊"
    elif confidence >= 0.50:
        return "疑似"
    else:
        return "排除"


def _collect_evidence(onto, disease_cls, case_dict: dict) -> list:
    """收集支持该疾病诊断的证据（已匹配的症状）。"""
    evidence = []
    symptoms = case_dict.get("symptoms", [])

    # 检查该疾病的必要症状是否有出现在病例中
    if hasattr(disease_cls, "is_a"):
        for res in disease_cls.is_a:
            if hasattr(res, "property") and res.property is onto.necessary:
                s_name = res.value.label[0] if res.value.label else res.value.name
                # 模糊匹配
                if any(s_name in s or s in s_name for s in symptoms):
                    evidence.append(s_name)

    return evidence


def _collect_missing(onto, disease_cls, case_dict: dict) -> list:
    """收集该疾病未匹配到的必要症状。"""
    missing = []
    symptoms = case_dict.get("symptoms", [])

    if hasattr(disease_cls, "is_a"):
        for res in disease_cls.is_a:
            if hasattr(res, "property") and res.property is onto.necessary:
                s_name = res.value.label[0] if res.value.label else res.value.name
                if not any(s_name in s or s in s_name for s in symptoms):
                    missing.append(s_name)

    return missing


def _fallback_diagnose(onto, case_dict: dict) -> list:
    """
    降级诊断：当 P1 的 diagnose 函数失败时，
    使用简单的必要症状匹配计算置信度。
    """
    logger.warning("使用降级诊断策略（必要症状匹配）")
    pet_type = case_dict.get("pet_type", "")
    symptoms = case_dict.get("symptoms", [])

    results = []

    for d in onto.search(type=onto.疾病):
        # 物种过滤
        d_species = []
        for res in d.is_a:
            if hasattr(res, "property") and res.property is onto.hasSpecies:
                d_species.append(res.value.name)

        if d_species and pet_type:
            species_match = any(
                pet_type in s or s in pet_type for s in d_species
            )
            if not species_match:
                continue

        # 计算必要症状匹配度
        necessary = []
        if hasattr(d, "is_a"):
            for res in d.is_a:
                if hasattr(res, "property") and res.property is onto.necessary:
                    necessary.append(res.value)

        if not necessary:
            continue

        matched = 0
        for nec in necessary:
            n_name = nec.label[0] if nec.label else nec.name
            if any(n_name in s or s in n_name for s in symptoms):
                matched += 1

        confidence = min(0.99, matched / len(necessary) + 0.1)
        results.append((d, confidence))

    # 按置信度排序
    results.sort(key=lambda x: x[1], reverse=True)
    return results

"""
PL2 诊断函数 —— 包装 P2 的 Prolog 推理引擎。

P2 的 diagnose(prolog, case_dict) 返回：
  (results, excluded)
  results: List[Tuple[disease_name, confidence, is_confirmed, disease_id]]
  excluded: List[disease_name]

PL2 的 diagnose_fn 需要返回 agent_core 能消费的格式：
  List[Dict[str, Any]]
  e.g. [{"disease": "猫瘟", "confidence": 0.99, "level": "确诊", ...}, ...]
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

# P2 模块路径
_P2_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P2", "src"
)
if _P2_DIR not in sys.path:
    sys.path.insert(0, _P2_DIR)

_KB_PL = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P2", "data", "pet_kb.pl"
)
_RULES_PL = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P2", "src", "rules.pl"
)

# 模块级缓存
_PROLOG = None


def _get_prolog():
    global _PROLOG
    if _PROLOG is None:
        try:
            from reasoner import load_knowledge_base
            _PROLOG = load_knowledge_base()
            logger.info("Prolog 知识库已加载（diagnose 模块）")
        except Exception as e:
            logger.error(f"加载 Prolog 知识库失败：{e}")
            raise
    return _PROLOG


def pl2_diagnose(case_dict: dict) -> list:
    """
    PL2 诊断入口，供 OntologyAgent 调用。

    Args:
        case_dict: 由 ConversationState.to_case_dict() 生成，格式：
            {
                "subject_type": "猫",
                "observations": ["发热", "呕吐"],
                "breed": "英短",          # 可选
                "age": 2,                  # 可选
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
    prolog = _get_prolog()

    # 将通用 case_dict 转换为 P2 期望的格式
    p2_case = _convert_case_dict(case_dict)

    # 调用 P2 的诊断函数
    from reasoner import diagnose as p2_diagnose

    try:
        raw_results, excluded = p2_diagnose(prolog, p2_case)
    except Exception as e:
        logger.error(f"P2 诊断函数执行失败：{e}")
        # 降级：手动查询
        raw_results, excluded = _fallback_diagnose(prolog, p2_case)

    # 转换为 agent_core 标准格式
    return _format_results(prolog, raw_results, excluded, p2_case)


_SPECIES_MAP = {
    "猫": "cat", "喵": "cat", "猫咪": "cat",
    "狗": "dog", "犬": "dog", "狗狗": "dog",
}


def _convert_case_dict(case_dict: dict) -> dict:
    """
    将 agent_core 的通用 case_dict 转换为 P2 期望的格式。

    agent_core 使用通用术语（subject_type / observations），
    P2 使用兽医术语（pet_type / symptoms）并期望英文物种名。
    """
    p2_case = {}

    raw_type = case_dict.get("subject_type", "")
    p2_case["pet_type"] = _SPECIES_MAP.get(raw_type, raw_type)

    p2_case["symptoms"] = case_dict.get("observations", [])

    for key in ["breed", "age"]:
        if key in case_dict:
            p2_case[key] = case_dict[key]

    return p2_case


def _format_results(prolog, raw_results: list, excluded: list, case_dict: dict) -> list:
    """
    将 P2 的原始结果转换为 agent_core 标准格式。

    P2 返回:
      results: List[Tuple[disease_name, confidence, is_confirmed, disease_id]]
      excluded: List[disease_name]

    agent_core 期望:
      List[Dict]
    """
    formatted = []

    for disease_name, confidence, is_confirmed, disease_id in raw_results:
        # 判断等级
        if is_confirmed:
            level = "确诊"
        elif confidence >= 0.50:
            level = "疑似"
        else:
            level = "排除"

        # 收集证据（匹配的必要症状）
        evidence = _collect_evidence(prolog, disease_id, case_dict)

        # 收集缺失症状
        missing = _collect_missing(prolog, disease_id, case_dict)

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


def _collect_evidence(prolog, disease_id: str, case_dict: dict) -> list:
    """收集支持该疾病诊断的证据（已匹配的症状）。"""
    evidence = []
    symptoms = case_dict.get("symptoms", [])

    nec_results = list(prolog.query(f"necessary({disease_id}, S)"))
    for r in nec_results:
        s_name = str(r["S"])
        if any(s_name in s or s in s_name for s in symptoms):
            evidence.append(s_name)

    return evidence


def _collect_missing(prolog, disease_id: str, case_dict: dict) -> list:
    """收集该疾病未匹配到的必要症状。"""
    missing = []
    symptoms = case_dict.get("symptoms", [])

    nec_results = list(prolog.query(f"necessary({disease_id}, S)"))
    for r in nec_results:
        s_name = str(r["S"])
        if not any(s_name in s or s in s_name for s in symptoms):
            missing.append(s_name)

    return missing


def _fallback_diagnose(prolog, case_dict: dict) -> tuple:
    """
    降级诊断：当 P2 的 diagnose 函数失败时，
    使用简单的 Prolog 查询手动计算匹配度。
    """
    logger.warning("使用降级诊断策略（手动 Prolog 查询）")
    pet_type = case_dict.get("pet_type", "pet")
    symptoms = case_dict.get("symptoms", [])

    results = []
    all_diseases = list(prolog.query("disease(DID, Name, Species)"))

    for d in all_diseases:
        did = d["DID"]
        dname = str(d["Name"])
        species = str(d["Species"])

        # 物种过滤
        if species != "pet" and species != pet_type:
            continue

        # 计算必要症状匹配度
        nec_results = list(prolog.query(f"necessary({did}, S)"))
        necessary = [str(r["S"]) for r in nec_results]

        if not necessary:
            continue

        matched = 0
        for nec in necessary:
            if any(nec in s or s in nec for s in symptoms):
                matched += 1

        confidence = matched / len(necessary)
        is_confirmed = (matched == len(necessary))

        # 检查排除症状
        nos_results = list(prolog.query(f"nos({did}, S)"))
        excluded = False
        for r in nos_results:
            n_name = str(r["S"])
            if any(n_name in s or s in n_name for s in symptoms):
                excluded = True
                break

        if not excluded and confidence > 0:
            results.append((dname, confidence, is_confirmed, did))

    # 排序：确诊优先，然后按置信度降序
    results.sort(key=lambda x: (not x[2], -x[1]))
    return results, []

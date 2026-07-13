"""
PL6 诊断函数 —— 包装 P6 的多范式分层仲裁引擎。
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

_P6_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P6", "src"
)
if _P6_DIR not in sys.path:
    sys.path.insert(0, _P6_DIR)

_SPECIES_MAP = {
    "猫": "cat", "喵": "cat", "猫咪": "cat",
    "狗": "dog", "犬": "dog", "狗狗": "dog",
}


def pl6_diagnose(case_dict: dict) -> list:
    """PL6 诊断入口，供 OntologyAgent 调用。"""
    p6_case = _convert_case_dict(case_dict)

    try:
        from reasoner import diagnose as p6_diagnose
        results = p6_diagnose(p6_case)
    except Exception as e:
        logger.error(f"P6 仲裁推理引擎执行失败：{e}")
        results = _fallback_diagnose(p6_case)

    return results


def _convert_case_dict(case_dict: dict) -> dict:
    """将 agent_core 的通用 case_dict 转换为 P6 期望的格式。"""
    p6_case = {}
    raw_type = case_dict.get("subject_type", "")
    p6_case["pet_type"] = _SPECIES_MAP.get(raw_type, raw_type)
    p6_case["symptoms"] = case_dict.get("observations", [])
    for key in ["breed", "age"]:
        if key in case_dict:
            p6_case[key] = case_dict[key]
    return p6_case


def _fallback_diagnose(case_dict: dict) -> list:
    """
    降级诊断：当 P6 仲裁引擎失败时，仅使用 P5 贝叶斯推理。
    """
    logger.warning("使用降级诊断策略（仅贝叶斯推理）")

    p5_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "P5", "src")
    if p5_dir not in sys.path:
        sys.path.insert(0, p5_dir)

    try:
        from reasoner import load_knowledge_base, diagnose as p5_diagnose
        kb = load_knowledge_base()
        raw_results = p5_diagnose(kb, case_dict)

        results = []
        for name, conf, level, did in raw_results:
            results.append({
                "disease": name,
                "confidence": round(conf, 4),
                "level": level,
                "disease_id": did,
                "evidence": [],
                "missing": [],
                "engine_results": {"P5": {"confidence": conf, "level": level}},
                "conflict": False,
                "arbitration_note": "降级模式：仅贝叶斯推理可用",
            })
        return results
    except Exception as e:
        logger.error(f"降级诊断也失败：{e}")
        return []


def _format_results(raw_results: list, case_dict: dict) -> list:
    """P6 的 diagnose 已经返回标准格式，直接透传。"""
    return raw_results

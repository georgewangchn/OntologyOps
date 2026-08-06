"""
PL5 诊断函数 —— 包装 P5 的朴素贝叶斯推理引擎。

P5 的 diagnose(kb, case_dict) 返回：
  List[Tuple[disease_name, confidence, probability_level, disease_id]]

PL5 的 diagnose_fn 需要返回 agent_core 能消费的格式：
  List[Dict[str, Any]]
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

_P5_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P5", "src"
)
if _P5_DIR not in sys.path:
    sys.path.insert(0, _P5_DIR)

_SPECIES_MAP = {
    "猫": "cat", "喵": "cat", "猫咪": "cat",
    "狗": "dog", "犬": "dog", "狗狗": "dog",
}

_KB_CACHE = None


def pl5_diagnose(case_dict: dict) -> list:
    """PL5 诊断入口，供 OntologyAgent 调用。"""
    p5_case = _convert_case_dict(case_dict)
    kb = _load_kb()

    try:
        from reasoner import diagnose as p5_diagnose
        raw_results = p5_diagnose(kb, p5_case)
    except Exception as e:
        logger.error(f"P5 贝叶斯推理引擎执行失败：{e}")
        raw_results = _fallback_diagnose(kb, p5_case)

    return _format_results(raw_results, p5_case, kb)


def _convert_case_dict(case_dict: dict) -> dict:
    """将 agent_core 的通用 case_dict 转换为 P5 期望的格式。"""
    p5_case = {}
    raw_type = case_dict.get("subject_type", "")
    p5_case["pet_type"] = _SPECIES_MAP.get(raw_type, raw_type)
    p5_case["symptoms"] = case_dict.get("observations", [])
    for key in ["breed", "age"]:
        if key in case_dict:
            p5_case[key] = case_dict[key]
    return p5_case


def _load_kb():
    """懒加载 P5 知识库，带缓存。"""
    global _KB_CACHE
    if _KB_CACHE is not None:
        return _KB_CACHE
    try:
        from reasoner import load_knowledge_base
        _KB_CACHE = load_knowledge_base()
    except Exception as e:
        logger.error(f"加载 P5 知识库失败：{e}")
        _KB_CACHE = _load_kb_fallback()
    return _KB_CACHE


def _load_kb_fallback() -> dict:
    """当 reasoner.load_knowledge_base 失败时，直接从 JSON 文件加载。"""
    import json
    kb_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "P5", "data", "bayesian_kb.json"
    )
    with open(kb_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fallback_diagnose(kb: dict, case_dict: dict) -> list:
    """
    降级诊断：当 P5 的贝叶斯推理引擎失败时，
    手动实现朴素贝叶斯推理。
    """
    logger.warning("使用降级诊断策略（手动贝叶斯推理）")

    pet_type = case_dict.get("pet_type", "pet")
    symptoms = case_dict.get("symptoms", [])

    raw_posteriors = []
    for disease in kb.get("diseases", []):
        species = disease.get("species", "pet")
        if species != "pet" and species != pet_type:
            continue

        prior = disease.get("prior", 0.05)
        cpt = disease.get("cpt", {})
        if not cpt:
            continue

        likelihood = prior
        for symptom, probs in cpt.items():
            p_present = probs["present"]
            if symptom in symptoms:
                likelihood *= p_present
            else:
                likelihood *= (1.0 - p_present)

        if likelihood > 0:
            raw_posteriors.append((disease, likelihood))

    total = sum(p for _, p in raw_posteriors)
    if total == 0:
        return []

    results = []
    for disease, posterior in raw_posteriors:
        normalized = posterior / total
        if normalized >= 0.50:
            level = "高概率"
        elif normalized >= 0.15:
            level = "中概率"
        else:
            level = "低概率"
        results.append((disease["name"], normalized, level, disease["id"]))

    results.sort(key=lambda x: -x[1])
    return results


def _format_results(raw_results: list, case_dict: dict, kb: dict) -> list:
    """将 P5 的原始结果转换为 agent_core 标准格式。"""
    formatted = []
    symptoms = case_dict.get("symptoms", [])

    for disease_name, confidence, level, disease_id in raw_results:
        evidence = _collect_evidence(disease_id, symptoms, kb)
        missing = _collect_missing(disease_id, symptoms, kb)

        formatted.append({
            "disease": disease_name,
            "confidence": round(confidence, 4),
            "level": level,
            "disease_id": disease_id,
            "evidence": evidence,
            "missing": missing,
        })

    return formatted


def _collect_evidence(disease_id: str, symptoms: list, kb: dict) -> list:
    """收集支持该疾病诊断的证据（已匹配的必要症状）。"""
    for disease in kb.get("diseases", []):
        if disease["id"] == disease_id:
            necessary = disease.get("necessary_symptoms", [])
            return [s for s in necessary if any(s in sym or sym in s for sym in symptoms)]
    return []


def _collect_missing(disease_id: str, symptoms: list, kb: dict) -> list:
    """收集该疾病未匹配到的必要症状。"""
    for disease in kb.get("diseases", []):
        if disease["id"] == disease_id:
            necessary = disease.get("necessary_symptoms", [])
            return [s for s in necessary if not any(s in sym or sym in s for sym in symptoms)]
    return []

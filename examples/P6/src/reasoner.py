# -*- coding: utf-8 -*-
"""
多范式分层仲裁推理引擎 —— P1-P5 的统一调度与冲突仲裁

对比 P1-P5：每个引擎独立推理，输出单一范式的结果
P6：分层架构，P1-P3 确定性推理先行 → P4 模糊量化 → P5 概率校准 → 仲裁器裁决

分层仲裁策略：
  第一层（确定性推理）：P1(OWL) + P2(Prolog) + P3(SPARQL)
    - 输出二元结果（确诊/排除/疑似）
    - 如果 P1/P2/P3 一致"确诊"→ 高置信度直接输出
    - 如果 P1/P2/P3 一致"排除"→ 直接排除
    - 如果 P1/P2/P3 冲突 → 标记冲突，进入第二层

  第二层（模糊量化）：P4(Mamdani)
    - 输出连续置信度（0-1）
    - 对第一层"疑似"的疾病做模糊量化
    - 置信度 > 0.7 → 升级为"高度疑似"
    - 置信度 < 0.3 → 降级为"低置信度"

  第三层（概率校准）：P5(贝叶斯)
    - 输出后验概率
    - 对所有候选疾病做概率校准
    - 后验概率作为最终排序依据

  仲裁器：综合三层结果做最终裁决
    - 确定性一致 → 直接采纳
    - 确定性冲突 → 以概率排序为准，标注冲突
    - 模糊与概率一致 → 加权融合
    - 模糊与概率冲突 → 概率优先，标注冲突
"""

import os
import sys
import json
import logging

logger = logging.getLogger(__name__)

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
CONFIG_JSON = os.path.join(LOCAL_DATA_DIR, "arbiter_config.json")

# 各引擎 src 路径
_ENGINES = {
    "P1": os.path.join(os.path.dirname(__file__), "../../P1/src"),
    "P2": os.path.join(os.path.dirname(__file__), "../../P2/src"),
    "P3": os.path.join(os.path.dirname(__file__), "../../P3/src"),
    "P4": os.path.join(os.path.dirname(__file__), "../../P4/src"),
    "P5": os.path.join(os.path.dirname(__file__), "../../P5/src"),
}

for path in _ENGINES.values():
    if path not in sys.path:
        sys.path.insert(0, path)


def diagnose(case_dict):
    """
    多范式分层仲裁诊断

    :param case_dict: {"pet_type": "cat", "symptoms": ["发热", "呕吐", "腹泻"]}
    :return: List[Dict] — 仲裁后的诊断结果，每项包含：
        {
            "disease": "猫瘟",
            "confidence": 0.92,
            "level": "确诊（多引擎一致）",
            "disease_id": "D001",
            "evidence": [...],
            "missing": [...],
            "engine_results": {
                "P1": {"confidence": 1.0, "level": "确诊"},
                "P2": {"confidence": 1.0, "level": "确诊"},
                "P3": {"confidence": 1.0, "level": "确诊"},
                "P4": {"confidence": 0.86, "level": "高"},
                "P5": {"confidence": 0.91, "level": "高概率"},
            },
            "conflict": False,
            "arbitration_note": "三层一致：确定性推理确诊 + 模糊量化高 + 概率校准高概率"
        }
    """
    # ── 第一层：确定性推理（P1/P2/P3）──
    layer1_results = _run_deterministic_layer(case_dict)

    # ── 第二层：模糊量化（P4）──
    layer2_results = _run_fuzzy_layer(case_dict)

    # ── 第三层：概率校准（P5）──
    layer3_results = _run_bayesian_layer(case_dict)

    # ── 仲裁器：综合三层结果 ──
    return _arbitrate(layer1_results, layer2_results, layer3_results, case_dict)


def _run_deterministic_layer(case_dict):
    """第一层：P1 + P2 + P3 确定性推理"""
    results = {}

    # P1: OWL/HermiT
    try:
        from reasoner import load_ontology, run_reasoner
        from diagnosis import diagnose as p1_diagnose
        onto = load_ontology()
        run_reasoner(onto)
        raw = p1_diagnose(onto, case_dict)
        results["P1"] = _normalize_p1(raw)
    except Exception as e:
        logger.warning(f"P1 推理失败（降级跳过）：{e}")
        results["P1"] = None

    # P2: Prolog
    try:
        from reasoner import load_knowledge_base as p2_load, diagnose as p2_diagnose
        prolog = p2_load()
        raw, excluded = p2_diagnose(prolog, case_dict)
        results["P2"] = _normalize_p2(raw, excluded)
    except Exception as e:
        logger.warning(f"P2 推理失败（降级跳过）：{e}")
        results["P2"] = None

    # P3: Jena/SPARQL (降级到 rdflib)
    try:
        from local_reasoner import diagnose_local as p3_diagnose
        raw, excluded = p3_diagnose(case_dict)
        results["P3"] = _normalize_p3(raw, excluded)
    except Exception as e:
        logger.warning(f"P3 推理失败（降级跳过）：{e}")
        results["P3"] = None

    return results


def _run_fuzzy_layer(case_dict):
    """第二层：P4 模糊量化"""
    try:
        from reasoner import load_knowledge_base as p4_load, diagnose as p4_diagnose
        kb = p4_load()
        raw = p4_diagnose(kb, case_dict)
        return _normalize_p4(raw)
    except Exception as e:
        logger.warning(f"P4 推理失败（降级跳过）：{e}")
        return {}


def _run_bayesian_layer(case_dict):
    """第三层：P5 贝叶斯概率校准"""
    try:
        from reasoner import load_knowledge_base as p5_load, diagnose as p5_diagnose
        kb = p5_load()
        raw = p5_diagnose(kb, case_dict)
        return _normalize_p5(raw)
    except Exception as e:
        logger.warning(f"P5 推理失败（降级跳过）：{e}")
        return {}


def _normalize_p1(raw):
    """P1 结果标准化：List[Tuple[class, confidence]] → Dict[disease_id, {confidence, level}]"""
    normalized = {}
    for cls, conf in raw:
        did = getattr(cls, "name", str(cls))
        if conf >= 1.0:
            level = "确诊"
        elif conf >= 0.5:
            level = "疑似"
        else:
            level = "排除"
        normalized[did] = {"confidence": float(conf), "level": level}
    return normalized


def _normalize_p2(raw, excluded):
    """P2 结果标准化"""
    normalized = {}
    for name, conf, is_confirmed, did in raw:
        level = "确诊" if is_confirmed else ("疑似" if conf >= 0.5 else "排除")
        normalized[did] = {"confidence": float(conf), "level": level, "name": name}
    for ex_name in excluded:
        normalized[ex_name] = {"confidence": 0.0, "level": "排除", "name": ex_name}
    return normalized


def _normalize_p3(raw, excluded):
    """P3 结果标准化"""
    normalized = {}
    for name, conf, is_confirmed, did in raw:
        level = "确诊" if is_confirmed else ("疑似" if conf >= 0.5 else "排除")
        normalized[did] = {"confidence": float(conf), "level": level, "name": name}
    for ex_name in excluded:
        normalized[ex_name] = {"confidence": 0.0, "level": "排除", "name": ex_name}
    return normalized


def _normalize_p4(raw):
    """P4 结果标准化"""
    normalized = {}
    for name, conf, level, did in raw:
        normalized[did] = {"confidence": float(conf), "level": level, "name": name}
    return normalized


def _normalize_p5(raw):
    """P5 结果标准化"""
    normalized = {}
    for name, conf, level, did in raw:
        normalized[did] = {"confidence": float(conf), "level": level, "name": name}
    return normalized


def _arbitrate(layer1, layer2, layer3, case_dict):
    """仲裁器：综合三层结果做最终裁决"""
    # 收集所有出现的疾病
    all_diseases = {}
    for layer_name, layer_data in [("P1", layer1), ("P2", layer2), ("P3", layer3)]:
        if layer_data is None:
            continue
        for did, info in layer_data.items():
            if did not in all_diseases:
                all_diseases[did] = {"name": info.get("name", did), "engines": {}}
            all_diseases[did]["engines"][layer_name] = {
                "confidence": info["confidence"],
                "level": info["level"],
            }

    for did, info in layer2.items():
        if did not in all_diseases:
            all_diseases[did] = {"name": info.get("name", did), "engines": {}}
        all_diseases[did]["engines"]["P4"] = {
            "confidence": info["confidence"],
            "level": info["level"],
        }

    for did, info in layer3.items():
        if did not in all_diseases:
            all_diseases[did] = {"name": info.get("name", did), "engines": {}}
        all_diseases[did]["engines"]["P5"] = {
            "confidence": info["confidence"],
            "level": info["level"],
        }

    results = []
    for did, disease_info in all_diseases.items():
        engines = disease_info["engines"]

        # 统计确定性层结果
        det_engines = {k: v for k, v in engines.items() if k in ("P1", "P2", "P3")}
        det_confirmed = sum(1 for v in det_engines.values() if v["level"] == "确诊")
        det_excluded = sum(1 for v in det_engines.values() if v["level"] == "排除")
        det_available = len(det_engines)

        # 模糊层结果
        fuzzy = engines.get("P4", {})
        # 概率层结果
        bayesian = engines.get("P5", {})

        # 仲裁逻辑
        conflict = False
        final_confidence = 0.0
        final_level = ""
        note = ""

        if det_available > 0 and det_confirmed == det_available:
            # 确定性层全部确诊
            final_confidence = 1.0
            final_level = "确诊（多引擎一致）"
            note = f"确定性推理一致确诊（{det_confirmed}/{det_available}引擎）"
        elif det_available > 0 and det_excluded == det_available:
            # 确定性层全部排除
            final_confidence = 0.0
            final_level = "排除（多引擎一致）"
            note = f"确定性推理一致排除（{det_excluded}/{det_available}引擎）"
        elif det_confirmed > 0 and det_excluded > 0:
            # 确定性层冲突
            conflict = True
            final_confidence = bayesian.get("confidence", 0.5)
            final_level = "冲突（概率优先）"
            note = f"确定性推理冲突：{det_confirmed}确诊 vs {det_excluded}排除，以贝叶斯后验为准"
        else:
            # 确定性层部分一致或无结果 → 加权融合模糊 + 概率
            fuzzy_conf = fuzzy.get("confidence", 0.0)
            bayesian_conf = bayesian.get("confidence", 0.0)

            # 加权融合：概率 60% + 模糊 40%
            if fuzzy_conf > 0 and bayesian_conf > 0:
                final_confidence = bayesian_conf * 0.6 + fuzzy_conf * 0.4
                note = f"加权融合：贝叶斯({bayesian_conf:.2f})×0.6 + 模糊({fuzzy_conf:.2f})×0.4"
            elif bayesian_conf > 0:
                final_confidence = bayesian_conf
                note = "仅贝叶斯推理可用"
            elif fuzzy_conf > 0:
                final_confidence = fuzzy_conf
                note = "仅模糊推理可用"
            else:
                # 仅有确定性层部分结果
                det_confs = [v["confidence"] for v in det_engines.values()]
                final_confidence = sum(det_confs) / len(det_confs) if det_confs else 0.0
                note = "仅确定性推理部分可用"

            if final_confidence >= 0.65:
                final_level = "高度疑似"
            elif final_confidence >= 0.30:
                final_level = "疑似"
            else:
                final_level = "低置信度"

        # 检查模糊与概率是否冲突
        if fuzzy and bayesian:
            if abs(fuzzy["confidence"] - bayesian["confidence"]) > 0.3:
                conflict = True
                note += f" | 模糊({fuzzy['confidence']:.2f})与概率({bayesian['confidence']:.2f})差异大"

        results.append({
            "disease": disease_info["name"],
            "confidence": round(final_confidence, 4),
            "level": final_level,
            "disease_id": did,
            "evidence": [],
            "missing": [],
            "engine_results": engines,
            "conflict": conflict,
            "arbitration_note": note,
        })

    # 按置信度降序
    results.sort(key=lambda x: -x["confidence"])
    return results


def print_diagnosis(results):
    """格式化打印多范式仲裁结果"""
    print("\n" + "─" * 60)
    print("  📋 诊断结果（多范式分层仲裁推理）")
    print("─" * 60)
    for i, r in enumerate(results[:5], 1):
        bar = "█" * int(r["confidence"] * 10)
        conflict_tag = " ⚠️冲突" if r["conflict"] else ""
        print(f"  {i}. {r['disease']:<16} {r['confidence']:.2%}  {bar} [{r['level']}]{conflict_tag}")
        print(f"     仲裁：{r['arbitration_note']}")
        for engine, info in r["engine_results"].items():
            print(f"     {engine}: {info['confidence']:.2f} [{info['level']}]")
    print("─" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="多范式分层仲裁诊断")
    parser.add_argument("--input", default=os.path.join(SHARED_DATA_DIR, "sample_case.json"))
    args = parser.parse_args()

    print("🏥 多范式分层仲裁诊断系统（P1-P5 融合）")
    print("=" * 60)

    with open(args.input, encoding="utf-8") as f:
        case = json.load(f)
    print(f"📋 病例：{case.get('note', args.input)}")
    print(f"   症状：{', '.join(case.get('symptoms', []))}")
    print(f"   物种：{case.get('pet_type', '未知')}")

    results = diagnose(case)
    print_diagnosis(results)

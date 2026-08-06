# -*- coding: utf-8 -*-
"""
多范式贝叶斯元推理引擎 —— P1-P5 的证据融合

核心范式转变（对比旧版分层仲裁）：
  旧版：P1+P2+P3 投票 → P4 模糊 → P5 概率 → 仲裁器加权(0.6/0.4)
  新版：各引擎并行推理 → 输出转为似然比(LR) → 贝叶斯乘法融合 → 归一化

第一性原理分析发现的问题：
  1. P1/P2/P3 知识源冗余：同一份领域知识的三种编码，投票=一人投三票
  2. P4 与 P1-P3 输入空间重叠：coverage 计算逻辑与 P1-P3 置信度完全相同
  3. 权重 0.6/0.4 无理论依据：贝叶斯后验概率和模糊匹配度语义不同，不能加权平均

解决方案：贝叶斯元推理
  - P1-P3 取其一（默认 P2 Prolog，CWA 最适合诊断场景）
  - 各引擎输出统一转为似然比（Likelihood Ratio, LR）
  - 贝叶斯乘法融合：P_final(D) ∝ P_prior(D) × LR_struct × LR_fuzzy × LR_bayesian
  - 归一化得到最终后验概率分布

各引擎的增量信息：
  P2(确定性推理)：疾病-症状必要性关系 + 排除关系 → LR_struct
  P4(模糊推理)：  症状严重度（连续） → LR_fuzzy
  P5(贝叶斯推理)：先验概率 + CPT → LR_bayesian（直接输出后验）
"""

import os
import sys
import json
import math
import logging

logger = logging.getLogger(__name__)

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
CONFIG_JSON = os.path.join(LOCAL_DATA_DIR, "meta_reasoner_config.json")

# 各引擎 src 路径
_ENGINE_DIRS = {
    "P2": os.path.join(os.path.dirname(__file__), "../../P2/src"),
    "P4": os.path.join(os.path.dirname(__file__), "../../P4/src"),
    "P5": os.path.join(os.path.dirname(__file__), "../../P5/src"),
}

for path in _ENGINE_DIRS.values():
    if path not in sys.path:
        sys.path.insert(0, path)


def diagnose(case_dict):
    """
    多范式贝叶斯元推理诊断

    :param case_dict: {"pet_type": "cat", "symptoms": ["发热", "呕吐", "腹泻"]}
    :return: List[Dict] — 融合后的诊断结果，每项包含：
        {
            "disease": "猫瘟",
            "confidence": 0.92,
            "level": "高概率",
            "disease_id": "D001",
            "evidence": [...],
            "missing": [...],
            "engine_results": {
                "P2": {"confidence": 1.0, "level": "确诊", "lr": 5.0},
                "P4": {"confidence": 0.86, "level": "高", "lr": 3.2},
                "P5": {"confidence": 0.91, "level": "高概率", "lr": 18.2},
            },
            "conflict": False,
            "arbitration_note": "贝叶斯元推理：P_prior × LR_struct(5.0) × LR_fuzzy(3.2) × LR_bayesian(18.2)"
        }
    """
    config = _load_config()

    # ── 并行运行各引擎 ──
    struct_results = _run_structural_engine(case_dict)
    fuzzy_results = _run_fuzzy_engine(case_dict)
    bayesian_results = _run_bayesian_engine(case_dict)

    # ── 收集所有疾病候选 ──
    all_diseases = _collect_disease_candidates(struct_results, fuzzy_results, bayesian_results)

    # ── 对每种疾病计算融合后验 ──
    results = []
    for did, disease_info in all_diseases.items():
        # 获取先验概率（从 P5 知识库）
        prior = disease_info.get("prior", 0.05)

        # 计算各引擎的似然比
        lr_struct = _compute_structural_lr(did, struct_results, config)
        lr_fuzzy = _compute_fuzzy_lr(did, fuzzy_results, config)
        lr_bayesian = _compute_bayesian_lr(did, bayesian_results, prior, config)

        # 贝叶斯乘法融合
        # P_final(D) ∝ P_prior(D) × LR_struct × LR_fuzzy × LR_bayesian
        unnormalized = prior * lr_struct * lr_fuzzy * lr_bayesian

        # 收集各引擎结果
        engine_results = {}
        if did in struct_results:
            r = struct_results[did]
            engine_results["P2"] = {
                "confidence": r["confidence"],
                "level": r["level"],
                "lr": round(lr_struct, 3),
            }
        if did in fuzzy_results:
            r = fuzzy_results[did]
            engine_results["P4"] = {
                "confidence": r["confidence"],
                "level": r["level"],
                "lr": round(lr_fuzzy, 3),
            }
        if did in bayesian_results:
            r = bayesian_results[did]
            engine_results["P5"] = {
                "confidence": r["confidence"],
                "level": r["level"],
                "lr": round(lr_bayesian, 3),
            }

        results.append({
            "disease": disease_info["name"],
            "disease_id": did,
            "_unnorm": unnormalized,
            "_prior": prior,
            "engine_results": engine_results,
            "evidence": disease_info.get("evidence", []),
            "missing": disease_info.get("missing", []),
        })

    if not results:
        return []

    # ── 归一化 ──
    total = sum(r["_unnorm"] for r in results)
    if total == 0:
        return []

    for r in results:
        r["confidence"] = round(r["_unnorm"] / total, 4)
        r["level"] = _probability_level(r["confidence"])

        # 构建仲裁说明
        lrs = {k: v["lr"] for k, v in r["engine_results"].items()}
        lr_parts = " x ".join(f"LR_{k}({v})" for k, v in lrs.items())
        r["arbitration_note"] = (
            f"贝叶斯元推理：P_prior({r['_prior']:.4f}) x {lr_parts} "
            f"-> 归一化后验 {r['confidence']:.2%}"
        )

        # 冲突检测：似然比方向不一致
        r["conflict"] = _detect_conflict(r["engine_results"])

        # 清理内部字段
        del r["_unnorm"]
        del r["_prior"]

    # 按后验概率降序
    results.sort(key=lambda x: -x["confidence"])
    return results


# ============================================================
# 引擎执行
# ============================================================

def _run_structural_engine(case_dict):
    """
    运行确定性推理引擎（默认使用 P2 Prolog）

    选择 P2 而非 P1/P3 的理由：
    - P1/P2/P3 共享同一份领域知识的不同编码形式，知识源冗余
    - P2 的 CWA（封闭世界假设）最适合诊断场景：
      未断言的症状 = 没有 → 可以直接排除
    - P1 的 OWA 过于保守（不排除未断言的）
    - P3 需要外部 Fuseki 服务，依赖重
    """
    try:
        from reasoner import load_knowledge_base as p2_load, diagnose as p2_diagnose
        prolog = p2_load()
        raw, excluded = p2_diagnose(prolog, case_dict)

        results = {}
        for name, conf, is_confirmed, did in raw:
            if is_confirmed:
                level = "确诊"
            elif conf >= 0.5:
                level = "疑似"
            else:
                level = "低匹配"
            results[did] = {
                "confidence": float(conf),
                "level": level,
                "name": name,
                "is_confirmed": is_confirmed,
            }
        # 排除的疾病
        for ex_name in excluded:
            # 用名称作为 key（排除的疾病可能没有 did）
            results[ex_name] = {
                "confidence": 0.0,
                "level": "排除",
                "name": ex_name,
                "is_confirmed": False,
                "is_excluded": True,
            }
        return results
    except Exception as e:
        logger.warning(f"P2 确定性推理失败（降级跳过）：{e}")
        return {}


def _run_fuzzy_engine(case_dict):
    """运行 P4 模糊推理引擎"""
    try:
        from reasoner import load_knowledge_base as p4_load, diagnose as p4_diagnose
        kb = p4_load()
        raw = p4_diagnose(kb, case_dict)

        results = {}
        for name, conf, level, did in raw:
            results[did] = {
                "confidence": float(conf),
                "level": level,
                "name": name,
            }
        return results
    except Exception as e:
        logger.warning(f"P4 模糊推理失败（降级跳过）：{e}")
        return {}


def _run_bayesian_engine(case_dict):
    """运行 P5 贝叶斯推理引擎"""
    try:
        from reasoner import load_knowledge_base as p5_load, diagnose as p5_diagnose
        kb = p5_load()
        raw = p5_diagnose(kb, case_dict)

        results = {}
        for name, conf, level, did in raw:
            results[did] = {
                "confidence": float(conf),
                "level": level,
                "name": name,
            }
        return results
    except Exception as e:
        logger.warning(f"P5 贝叶斯推理失败（降级跳过）：{e}")
        return {}


# ============================================================
# 似然比计算
# ============================================================

def _compute_structural_lr(did, struct_results, config):
    """
    将确定性推理结果转为似然比

    似然比（Likelihood Ratio）的医学含义：
      LR+ = P(确诊|患病) / P(确诊|未患病)  → 确诊证据增强
      LR- = P(排除|患病) / P(排除|未患病)  → 排除证据减弱

    映射策略：
      确诊 → LR+ (config: lr_confirmed, 默认 5.0)
      疑似 → 中性 LR (config: lr_suspect, 默认 1.5)
      低匹配 → 弱 LR (config: lr_low_match, 默认 0.8)
      排除 → LR- (config: lr_excluded, 默认 0.1)
      未出现 → 中性 1.0（无信息）
    """
    lr_confirmed = config.get("lr_confirmed", 5.0)
    lr_suspect = config.get("lr_suspect", 1.5)
    lr_low_match = config.get("lr_low_match", 0.8)
    lr_excluded = config.get("lr_excluded", 0.1)

    if did not in struct_results:
        return 1.0

    r = struct_results[did]
    if r.get("is_excluded"):
        return lr_excluded
    if r.get("is_confirmed"):
        return lr_confirmed
    level = r.get("level", "")
    if level == "确诊":
        return lr_confirmed
    elif level == "疑似":
        return lr_suspect
    elif level == "排除":
        return lr_excluded
    elif level == "低匹配":
        return lr_low_match
    return 1.0


def _compute_fuzzy_lr(did, fuzzy_results, config):
    """
    将模糊推理的匹配度转为似然比

    模糊匹配度 [0, 1] → 似然比 [lr_min, lr_max]

    使用指数映射：LR = exp(k * (confidence - 0.5))
      confidence = 0.5 → LR = 1.0（中性）
      confidence = 1.0 → LR = exp(k/2)（强支持）
      confidence = 0.0 → LR = exp(-k/2)（强反对）

    理由：似然比在医学中通常是乘法关系，指数映射保证：
      - LR 始终为正
      - 对称区间（支持/反对）
      - 可调灵敏度（k 参数）
    """
    k = config.get("fuzzy_lr_k", 3.0)

    if did not in fuzzy_results:
        return 1.0

    conf = fuzzy_results[did]["confidence"]
    return math.exp(k * (conf - 0.5))


def _compute_bayesian_lr(did, bayesian_results, prior, config):
    """
    将贝叶斯后验概率转为似然比

    P5 直接输出了 P(D|S)（后验概率），这已经是融合了先验和似然的完整结果。
    我们将其转为似然比：LR = posterior / prior

    含义：后验概率相对于先验的提升倍数。
      LR = 1.0 → 后验 = 先验（症状没有提供额外信息）
      LR > 1.0 → 症状支持该疾病
      LR < 1.0 → 症状反对该疾病

    注意：P5 的后验概率经过归一化，是相对概率。
    转为 LR 后消除了归一化的影响，只保留"证据方向"。
    """
    if did not in bayesian_results:
        return 1.0

    posterior = bayesian_results[did]["confidence"]
    if prior <= 0:
        return 1.0 if posterior <= 0 else float("inf")

    lr = posterior / prior
    # 限制极端值
    lr_max = config.get("lr_max", 100.0)
    lr_min = config.get("lr_min", 0.01)
    return max(lr_min, min(lr_max, lr))


# ============================================================
# 辅助函数
# ============================================================

def _load_config():
    """加载元推理配置"""
    defaults = {
        "lr_confirmed": 5.0,
        "lr_suspect": 1.5,
        "lr_low_match": 0.8,
        "lr_excluded": 0.1,
        "fuzzy_lr_k": 3.0,
        "lr_max": 100.0,
        "lr_min": 0.01,
        "conflict_lr_ratio": 5.0,
    }
    if os.path.exists(CONFIG_JSON):
        try:
            with open(CONFIG_JSON, encoding="utf-8") as f:
                user_config = json.load(f)
                defaults.update(user_config.get("lr_mapping", {}))
        except Exception:
            pass
    return defaults


def _collect_disease_candidates(struct_results, fuzzy_results, bayesian_results):
    """收集所有引擎输出的疾病候选，合并信息"""
    all_diseases = {}

    for did, info in struct_results.items():
        if did not in all_diseases:
            all_diseases[did] = {"name": info.get("name", did), "prior": 0.05}
        all_diseases[did]["name"] = info.get("name", all_diseases[did]["name"])

    for did, info in fuzzy_results.items():
        if did not in all_diseases:
            all_diseases[did] = {"name": info.get("name", did), "prior": 0.05}
        all_diseases[did]["name"] = info.get("name", all_diseases[did]["name"])

    for did, info in bayesian_results.items():
        if did not in all_diseases:
            all_diseases[did] = {"name": info.get("name", did), "prior": 0.05}
        all_diseases[did]["name"] = info.get("name", all_diseases[did]["name"])

    # 从 P5 知识库获取先验概率
    try:
        from reasoner import load_knowledge_base as p5_load
        kb = p5_load()
        for disease in kb["diseases"]:
            if disease["id"] in all_diseases:
                all_diseases[disease["id"]]["prior"] = disease.get("prior", 0.05)
    except Exception:
        pass

    return all_diseases


def _probability_level(prob):
    """将后验概率映射到等级标签"""
    if prob >= 0.50:
        return "高概率"
    elif prob >= 0.15:
        return "中概率"
    else:
        return "低概率"


def _detect_conflict(engine_results):
    """
    冲突检测：似然比方向不一致

    如果一个引擎的 LR > 1（支持）而另一个 LR < 1（反对），
    且比值超过阈值，则标记冲突。
    """
    if len(engine_results) < 2:
        return False

    lrs = [v["lr"] for v in engine_results.values() if v["lr"] > 0]
    if len(lrs) < 2:
        return False

    max_lr = max(lrs)
    min_lr = min(lrs)
    ratio = max_lr / min_lr if min_lr > 0 else float("inf")

    config = _load_config()
    threshold = config.get("conflict_lr_ratio", 5.0)
    return ratio > threshold


def explain(case_dict):
    """
    生成元推理链解释（可追溯的诊断依据）

    对比旧版仲裁器的 explain：
      旧版：列出各层结果 + 仲裁规则
      新版：列出各引擎的 LR + 贝叶斯融合公式 + 先验/后验变化
    """
    results = diagnose(case_dict)
    if not results:
        return []

    explanations = []
    for r in results[:5]:
        engine_lrs = {
            k: v["lr"] for k, v in r["engine_results"].items()
        }
        explanations.append({
            "disease_id": r["disease_id"],
            "disease_name": r["disease"],
            "posterior": r["confidence"],
            "level": r["level"],
            "engine_lrs": engine_lrs,
            "arbitration_note": r["arbitration_note"],
            "conflict": r["conflict"],
        })

    return explanations


def print_diagnosis(results):
    """格式化打印多范式贝叶斯元推理结果"""
    print("\n" + "-" * 60)
    print("  诊断结果（多范式贝叶斯元推理）")
    print("-" * 60)
    for i, r in enumerate(results[:5], 1):
        bar = "|" * int(r["confidence"] * 10)
        conflict_tag = " [冲突]" if r["conflict"] else ""
        print(f"  {i}. {r['disease']:<16} {r['confidence']:.2%}  {bar} [{r['level']}]{conflict_tag}")
        print(f"     融合：{r['arbitration_note']}")
        for engine, info in r["engine_results"].items():
            print(f"     {engine}: conf={info['confidence']:.2f} [{info['level']}] LR={info['lr']:.2f}")
    print("-" * 60)

    print("\n  核心原理：")
    print("     各引擎输出统一转为似然比(LR)，以贝叶斯乘法融合")
    print("     P_final(D) x P_prior(D) x LR_struct x LR_fuzzy x LR_bayesian")
    print("     归一化后得到最终后验概率分布")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="多范式贝叶斯元推理诊断")
    parser.add_argument("--input", default=os.path.join(SHARED_DATA_DIR, "sample_case.json"))
    args = parser.parse_args()

    print("多范式贝叶斯元推理诊断系统（P2 + P4 + P5 证据融合）")
    print("=" * 60)

    with open(args.input, encoding="utf-8") as f:
        case = json.load(f)
    print(f"病例：{case.get('note', args.input)}")
    print(f"   症状：{', '.join(case.get('symptoms', []))}")
    print(f"   物种：{case.get('pet_type', '未知')}")

    results = diagnose(case)
    print_diagnosis(results)

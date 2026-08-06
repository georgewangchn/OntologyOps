# -*- coding: utf-8 -*-
"""
诊断主流程 —— 多范式贝叶斯元推理

核心范式转变（对比旧版分层仲裁）：
  旧版：P1+P2+P3 投票 → P4 模糊 → P5 概率 → 仲裁器加权(0.6/0.4)
  新版：P2+P4+P5 并行 → 各引擎输出转似然比(LR) → 贝叶斯乘法融合 → 归一化

关键改进：
  1. P1-P3 取其一（P2 Prolog），消除知识源冗余
  2. 各引擎输出统一转为似然比，语义对齐
  3. 贝叶斯乘法融合有概率论保证（贝叶斯定理链式法则）
"""

from reasoner import diagnose, print_diagnosis, explain
import json
import os

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")


def diagnose_from_json(json_path):
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)
    results = diagnose(case)
    print_diagnosis(results)
    return results


def diagnose_interactive():
    print("多范式贝叶斯元推理诊断系统（交互模式）")
    print("=" * 60)

    case = {}
    case["pet_type"] = input("物种 (cat/dog)：").strip() or "cat"
    symptoms_input = input("症状（逗号分隔）：").strip()
    case["symptoms"] = [s.strip() for s in symptoms_input.split(",") if s.strip()]

    print(f"\n病例：{case['pet_type']}，症状：{', '.join(case['symptoms'])}")
    results = diagnose(case)
    print_diagnosis(results)
    return results


def diagnose_api(case_dict):
    output = {
        "success": True,
        "pet_type": case_dict.get("pet_type", "unknown"),
        "symptoms": case_dict.get("symptoms", []),
        "results": [
            {
                "disease": r["disease"],
                "confidence": r["confidence"],
                "level": r["level"],
                "id": r["disease_id"],
                "conflict": r["conflict"],
                "arbitration_note": r["arbitration_note"],
                "engine_results": r["engine_results"],
            }
            for r in diagnose(case_dict)[:10]
        ]
    }
    return output


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        diagnose_from_json(sys.argv[1])
    else:
        diagnose_interactive()

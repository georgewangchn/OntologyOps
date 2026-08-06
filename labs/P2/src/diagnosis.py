# -*- coding: utf-8 -*-
"""
诊断主流程 —— 串联「数据输入 → Prolog 推理 → 结果输出」
对比 P1 的 diagnosis.py：支持 JSON / 交互式 / API 三种入口
"""

from reasoner import diagnose, load_knowledge_base, print_diagnosis, explain
import json
import os

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")


def diagnose_from_json(json_path):
    """从 JSON 文件读取病例并执行诊断"""
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)

    prolog = load_knowledge_base()
    results, excluded = diagnose(prolog, case)
    print_diagnosis(results, excluded)
    return results


def diagnose_interactive():
    """交互式诊断"""
    print("🏥 宠物疾病诊断系统（Prolog 交互模式）")
    print("=" * 50)

    case = {}
    case["pet_type"] = input("物种 (cat/dog)：").strip() or "cat"
    case["breed"] = input("品种：").strip()
    case["age"] = input("年龄（岁）：").strip()
    symptoms_input = input("症状（逗号分隔，如：发热,呕吐,腹泻）：").strip()
    case["symptoms"] = [s.strip() for s in symptoms_input.split(",") if s.strip()]

    print(f"\n📋 病例摘要：{case['pet_type']}，{case['age']}岁，症状：{', '.join(case['symptoms'])}")
    print()

    prolog = load_knowledge_base()
    results, excluded = diagnose(prolog, case)
    print_diagnosis(results, excluded)
    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        if not os.path.exists(json_path):
            json_path = os.path.join(SHARED_DATA_DIR, os.path.basename(json_path))
        diagnose_from_json(json_path)
    else:
        diagnose_interactive()

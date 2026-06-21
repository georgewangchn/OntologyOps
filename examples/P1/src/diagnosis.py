# -*- coding: utf-8 -*-
"""
诊断主流程 —— 串联「数据输入 → 本体推理 → 结果输出」
支持三种输入方式：
  1. JSON 文件（结构化病例）
  2. 交互式命令行输入
  3. API 调用（返回 JSON）
"""

from reasoner import diagnose, load_ontology, run_reasoner, print_diagnosis
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")


def diagnose_from_json(json_path):
    """从 JSON 文件读取病例并执行诊断"""
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)

    onto = load_ontology()
    results = diagnose(onto, case)
    print_diagnosis(results)
    return results


def diagnose_interactive():
    """交互式诊断"""
    print("🏥 宠物疾病诊断系统（交互模式）")
    print("=" * 50)

    case = {}
    case["pet_type"]  = input("物种 (cat/dog)：").strip() or "cat"
    case["breed"]     = input("品种：").strip()
    case["age"]        = input("年龄（岁）：").strip()
    symptoms_input     = input("症状（逗号分隔，如：发热,呕吐,腹泻）：").strip()
    case["symptoms"]  = [s.strip() for s in symptoms_input.split(",") if s.strip()]

    print(f"\n📋 病例摘要：{case['pet_type']}，{case['age']}岁，症状：{', '.join(case['symptoms'])}")
    print()

    onto = load_ontology()
    results = diagnose(onto, case)
    print_diagnosis(results)
    return results


def diagnose_api(case_dict):
    """
    API 调用接口（供 Web 服务调用）
    返回 JSON 格式结果：
    {
      "success": true,
      "results": [
        {"disease": "猫瘟", "confidence": 0.92, "reason": "必要症状匹配..."},
        ...
      ]
    }
    """
    onto = load_ontology()
    results = diagnose(onto, case_dict)

    output = {
        "success": True,
        "pet_type": case_dict.get("pet_type", "unknown"),
        "symptoms": case_dict.get("symptoms", []),
        "results": [
            {
                "disease": cls.label[0] if cls.label else cls.name,
                "confidence": round(conf, 2),
                "iri": str(cls.iri) if hasattr(cls, "iri") else ""
            }
            for cls, conf in results[:10]
        ]
    }
    return output


# ── CLI 入口 ──────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 命令行传入 JSON 路径
        json_path = sys.argv[1]
        if not os.path.exists(json_path):
            # 尝试在 data/ 目录下查找
            json_path = os.path.join(DATA_DIR, os.path.basename(json_path))
        diagnose_from_json(json_path)
    else:
        # 无参数时进入交互模式
        diagnose_interactive()

# -*- coding: utf-8 -*-
"""
诊断主流程 —— 串联「数据输入 → 模糊推理 → 结果输出」
对比 P1-P3 的 diagnosis.py：支持 JSON / 交互式 / API 三种入口

核心差异：
  P1：diagnosis.py 调用 reasoner.diagnose(onto, case)，onto 是 OWL 本体
  P2：diagnosis.py 调用 reasoner.diagnose(prolog, case)，prolog 是 SWI-Prolog 引擎
  P3：diagnosis.py 调用 reasoner.diagnose(case)，Fuseki 是外部 HTTP 服务
  P4：diagnosis.py 调用 reasoner.diagnose(kb, case)，kb 是模糊知识库（JSON）
"""

from reasoner import diagnose, load_knowledge_base, print_diagnosis, explain
from utils import load_symptom_baselines, compute_symptom_severity
import json
import os

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")


def diagnose_from_json(json_path):
    """从 JSON 文件读取病例并执行诊断"""
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)

    kb = load_knowledge_base()
    results = diagnose(kb, case)
    print_diagnosis(results)
    return results


def diagnose_interactive():
    """交互式诊断"""
    print("🏥 宠物疾病诊断系统（模糊推理 · 交互模式）")
    print("=" * 50)

    case = {}
    case["pet_type"] = input("物种 (cat/dog)：").strip() or "cat"
    case["breed"] = input("品种：").strip()
    case["age"] = input("年龄（岁）：").strip()
    symptoms_input = input("症状（逗号分隔，如：发热,呕吐,腹泻）：").strip()
    case["symptoms"] = [s.strip() for s in symptoms_input.split(",") if s.strip()]

    # 交互式收集症状严重度（P4 独有）
    case["symptom_details"] = {}
    for s in case["symptoms"]:
        print(f"\n  「{s}」的详细情况：")
        if s == "发热":
            temp = input(f"    体温（°C，默认38.5）：").strip()
            if temp:
                case["symptom_details"][s] = {"degree": "高", "value": float(temp)}
        elif s == "呕吐":
            freq = input(f"    频率（偶尔/多次/频繁）：").strip()
            if freq:
                case["symptom_details"][s] = {"frequency": freq}
        elif s == "腹泻":
            dtype = input(f"    类型（成型/软便/水样）：").strip()
            color = input(f"    颜色（正常/暗红/血）：").strip()
            detail = {}
            if dtype:
                detail["type"] = dtype
            if color:
                detail["color"] = color
            if detail:
                case["symptom_details"][s] = detail

    print(f"\n📋 病例摘要：{case['pet_type']}，{case['age']}岁，症状：{', '.join(case['symptoms'])}")

    baselines = load_symptom_baselines()
    print(f"\n   症状严重度（模糊化输入）：")
    for s in case["symptoms"]:
        sev = compute_symptom_severity(s, case, baselines)
        print(f"     {s}: {sev:.2f}")
    print()

    kb = load_knowledge_base()
    results = diagnose(kb, case)
    print_diagnosis(results)
    return results


def diagnose_api(case_dict):
    """
    API 调用接口（供 Web 服务调用）
    返回 JSON 格式结果：
    {
      "success": true,
      "results": [
        {"disease": "猫瘟", "confidence": 0.85, "level": "高", "id": "D001"},
        ...
      ]
    }
    """
    kb = load_knowledge_base()
    results = diagnose(kb, case_dict)

    output = {
        "success": True,
        "pet_type": case_dict.get("pet_type", "unknown"),
        "symptoms": case_dict.get("symptoms", []),
        "results": [
            {
                "disease": name,
                "confidence": round(conf, 2),
                "level": level,
                "id": did,
            }
            for name, conf, level, did in results[:10]
        ]
    }
    return output


# ── CLI 入口 ──────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        if not os.path.exists(json_path):
            json_path = os.path.join(SHARED_DATA_DIR, os.path.basename(json_path))
        diagnose_from_json(json_path)
    else:
        diagnose_interactive()

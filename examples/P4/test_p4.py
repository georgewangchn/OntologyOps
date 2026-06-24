#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P4 完整流程测试脚本
用法：python test_p4.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_kb_builder():
    print("=" * 50)
    print(" 测试 1/3：模糊知识库构建")
    print("=" * 50)

    from kb_builder import build_kb

    path = build_kb()
    print(f"✅ 知识库构建完成：{path}\n")

    # 断言：知识库文件已生成
    assert os.path.exists(path), "知识库文件未生成"
    with open(path, encoding="utf-8") as f:
        import json
        kb = json.load(f)

    # 断言：包含隶属度函数
    assert "membership_functions" in kb, "知识库缺少隶属度函数"
    assert "覆盖率" in kb["membership_functions"], "缺少覆盖率隶属度函数"
    assert "强度" in kb["membership_functions"], "缺少强度隶属度函数"
    assert "排除度" in kb["membership_functions"], "缺少排除度隶属度函数"
    assert "置信度" in kb["membership_functions"], "缺少置信度隶属度函数"

    # 断言：包含模糊规则
    assert "fuzzy_rules" in kb, "知识库缺少模糊规则"
    assert len(kb["fuzzy_rules"]) == 12, f"应有12条模糊规则，实际{len(kb['fuzzy_rules'])}条"

    # 断言：包含疾病定义
    assert len(kb["diseases"]) >= 10, f"疾病数量不足：{len(kb['diseases'])}"

    return kb


def test_reasoner(kb):
    print("=" * 50)
    print(" 测试 2/3：模糊推理")
    print("=" * 50)

    from reasoner import diagnose, print_diagnosis

    case = {
        "pet_type": "cat",
        "symptoms": ["发热", "呕吐", "腹泻"],
        "symptom_details": {
            "发热": {"degree": "高", "value": 39.5},
            "呕吐": {"frequency": "多次"},
            "腹泻": {"type": "水样", "color": "暗红"},
        },
        "breed": "英短",
        "age": 2,
    }

    results = diagnose(kb, case)
    print_diagnosis(results)

    # 断言：猫瘟应排第一
    assert len(results) > 0, "推理结果为空"
    assert results[0][0] == "猫瘟", f"首选诊断应为猫瘟，实际为 {results[0][0]}"

    # 断言：猫瘟置信度应为"高"（>0.6）
    assert results[0][2] == "高", f"猫瘟模糊等级应为高，实际为 {results[0][2]}"
    assert results[0][1] > 0.6, f"猫瘟置信度应>0.6，实际为 {results[0][1]:.2f}"

    # 断言：犬细小病毒（犬病）不应出现在猫的结果中（物种过滤）
    result_names = [r[0] for r in results]
    assert "犬细小病毒" not in result_names, "犬细小病毒（犬病）不应出现在猫的诊断结果中"
    assert "犬感冒" not in result_names, "犬感冒（犬病）不应出现在猫的诊断结果中"

    # ── P4 独有断言：猫肠炎应出现在结果中（与 P1-P3 的关键区别）──
    # P1-P3：猫肠炎因排除症状"发热"命中 → 完全排除（不在结果中）
    # P4：猫肠炎因排除症状"发热"命中 → 置信度降低（仍在结果中，但排名低）
    assert "猫肠炎" in result_names, (
        "猫肠炎应出现在模糊推理结果中（P4 不完全排除，只降低置信度）"
    )
    maochangyan = [r for r in results if r[0] == "猫肠炎"][0]
    # 双输入设计：猫肠炎覆盖率=1.0(高)、强度=0.8(高)，排除度=0.8(有)
    # → 规则12：高×高×有 → 置信度=中（降一级，不是完全低）
    assert maochangyan[2] == "中", (
        f"猫肠炎模糊等级应为中（全覆盖高强度高但排除度有 → 降一级），实际为 {maochangyan[2]}"
    )
    print(f"\n  💡 猫肠炎出现在结果中（置信度={maochangyan[1]:.2f}，等级=中）")
    print(f"     P1-P3 中猫肠炎被完全排除，P4 中降为中等置信度——这是模糊推理的核心区别")
    print(f"     双输入设计：覆盖率=高+强度=高 但排除度=有 → 降一级（中），而非完全压低（低）")

    return results


def test_diagnosis_module():
    print("=" * 50)
    print(" 测试 3/3：诊断模块（从 JSON）")
    print("=" * 50)

    import json
    from reasoner import load_knowledge_base, diagnose, print_diagnosis, explain

    json_path = os.path.join(os.path.dirname(__file__), "..", "shared_data", "sample_case.json")
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)

    kb = load_knowledge_base()
    results = diagnose(kb, case)
    print_diagnosis(results)

    # 断言：样本病例（猫）首选诊断应为猫瘟
    assert len(results) > 0, "JSON 病例推理结果为空"
    assert results[0][0] == "猫瘟", f"JSON 病例首选诊断应为猫瘟，实际为 {results[0][0]}"

    # 打印推理链
    print("\n  🔗 推理链解释：")
    explanations = explain(kb, case)
    for exp in explanations[:3]:
        print(f"\n  [{exp['disease_name']}]")
        print(f"    覆盖率：{exp['coverage']}  强度：{exp['intensity']}  排除度：{exp['exclusion_degree']}")
        print(f"    必要症状：")
        for s in exp["necessary_symptoms"]:
            tag = "✅" if s["present"] else "❌"
            print(f"      {s['symptom']}: 严重度={s['severity']} {tag}")
        if exp["exclusion_symptoms"]:
            print(f"    排除症状：")
            for s in exp["exclusion_symptoms"]:
                tag = "⚠️命中" if s["present"] else "✅未命中"
                print(f"      {s['symptom']}: 严重度={s['severity']} {tag}")
    print()

    # 断言：推理链解释非空
    assert len(explanations) > 0, "推理链解释为空"

    # 断言：猫瘟的覆盖率应为 1.0（3/3 必要症状全部出现）
    mao = [e for e in explanations if e["disease_name"] == "猫瘟"][0]
    assert mao["coverage"] == 1.0, f"猫瘟覆盖率应为1.0，实际为 {mao['coverage']}"
    assert mao["intensity"] > 0.6, f"猫瘟强度应>0.6，实际为 {mao['intensity']}"
    assert mao["exclusion_degree"] < 0.1, f"猫瘟排除度应≈0，实际为 {mao['exclusion_degree']}"


if __name__ == "__main__":
    print("\n🏥 宠物疾病模糊推理系统 · P4 测试\n")

    try:
        kb = test_kb_builder()
        test_reasoner(kb)
        test_diagnosis_module()
        print("🎉 全部测试通过！\n")
    except Exception as e:
        print(f"❌ 测试失败：{e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

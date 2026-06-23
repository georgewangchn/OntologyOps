#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1 完整流程测试脚本
用法：python test_p1.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def test_onto_builder():
    print("=" * 50)
    print(" 测试 1/3：本体构建")
    print("=" * 50)

    from onto_builder import create_ontology, load_diseases, load_symptoms, add_symptom_relations, save_ontology

    onto = create_ontology()
    onto = load_diseases(onto)
    onto = load_symptoms(onto)
    onto = add_symptom_relations(onto)
    path = save_ontology(onto)

    # 断言：本体文件已生成
    assert os.path.exists(path), "本体文件未生成"
    assert os.path.getsize(path) > 0, "本体文件为空"

    # 断言：疾病类已创建
    disease_classes = [c for c in onto.classes() if c != onto.疾病]
    assert len(disease_classes) >= 10, f"疾病类数量不足：{len(disease_classes)}"

    print(f"✅ 本体构建完成：{path}\n")
    return onto


def test_reasoner(onto):
    print("=" * 50)
    print(" 测试 2/3：推理机")
    print("=" * 50)

    from reasoner import diagnose, print_diagnosis

    case = {
        "pet_type": "cat",
        "symptoms": ["发热", "呕吐", "腹泻"],
        "breed": "英短",
        "age": 2
    }

    results = diagnose(onto, case)
    print_diagnosis(results)

    # 断言：猫瘟应排第一
    assert len(results) > 0, "推理结果为空"
    top_name = results[0][0].label[0] if results[0][0].label else results[0][0].name
    assert top_name == "猫瘟", f"首选诊断应为猫瘟，实际为 {top_name}"

    # 断言：置信度约为 0.99
    assert abs(results[0][1] - 0.99) < 0.01, f"猫瘟置信度应为0.99，实际为 {results[0][1]}"

    # 断言：犬细小病毒（犬病）不应出现在猫的结果中（物种过滤）
    result_names = [cls.label[0] if cls.label else cls.name for cls, _ in results]
    assert "犬细小病毒" not in result_names, "犬细小病毒（犬病）不应出现在猫的诊断结果中"
    assert "犬感冒" not in result_names, "犬感冒（犬病）不应出现在猫的诊断结果中"

    return results


def test_diagnosis_module():
    print("=" * 50)
    print(" 测试 3/3：诊断模块（从 JSON）")
    print("=" * 50)

    import json
    from reasoner import load_ontology, diagnose, print_diagnosis

    json_path = os.path.join(os.path.dirname(__file__), "..", "shared_data", "sample_case.json")
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)

    onto = load_ontology()
    results = diagnose(onto, case)
    print_diagnosis(results)
    print()

    # 断言：样本病例（猫）首选诊断应为猫瘟
    assert len(results) > 0, "JSON 病例推理结果为空"
    top_name = results[0][0].label[0] if results[0][0].label else results[0][0].name
    assert top_name == "猫瘟", f"JSON 病例首选诊断应为猫瘟，实际为 {top_name}"


if __name__ == "__main__":
    print("\n🏥 宠物疾病本体推理系统 · P1 测试\n")

    try:
        onto = test_onto_builder()
        test_reasoner(onto)
        test_diagnosis_module()
        print("🎉 全部测试通过！\n")
    except Exception as e:
        print(f"❌ 测试失败：{e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

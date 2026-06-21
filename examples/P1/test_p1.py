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
    return results


def test_diagnosis_module():
    print("=" * 50)
    print(" 测试 3/3：诊断模块（从 JSON）")
    print("=" * 50)

    import json
    from reasoner import load_ontology, diagnose, print_diagnosis

    json_path = os.path.join(os.path.dirname(__file__), "data", "sample_case.json")
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)

    onto = load_ontology()
    results = diagnose(onto, case)
    print_diagnosis(results)
    print()


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

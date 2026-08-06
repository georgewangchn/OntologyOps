#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2 完整流程测试脚本
用法：python test_p2.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_kb_builder():
    print("=" * 50)
    print(" 测试 1/3：知识库构建")
    print("=" * 50)

    from kb_builder import build_kb

    path = build_kb()
    print(f"✅ 知识库构建完成：{path}\n")

    # 断言：知识库文件已生成
    assert os.path.exists(path), "知识库文件未生成"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "disease(d001," in content, "知识库缺少 d001 疾病事实"
    assert "necessary(d001," in content, "知识库缺少必要症状事实"

    return path


def test_reasoner():
    print("=" * 50)
    print(" 测试 2/3：Prolog 推理")
    print("=" * 50)

    from reasoner import load_knowledge_base, diagnose, print_diagnosis

    case = {
        "pet_type": "cat",
        "symptoms": ["发热", "呕吐", "腹泻"],
        "breed": "英短",
        "age": 2
    }

    prolog = load_knowledge_base()
    results, excluded = diagnose(prolog, case)
    print_diagnosis(results, excluded)

    # 断言：猫瘟应排第一
    assert len(results) > 0, "推理结果为空"
    assert results[0][0] == "猫瘟", f"首选诊断应为猫瘟，实际为 {results[0][0]}"

    # 断言：猫瘟应为确诊
    assert results[0][2] == True, "猫瘟应为确诊（全匹配 + 无排除）"

    # 断言：置信度应为 1.0
    assert abs(results[0][1] - 1.0) < 0.01, f"猫瘟置信度应为1.0，实际为 {results[0][1]}"

    # 断言：犬细小病毒（犬病）不应出现在猫的结果中（物种过滤）
    result_names = [r[0] for r in results]
    assert "犬细小病毒" not in result_names, "犬细小病毒（犬病）不应出现在猫的诊断结果中"
    assert "犬感冒" not in result_names, "犬感冒（犬病）不应出现在猫的诊断结果中"

    return results


def test_diagnosis_module():
    print("=" * 50)
    print(" 测试 3/3：诊断模块（从 JSON）")
    print("=" * 50)

    from reasoner import load_knowledge_base, diagnose, print_diagnosis, explain

    json_path = os.path.join(os.path.dirname(__file__), "..", "shared_data", "sample_case.json")
    import json
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)

    prolog = load_knowledge_base()
    results, excluded = diagnose(prolog, case)
    print_diagnosis(results, excluded)

    # 断言：样本病例（猫）首选诊断应为猫瘟
    assert len(results) > 0, "JSON 病例推理结果为空"
    assert results[0][0] == "猫瘟", f"JSON 病例首选诊断应为猫瘟，实际为 {results[0][0]}"

    # 打印推理链
    print("  🔗 推理链解释：")
    explanations = explain(prolog, case)
    for exp in explanations:
        print(f"\n  [{exp['disease_name']}]")
        if exp["matched"]:
            print(f"    匹配：{', '.join(exp['matched'])} ✅")
        if exp["missing"]:
            print(f"    缺失：{', '.join(exp['missing'])} ❌")
        if exp["excluded"]:
            print(f"    排除症状命中：{', '.join(exp['excluded'])} 🚫")
        else:
            print(f"    排除症状：无命中 ✅")
    print()

    # 断言：推理链解释非空
    assert len(explanations) > 0, "推理链解释为空"


if __name__ == "__main__":
    print("\n🏥 宠物疾病诊断推理系统 · P2 测试（Prolog）\n")

    try:
        test_kb_builder()
        test_reasoner()
        test_diagnosis_module()
        print("🎉 全部测试通过！\n")
    except Exception as e:
        print(f"❌ 测试失败：{e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

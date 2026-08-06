#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3 完整流程测试脚本
用法：python test_p3.py

支持两种模式：
  1. Fuseki 模式（docker-compose up -d 后运行，通过 SPARQL 端点查询）
  2. 本地模式（无 Docker 时，用 rdflib 模拟前向链推理）
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

    # 断言：Turtle 文件已生成
    assert os.path.exists(path), "Turtle 文件未生成"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert ":d001" in content, "知识库缺少 d001 疾病个体"
    assert ":has_species" in content, "知识库缺少物种三元组"
    assert ":d010 :contain :d005" in content, "知识库缺少传递闭包链数据"

    return path


def test_local_reasoner():
    """本地模式测试（rdflib 模拟前向链）"""
    print("=" * 50)
    print(" 测试 2/3：前向链推理（rdflib 本地模式）")
    print("=" * 50)

    from local_reasoner import diagnose_local, print_diagnosis

    case = {
        "pet_type": "cat",
        "symptoms": ["发热", "呕吐", "腹泻"],
        "breed": "英短",
        "age": 2
    }

    results, excluded = diagnose_local(case)
    print_diagnosis(results, excluded)

    # 断言：猫瘟应排第一
    assert len(results) > 0, "推理结果为空"
    assert results[0][0] == "猫瘟", f"首选诊断应为猫瘟，实际为 {results[0][0]}"

    # 断言：置信度应为 1.0（3/3 全匹配）
    assert abs(results[0][1] - 1.0) < 0.01, f"猫瘟置信度应为1.0，实际为 {results[0][1]}"

    # 断言：犬细小病毒（犬病）不应出现在猫的结果中（物种过滤）
    result_names = [r[0] for r in results]
    assert "犬细小病毒" not in result_names, "犬细小病毒（犬病）不应出现在猫的诊断结果中"
    assert "犬感冒" not in result_names, "犬感冒（犬病）不应出现在猫的诊断结果中"
    assert "犬冠状病毒" not in result_names, "犬冠状病毒（犬病）不应出现在猫的诊断结果中"

    return results


def test_transitive():
    print("=" * 50)
    print(" 测试 3/3：传递闭包（前向链预计算）")
    print("=" * 50)

    from local_reasoner import query_transitive_local, get_graph

    query_transitive_local()

    # 断言：传递闭包应包含 d010 → d004（通过 d005 中转）
    graph = get_graph()
    from rdflib import URIRef
    ns = "http://petbps.com/ontology/pet_disease#"
    d010 = URIRef(ns + "d010")
    d004 = URIRef(ns + "d004")
    contain = URIRef(ns + "contain")
    triples = list(graph.triples((d010, contain, d004)))
    assert len(triples) > 0, "传递闭包应包含 d010 → d004（通过 d005 中转）"

    print()


if __name__ == "__main__":
    print("\n🏥 宠物疾病诊断推理系统 · P3 测试（Jena 前向链）\n")

    try:
        test_kb_builder()
        test_local_reasoner()
        test_transitive()
        print("🎉 全部测试通过！\n")
        print("📌 提示：生产环境请使用 docker-compose up -d 启动 Fuseki，")
        print("   然后通过 reasoner.py 的 SPARQL 端点查询（推理内置到查询管线）。")
    except Exception as e:
        print(f"❌ 测试失败：{e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

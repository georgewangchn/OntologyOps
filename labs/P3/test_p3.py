#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3 完整流程测试（pytest，本地 rdflib 模式，无需 Docker/Fuseki）
用法：cd P3 && python -m pytest test_p3.py -v

说明：生产环境用 docker-compose up -d 启动 Fuseki 走 SPARQL 端点；
      本测试用 rdflib 本地模式模拟前向链推理，无需 Docker。
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_kb_builder():
    """知识库构建：生成 Turtle，含 d001 个体、物种三元组、传递闭包链数据。"""
    from kb_builder import build_kb
    path = build_kb()
    assert os.path.exists(path), "Turtle 文件未生成"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert ":d001" in content, "知识库缺少 d001 疾病个体"
    assert ":has_species" in content, "知识库缺少物种三元组"
    assert ":d010 :contain :d005" in content, "知识库缺少传递闭包链数据"


def test_local_reasoner():
    """前向链推理（rdflib 本地模式）：猫瘟首选且置信度 1.0，犬病被物种过滤。"""
    from local_reasoner import diagnose_local
    case = {
        "pet_type": "cat",
        "symptoms": ["发热", "呕吐", "腹泻"],
        "breed": "英短",
        "age": 2,
    }
    results, excluded = diagnose_local(case)
    assert len(results) > 0, "推理结果为空"
    assert results[0][0] == "猫瘟", f"首选诊断应为猫瘟，实际为 {results[0][0]}"
    assert abs(results[0][1] - 1.0) < 0.01, f"猫瘟置信度应为1.0，实际为 {results[0][1]}"
    result_names = [r[0] for r in results]
    assert "犬细小病毒" not in result_names, "犬细小病毒不应出现在猫的结果中"
    assert "犬感冒" not in result_names, "犬感冒不应出现在猫的结果中"
    assert "犬冠状病毒" not in result_names, "犬冠状病毒不应出现在猫的结果中"


def test_transitive_closure():
    """传递闭包（前向链预计算）：d010 → d004（通过 d005 中转）应存在。"""
    from local_reasoner import query_transitive_local, get_graph
    from rdflib import URIRef
    query_transitive_local()
    graph = get_graph()
    ns = "http://petbps.com/ontology/pet_disease#"
    d010 = URIRef(ns + "d010")
    d004 = URIRef(ns + "d004")
    contain = URIRef(ns + "contain")
    triples = list(graph.triples((d010, contain, d004)))
    assert len(triples) > 0, "传递闭包应包含 d010 → d004（通过 d005 中转）"

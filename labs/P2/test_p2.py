#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2 完整流程测试（pytest）
用法：cd P2 && python -m pytest test_p2.py -v
"""

import sys
import os
import json

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_kb_builder():
    """知识库构建：生成 Prolog 事实文件，含 d001 疾病与必要症状。"""
    from kb_builder import build_kb
    path = build_kb()
    assert os.path.exists(path), "知识库文件未生成"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "disease(d001," in content, "知识库缺少 d001 疾病事实"
    assert "necessary(d001," in content, "知识库缺少必要症状事实"


def test_reasoner():
    """Prolog 推理：猫瘟首选且确诊（置信度 1.0），犬病被物种过滤。"""
    from reasoner import load_knowledge_base, diagnose
    case = {
        "pet_type": "cat",
        "symptoms": ["发热", "呕吐", "腹泻"],
        "breed": "英短",
        "age": 2,
    }
    prolog = load_knowledge_base()
    results, excluded = diagnose(prolog, case)
    assert len(results) > 0, "推理结果为空"
    assert results[0][0] == "猫瘟", f"首选诊断应为猫瘟，实际为 {results[0][0]}"
    assert results[0][2], "猫瘟应为确诊（全匹配 + 无排除）"
    assert abs(results[0][1] - 1.0) < 0.01, f"猫瘟置信度应为1.0，实际为 {results[0][1]}"
    result_names = [r[0] for r in results]
    assert "犬细小病毒" not in result_names, "犬细小病毒不应出现在猫的结果中"
    assert "犬感冒" not in result_names, "犬感冒不应出现在猫的结果中"


def test_diagnosis_from_json():
    """诊断模块（从 JSON）：样本病例首选猫瘟，推理链解释非空。"""
    from reasoner import load_knowledge_base, diagnose, explain
    json_path = os.path.join(os.path.dirname(__file__), "..", "shared_data", "sample_case.json")
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)
    prolog = load_knowledge_base()
    results, excluded = diagnose(prolog, case)
    assert len(results) > 0, "JSON 病例推理结果为空"
    assert results[0][0] == "猫瘟", f"JSON 病例首选诊断应为猫瘟，实际为 {results[0][0]}"
    explanations = explain(prolog, case)
    assert len(explanations) > 0, "推理链解释为空"

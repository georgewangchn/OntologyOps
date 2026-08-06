#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P5 完整流程测试（pytest）
用法：cd P5 && python -m pytest test_p5.py -v

P5 为纯标准库实现（csv/json/os/math），测试仅需 pytest。
"""

import sys
import os
import json

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_kb_builder():
    """知识库构建：生成 bayesian_kb.json，含疾病先验与 CPT。"""
    from kb_builder import build_kb
    path = build_kb()
    assert os.path.exists(path), "贝叶斯知识库未生成"
    with open(path, encoding="utf-8") as f:
        kb = json.load(f)
    assert "diseases" in kb, "知识库缺少 diseases"
    assert len(kb["diseases"]) >= 10, f"疾病数量不足：{len(kb['diseases'])}"
    for d in kb["diseases"][:3]:
        assert "prior" in d, f"{d.get('name')} 缺少先验概率"
        assert "cpt" in d, f"{d.get('name')} 缺少条件概率表"


def test_reasoner():
    """贝叶斯推理：猫瘟后验概率最高（>0.5）。"""
    from reasoner import load_knowledge_base, diagnose
    case = {
        "pet_type": "cat",
        "symptoms": ["发热", "呕吐", "腹泻"],
        "breed": "英短",
        "age": 2,
    }
    kb = load_knowledge_base()
    results = diagnose(kb, case)
    assert len(results) > 0, "推理结果为空"
    # results: List[(name, confidence, level, disease_id)]
    assert results[0][0] == "猫瘟", f"首选诊断应为猫瘟，实际为 {results[0][0]}"
    assert results[0][1] > 0.5, f"猫瘟后验概率应>0.5，实际为 {results[0][1]:.4f}"


def test_diagnosis_from_json():
    """诊断模块（从 JSON）：样本病例首选猫瘟。"""
    from reasoner import load_knowledge_base, diagnose
    json_path = os.path.join(os.path.dirname(__file__), "..", "shared_data", "sample_case.json")
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)
    kb = load_knowledge_base()
    results = diagnose(kb, case)
    assert len(results) > 0, "JSON 病例推理结果为空"
    assert results[0][0] == "猫瘟", f"JSON 病例首选诊断应为猫瘟，实际为 {results[0][0]}"


def test_explain():
    """推理链解释：猫瘟含先验/后验/似然比，后验 > 先验。"""
    from reasoner import load_knowledge_base, explain
    case = {"pet_type": "cat", "symptoms": ["发热", "呕吐", "腹泻"]}
    kb = load_knowledge_base()
    explanations = explain(kb, case)
    assert len(explanations) > 0, "推理链解释为空"
    mao = [e for e in explanations if e["disease_name"] == "猫瘟"][0]
    assert mao["posterior"] > mao["prior"], "猫瘟后验应高于先验"
    assert mao["likelihood_ratio"] > 1, "猫瘟似然比应>1（症状支持）"

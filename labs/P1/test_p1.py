#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1 完整流程测试（pytest）
用法：cd P1 && python -m pytest test_p1.py -v
"""

import sys
import os
import json

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


@pytest.fixture(scope="module")
def built_ontology():
    """构建并保存本体（模块级复用）。"""
    from onto_builder import (
        create_ontology, load_diseases, load_symptoms,
        add_symptom_relations, save_ontology,
    )
    onto = create_ontology()
    onto = load_diseases(onto)
    onto = load_symptoms(onto)
    onto = add_symptom_relations(onto)
    path = save_ontology(onto)
    assert os.path.exists(path), "本体文件未生成"
    assert os.path.getsize(path) > 0, "本体文件为空"
    return onto


def test_ontology_has_diseases(built_ontology):
    """本体构建：疾病类数量 >= 10。"""
    onto = built_ontology
    disease_classes = [c for c in onto.classes() if c != onto.疾病]
    assert len(disease_classes) >= 10, f"疾病类数量不足：{len(disease_classes)}"


def test_reasoner(built_ontology):
    """推理机：猫瘟首选，置信度 0.99，犬病被物种过滤。"""
    from reasoner import diagnose
    onto = built_ontology
    case = {
        "pet_type": "cat",
        "symptoms": ["发热", "呕吐", "腹泻"],
        "breed": "英短",
        "age": 2,
    }
    results = diagnose(onto, case)
    assert len(results) > 0, "推理结果为空"
    top_name = results[0][0].label[0] if results[0][0].label else results[0][0].name
    assert top_name == "猫瘟", f"首选诊断应为猫瘟，实际为 {top_name}"
    assert abs(results[0][1] - 0.99) < 0.01, f"猫瘟置信度应为0.99，实际为 {results[0][1]}"
    result_names = [cls.label[0] if cls.label else cls.name for cls, _ in results]
    assert "犬细小病毒" not in result_names, "犬细小病毒不应出现在猫的结果中"
    assert "犬感冒" not in result_names, "犬感冒不应出现在猫的结果中"


def test_diagnosis_from_json():
    """诊断模块（从 JSON）：样本病例首选猫瘟。"""
    from reasoner import load_ontology, diagnose
    json_path = os.path.join(os.path.dirname(__file__), "..", "shared_data", "sample_case.json")
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)
    onto = load_ontology()
    results = diagnose(onto, case)
    assert len(results) > 0, "JSON 病例推理结果为空"
    top_name = results[0][0].label[0] if results[0][0].label else results[0][0].name
    assert top_name == "猫瘟", f"JSON 病例首选诊断应为猫瘟，实际为 {top_name}"

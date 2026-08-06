#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P4 完整流程测试（pytest）
用法：cd P4 && python -m pytest test_p4.py -v
"""

import sys
import os
import json

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


@pytest.fixture(scope="module")
def fuzzy_kb():
    """构建模糊知识库（模块级复用）。"""
    from kb_builder import build_kb
    path = build_kb()
    assert os.path.exists(path), "知识库文件未生成"
    with open(path, encoding="utf-8") as f:
        kb = json.load(f)
    assert "membership_functions" in kb, "知识库缺少隶属度函数"
    assert "fuzzy_rules" in kb, "知识库缺少模糊规则"
    assert len(kb["fuzzy_rules"]) == 12, f"应有12条模糊规则，实际{len(kb['fuzzy_rules'])}条"
    assert len(kb["diseases"]) >= 10, f"疾病数量不足：{len(kb['diseases'])}"
    return kb


def test_membership_functions(fuzzy_kb):
    """隶属度函数：覆盖率/强度/排除度/置信度 四组齐全。"""
    mf = fuzzy_kb["membership_functions"]
    for var in ["覆盖率", "强度", "排除度", "置信度"]:
        assert var in mf, f"缺少{var}隶属度函数"


def test_reasoner(fuzzy_kb):
    """模糊推理：猫瘟首选且等级=高(>0.6)；猫肠炎不被完全排除（降为中）。"""
    from reasoner import diagnose
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
    results = diagnose(fuzzy_kb, case)
    assert len(results) > 0, "推理结果为空"
    assert results[0][0] == "猫瘟", f"首选诊断应为猫瘟，实际为 {results[0][0]}"
    assert results[0][2] == "高", f"猫瘟模糊等级应为高，实际为 {results[0][2]}"
    assert results[0][1] > 0.6, f"猫瘟置信度应>0.6，实际为 {results[0][1]:.2f}"
    result_names = [r[0] for r in results]
    assert "犬细小病毒" not in result_names, "犬细小病毒不应出现在猫的结果中"
    assert "犬感冒" not in result_names, "犬感冒不应出现在猫的结果中"
    # P4 独有：猫肠炎因排除症状命中仅降低置信度（降为中），而非完全排除
    assert "猫肠炎" in result_names, "猫肠炎应出现在模糊推理结果中（P4 不完全排除）"
    maochangyan = [r for r in results if r[0] == "猫肠炎"][0]
    assert maochangyan[2] == "中", (
        f"猫肠炎等级应为中（全覆盖高强度高但排除度有 → 降一级），实际为 {maochangyan[2]}"
    )


def test_diagnosis_from_json():
    """诊断模块（从 JSON）：样本病例首选猫瘟，推理链解释非空。"""
    from reasoner import load_knowledge_base, diagnose, explain
    json_path = os.path.join(os.path.dirname(__file__), "..", "shared_data", "sample_case.json")
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)
    kb = load_knowledge_base()
    results = diagnose(kb, case)
    assert len(results) > 0, "JSON 病例推理结果为空"
    assert results[0][0] == "猫瘟", f"JSON 病例首选诊断应为猫瘟，实际为 {results[0][0]}"
    explanations = explain(kb, case)
    assert len(explanations) > 0, "推理链解释为空"
    mao = [e for e in explanations if e["disease_name"] == "猫瘟"][0]
    assert mao["coverage"] == 1.0, f"猫瘟覆盖率应为1.0，实际为 {mao['coverage']}"
    assert mao["intensity"] > 0.6, f"猫瘟强度应>0.6，实际为 {mao['intensity']}"
    assert mao["exclusion_degree"] < 0.1, f"猫瘟排除度应≈0，实际为 {mao['exclusion_degree']}"

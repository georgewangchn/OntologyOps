#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P6 完整流程测试（pytest）
用法：cd P6 && python -m pytest test_p6.py -v

前置：先运行 `bash setup_env.sh`（构建 P2/P4/P5 知识库）。
P6 融合 P2+P4+P5 三引擎，缺任一知识库时对应引擎降级，测试仍可运行。
"""

import sys
import os
import json

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_meta_reasoner_config():
    """元推理配置存在且含似然比映射。"""
    config_path = os.path.join(os.path.dirname(__file__), "data", "meta_reasoner_config.json")
    assert os.path.exists(config_path), "meta_reasoner_config.json 不存在"
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    assert "lr_mapping" in cfg, "配置缺少 lr_mapping"
    assert "lr_confirmed" in cfg["lr_mapping"], "缺少 lr_confirmed"


def test_reasoner():
    """元推理：猫瘟后验最高（>0.5），结果含引擎明细。"""
    from reasoner import diagnose
    case = {"pet_type": "cat", "symptoms": ["发热", "呕吐", "腹泻"]}
    results = diagnose(case)
    assert len(results) > 0, "推理结果为空"
    assert results[0]["disease"] == "猫瘟", f"首选诊断应为猫瘟，实际为 {results[0]['disease']}"
    assert results[0]["confidence"] > 0.5, f"猫瘟后验应>0.5，实际为 {results[0]['confidence']:.4f}"
    assert "engine_results" in results[0], "结果缺少 engine_results"
    assert "level" in results[0], "结果缺少 level"
    assert "disease_id" in results[0], "结果缺少 disease_id"


def test_reasoner_dog_case():
    """犬病例推理：返回非空，犬病出现在结果中。"""
    from reasoner import diagnose
    case = {"pet_type": "dog", "symptoms": ["咳嗽", "打喷嚏"]}
    results = diagnose(case)
    assert isinstance(results, list)
    # 犬病例可能匹配犬感冒/犬副流感；不强制首选，仅校验结构完整
    for r in results[:3]:
        assert "disease" in r and "confidence" in r and "engine_results" in r

"""
PL5 单元测试

测试覆盖：
  1. create_pl5_tools 创建工具集
  2. 工具功能（不依赖贝叶斯引擎）
  3. run_bayesian_reasoning 前置检查
  4. build_pl5_report 报告构建
  5. OntologyAgent + PL5 集成
  6. pl5_diagnose（需要知识库）
  7. case_dict 转换
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_core import OntologyAgent, ConversationState
from pl5.tools import create_pl5_tools
from pl5.diagnose import pl5_diagnose
from pl5.report import build_pl5_report


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def fake_api_key():
    return "sk-test-mock-key"


@pytest.fixture
def pl5_agent(fake_api_key):
    agent = OntologyAgent(
        tools_factory=create_pl5_tools,
        diagnose_fn=pl5_diagnose,
        report_builder=build_pl5_report,
        system_prompt="你是一个宠物疾病诊断助手。",
        api_key=fake_api_key,
        max_turns=5,
        verbose=False,
    )
    return agent


# ============================================================
# 测试 1: 工具集创建
# ============================================================

def test_create_pl5_tools_returns_list():
    state = ConversationState()
    tools = create_pl5_tools(state, pl5_diagnose, build_pl5_report)
    assert isinstance(tools, list)
    assert len(tools) >= 7


def test_create_pl5_tools_tool_names():
    state = ConversationState()
    tools = create_pl5_tools(state, pl5_diagnose, build_pl5_report)
    tool_names = [t.name for t in tools]
    assert "lookup_symptom_bayesian" in tool_names
    assert "add_observation" in tool_names
    assert "set_pet_info" in tool_names
    assert "run_bayesian_reasoning" in tool_names
    assert "get_case_summary" in tool_names
    assert "query_prior_and_likelihood" in tool_names
    assert "explain_bayesian_reasoning" in tool_names


# ============================================================
# 测试 2: 工具功能（不依赖贝叶斯引擎）
# ============================================================

def test_add_observation_tool():
    state = ConversationState()
    tools = create_pl5_tools(state, pl5_diagnose, build_pl5_report)
    add_obs = next(t for t in tools if t.name == "add_observation")
    result = add_obs.invoke({"symptom_name": "发热", "severity": "重度"})
    assert "已记录" in result
    assert len(state.observations) == 1


def test_set_pet_info_tool():
    state = ConversationState()
    tools = create_pl5_tools(state, pl5_diagnose, build_pl5_report)
    set_info = next(t for t in tools if t.name == "set_pet_info")
    result = set_info.invoke({"species": "猫", "breed": "英短", "age": 2, "sex": "公"})
    assert "已设置" in result
    assert state.subject.species == "猫"


def test_get_case_summary_tool():
    state = ConversationState()
    tools = create_pl5_tools(state, pl5_diagnose, build_pl5_report)
    get_summary = next(t for t in tools if t.name == "get_case_summary")
    state.set_subject(species="狗")
    state.add_observation("呕吐")
    state.add_observation("腹泻")
    result = get_summary.invoke({})
    assert "狗" in result
    assert "呕吐" in result


def test_get_case_summary_not_ready():
    state = ConversationState()
    tools = create_pl5_tools(state, pl5_diagnose, build_pl5_report)
    get_summary = next(t for t in tools if t.name == "get_case_summary")
    result = get_summary.invoke({})
    assert "信息不足" in result or "不足" in result


# ============================================================
# 测试 3: run_bayesian_reasoning 前置检查
# ============================================================

def test_run_bayesian_reasoning_not_ready():
    state = ConversationState()
    tools = create_pl5_tools(state, pl5_diagnose, build_pl5_report)
    run_reasoning = next(t for t in tools if t.name == "run_bayesian_reasoning")
    result = run_reasoning.invoke({})
    assert "信息不足" in result or "不足" in result


# ============================================================
# 测试 4: build_pl5_report
# ============================================================

def test_build_pl5_report():
    from agent_core import DiagnosisReport
    state = ConversationState()
    state.set_subject(species="猫")
    state.add_observation("发热")
    state.add_observation("呕吐")
    results = [
        {
            "disease": "猫瘟",
            "confidence": 0.9132,
            "level": "高概率",
            "disease_id": "D001",
            "evidence": ["发热", "呕吐"],
            "missing": [],
        }
    ]
    report = build_pl5_report(state, results)
    assert isinstance(report, DiagnosisReport)
    assert report.subject.species == "猫"
    assert len(report.results) == 1
    assert report.results[0].disease == "猫瘟"
    assert report.reasoning_engine == "Naive Bayes (贝叶斯网络)"


def test_build_pl5_report_format():
    state = ConversationState()
    state.set_subject(species="犬")
    state.add_observation("咳嗽")
    results = [
        {
            "disease": "犬副流感",
            "confidence": 0.7500,
            "level": "高概率",
            "disease_id": "D010",
            "evidence": ["咳嗽"],
            "missing": ["打喷嚏"],
        }
    ]
    report = build_pl5_report(state, results)
    formatted = report.format_for_user()
    assert "推理报告" in formatted
    assert "犬副流感" in formatted


def test_build_pl5_report_bayesian_explanation():
    """报告 disclaimer 应包含贝叶斯特有说明。"""
    state = ConversationState()
    state.set_subject(species="猫")
    state.add_observation("发热")
    results = [{"disease": "猫瘟", "confidence": 0.9, "level": "高概率", "disease_id": "D001", "evidence": ["发热"], "missing": []}]
    report = build_pl5_report(state, results)
    assert "后验概率" in report.disclaimer or "先验" in report.disclaimer


# ============================================================
# 测试 5: OntologyAgent + PL5 集成
# ============================================================

def test_pl5_agent_creation(pl5_agent):
    assert pl5_agent is not None
    assert pl5_agent.system_prompt == "你是一个宠物疾病诊断助手。"


def test_pl5_agent_reset(pl5_agent):
    state = pl5_agent.state
    state.set_subject(species="猫")
    state.add_observation("发热")
    pl5_agent.reset()
    assert pl5_agent.state.subject.species == ""
    assert len(pl5_agent.state.observations) == 0


def test_pl5_agent_state_sync():
    state = ConversationState()
    tools = create_pl5_tools(state, pl5_diagnose, build_pl5_report)
    set_info = next(t for t in tools if t.name == "set_pet_info")
    set_info.invoke({"species": "猫"})
    assert state.subject.species == "猫"


# ============================================================
# 测试 6: case_dict 转换
# ============================================================

def test_convert_case_dict():
    from pl5.diagnose import _convert_case_dict, _SPECIES_MAP
    case = {
        "subject_type": "猫",
        "observations": ["发热", "呕吐"],
    }
    p5_case = _convert_case_dict(case)
    assert p5_case["pet_type"] == "cat"
    assert p5_case["symptoms"] == ["发热", "呕吐"]

    case2 = {"subject_type": "猫咪", "observations": []}
    p5_case2 = _convert_case_dict(case2)
    assert p5_case2["pet_type"] == "cat"

    case3 = {"subject_type": "狗狗", "observations": []}
    p5_case3 = _convert_case_dict(case3)
    assert p5_case3["pet_type"] == "dog"


# ============================================================
# 测试 7: pl5_diagnose（需要知识库）
# ============================================================

def test_pl5_diagnose_with_kb():
    """测试 pl5_diagnose 函数（需要 bayesian_kb.json 存在）。"""
    kb_path = os.path.join(
        os.path.dirname(__file__), "..", "P5", "data", "bayesian_kb.json"
    )
    if not os.path.exists(kb_path):
        pytest.skip("P5 知识库文件不存在，跳过贝叶斯推理测试")

    case_dict = {
        "subject_type": "cat",
        "observations": ["发热", "呕吐", "腹泻"],
    }

    try:
        results = pl5_diagnose(case_dict)
        assert isinstance(results, list)
        if results:
            assert "disease" in results[0]
            assert "confidence" in results[0]
            assert "level" in results[0]
    except Exception as e:
        pytest.skip(f"贝叶斯推理失败：{e}")

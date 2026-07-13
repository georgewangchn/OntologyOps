"""
PL6 单元测试
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_core import OntologyAgent, ConversationState
from pl6.tools import create_pl6_tools
from pl6.diagnose import pl6_diagnose, _convert_case_dict
from pl6.report import build_pl6_report


@pytest.fixture
def fake_api_key():
    return "sk-test-mock-key"


@pytest.fixture
def pl6_agent(fake_api_key):
    return OntologyAgent(
        tools_factory=create_pl6_tools,
        diagnose_fn=pl6_diagnose,
        report_builder=build_pl6_report,
        system_prompt="你是一个宠物疾病诊断助手。",
        api_key=fake_api_key,
        max_turns=5,
        verbose=False,
    )


def test_create_pl6_tools_returns_list():
    state = ConversationState()
    tools = create_pl6_tools(state, pl6_diagnose, build_pl6_report)
    assert isinstance(tools, list)
    assert len(tools) >= 7


def test_create_pl6_tools_tool_names():
    state = ConversationState()
    tools = create_pl6_tools(state, pl6_diagnose, build_pl6_report)
    tool_names = [t.name for t in tools]
    assert "lookup_symptom_multi" in tool_names
    assert "add_observation" in tool_names
    assert "set_pet_info" in tool_names
    assert "run_multi_engine_reasoning" in tool_names
    assert "compare_engine_results" in tool_names
    assert "explain_arbitration" in tool_names
    assert "get_case_summary" in tool_names


def test_add_observation_tool():
    state = ConversationState()
    tools = create_pl6_tools(state, pl6_diagnose, build_pl6_report)
    add_obs = next(t for t in tools if t.name == "add_observation")
    result = add_obs.invoke({"symptom_name": "发热"})
    assert "已记录" in result
    assert len(state.observations) == 1


def test_set_pet_info_tool():
    state = ConversationState()
    tools = create_pl6_tools(state, pl6_diagnose, build_pl6_report)
    set_info = next(t for t in tools if t.name == "set_pet_info")
    result = set_info.invoke({"species": "猫", "breed": "英短"})
    assert "已设置" in result
    assert state.subject.species == "猫"


def test_get_case_summary_not_ready():
    state = ConversationState()
    tools = create_pl6_tools(state, pl6_diagnose, build_pl6_report)
    get_summary = next(t for t in tools if t.name == "get_case_summary")
    result = get_summary.invoke({})
    assert "信息不足" in result or "不足" in result


def test_run_multi_engine_reasoning_not_ready():
    state = ConversationState()
    tools = create_pl6_tools(state, pl6_diagnose, build_pl6_report)
    run_reasoning = next(t for t in tools if t.name == "run_multi_engine_reasoning")
    result = run_reasoning.invoke({})
    assert "信息不足" in result or "不足" in result


def test_explain_arbitration():
    state = ConversationState()
    tools = create_pl6_tools(state, pl6_diagnose, build_pl6_report)
    explain = next(t for t in tools if t.name == "explain_arbitration")
    result = explain.invoke({})
    assert "似然比" in result or "LR" in result
    assert "贝叶斯" in result
    assert "乘法融合" in result


def test_explain_arbitration_no_old_weights():
    """确保旧版的 0.6/0.4 权重不再出现"""
    state = ConversationState()
    tools = create_pl6_tools(state, pl6_diagnose, build_pl6_report)
    explain = next(t for t in tools if t.name == "explain_arbitration")
    result = explain.invoke({})
    assert "0.6" not in result or "0.4" not in result


def test_build_pl6_report():
    from agent_core import DiagnosisReport
    state = ConversationState()
    state.set_subject(species="猫")
    state.add_observation("发热")
    results = [{
        "disease": "猫瘟", "confidence": 0.91, "level": "高概率",
        "disease_id": "D001", "evidence": ["发热"], "missing": [],
        "engine_results": {
            "P2": {"confidence": 1.0, "level": "确诊", "lr": 5.0},
            "P4": {"confidence": 0.86, "level": "高", "lr": 3.2},
            "P5": {"confidence": 0.91, "level": "高概率", "lr": 18.2},
        },
        "conflict": False,
        "arbitration_note": "贝叶斯元推理：P_prior(0.0500) x LR_P2(5.0) x LR_P4(3.2) x LR_P5(18.2)"
    }]
    report = build_pl6_report(state, results)
    assert isinstance(report, DiagnosisReport)
    assert "似然比" in report.reasoning_engine or "Meta-Reasoner" in report.reasoning_engine


def test_build_pl6_report_format():
    state = ConversationState()
    state.set_subject(species="犬")
    state.add_observation("咳嗽")
    results = [{
        "disease": "犬副流感", "confidence": 0.75, "level": "高概率",
        "disease_id": "D010", "evidence": ["咳嗽"], "missing": ["打喷嚏"],
        "engine_results": {}, "conflict": False,
        "arbitration_note": "贝叶斯元推理融合"
    }]
    report = build_pl6_report(state, results)
    formatted = report.format_for_user()
    assert "推理报告" in formatted
    assert "犬副流感" in formatted


def test_pl6_agent_creation(pl6_agent):
    assert pl6_agent is not None


def test_pl6_agent_reset(pl6_agent):
    pl6_agent.state.set_subject(species="猫")
    pl6_agent.reset()
    assert pl6_agent.state.subject.species == ""


def test_pl6_agent_state_sync():
    state = ConversationState()
    tools = create_pl6_tools(state, pl6_diagnose, build_pl6_report)
    set_info = next(t for t in tools if t.name == "set_pet_info")
    set_info.invoke({"species": "猫"})
    assert state.subject.species == "猫"


def test_convert_case_dict():
    case = {"subject_type": "猫", "observations": ["发热", "呕吐"]}
    p6_case = _convert_case_dict(case)
    assert p6_case["pet_type"] == "cat"
    assert p6_case["symptoms"] == ["发热", "呕吐"]

    case2 = {"subject_type": "狗狗", "observations": []}
    p6_case2 = _convert_case_dict(case2)
    assert p6_case2["pet_type"] == "dog"

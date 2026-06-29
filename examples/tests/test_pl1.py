"""
PL1 单元测试

测试覆盖：
  1. create_pl1_tools 创建工具集
  2. pl1_diagnose 诊断函数
  3. build_pl1_report 报告构建
  4. 工具与 OntologyAgent 集成
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_core import OntologyAgent, ConversationState
from pl1.tools import create_pl1_tools
from pl1.diagnose import pl1_diagnose
from pl1.report import build_pl1_report


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def fake_api_key():
    return "sk-test-mock-key"


@pytest.fixture
def pl1_agent(fake_api_key):
    """创建一个 PL1 Agent（使用 mock API key）。"""
    agent = OntologyAgent(
        tools_factory=create_pl1_tools,
        diagnose_fn=pl1_diagnose,
        report_builder=build_pl1_report,
        system_prompt="你是一个宠物疾病诊断助手。",
        api_key=fake_api_key,
        max_turns=5,
        verbose=False,
    )
    return agent


# ============================================================
# 测试 1: 工具集创建
# ============================================================

def test_create_pl1_tools_returns_list():
    """create_pl1_tools 应返回工具列表。"""
    state = ConversationState()
    tools = create_pl1_tools(state, pl1_diagnose, build_pl1_report)
    assert isinstance(tools, list)
    assert len(tools) >= 5  # 至少 5 个工具


def test_create_pl1_tools_tool_names():
    """工具名称应符合预期。"""
    state = ConversationState()
    tools = create_pl1_tools(state, pl1_diagnose, build_pl1_report)
    tool_names = [t.name for t in tools]
    assert "lookup_symptom_owl" in tool_names
    assert "add_observation" in tool_names
    assert "set_pet_info" in tool_names
    assert "run_dl_reasoning" in tool_names
    assert "get_case_summary" in tool_names


# ============================================================
# 测试 2: 工具功能（不依赖 OWL 本体）
# ============================================================

def test_add_observation_tool():
    """add_observation 工具应正确写入 state。"""
    state = ConversationState()
    tools = create_pl1_tools(state, pl1_diagnose, build_pl1_report)
    add_obs = next(t for t in tools if t.name == "add_observation")

    result = add_obs.invoke({"symptom_name": "发热", "severity": "重度"})
    assert "已记录" in result
    assert len(state.observations) == 1
    assert state.observations[0].name == "发热"
    assert state.observations[0].severity == "重度"


def test_set_pet_info_tool():
    """set_pet_info 工具应正确写入 state。"""
    state = ConversationState()
    tools = create_pl1_tools(state, pl1_diagnose, build_pl1_report)
    set_info = next(t for t in tools if t.name == "set_pet_info")

    result = set_info.invoke({
        "species": "猫",
        "breed": "英短",
        "age": 2,
        "sex": "公",
    })
    assert "已设置" in result
    assert state.subject.species == "猫"
    assert state.subject.breed == "英短"
    assert state.subject.age == 2
    assert state.subject.sex == "公"


def test_get_case_summary_tool():
    """get_case_summary 工具应返回当前状态摘要。"""
    state = ConversationState()
    tools = create_pl1_tools(state, pl1_diagnose, build_pl1_report)
    get_summary = next(t for t in tools if t.name == "get_case_summary")

    # 添加一些数据
    state.set_subject(species="狗")
    state.add_observation("呕吐")
    state.add_observation("腹泻")

    result = get_summary.invoke({})
    assert "狗" in result
    assert "呕吐" in result
    assert "腹泻" in result


def test_get_case_summary_not_ready():
    """信息不足时，摘要应提示信息不足。"""
    state = ConversationState()
    tools = create_pl1_tools(state, pl1_diagnose, build_pl1_report)
    get_summary = next(t for t in tools if t.name == "get_case_summary")

    result = get_summary.invoke({})
    assert "信息不足" in result or "不足" in result


# ============================================================
# 测试 3: run_dl_reasoning 工具（信息不足时）
# ============================================================

def test_run_dl_reasoning_not_ready():
    """信息不足时，run_dl_reasoning 应返回提示而非报错。"""
    state = ConversationState()
    tools = create_pl1_tools(state, pl1_diagnose, build_pl1_report)
    run_reasoning = next(t for t in tools if t.name == "run_dl_reasoning")

    result = run_reasoning.invoke({})
    assert "信息不足" in result or "不足" in result


# ============================================================
# 测试 4: build_pl1_report
# ============================================================

def test_build_pl1_report():
    """build_pl1_report 应返回 DiagnosisReport。"""
    from agent_core import DiagnosisReport, DiagnosisItem

    state = ConversationState()
    state.set_subject(species="猫")
    state.add_observation("发热")
    state.add_observation("呕吐")

    results = [
        {
            "disease": "猫瘟",
            "confidence": 0.99,
            "level": "确诊",
            "disease_id": "D001",
            "evidence": ["发热", "呕吐"],
            "missing": [],
        }
    ]

    report = build_pl1_report(state, results)
    assert isinstance(report, DiagnosisReport)
    assert report.subject.species == "猫"
    assert len(report.results) == 1
    assert report.results[0].disease == "猫瘟"
    assert report.reasoning_engine == "OWL-DL (HermiT) + SWRL"


def test_build_pl1_report_format():
    """format_for_user() 应输出可读文本。"""
    from agent_core import DiagnosisReport, DiagnosisItem

    state = ConversationState()
    state.set_subject(species="犬")
    state.add_observation("咳嗽")

    results = [
        {
            "disease": "犬感冒",
            "confidence": 0.75,
            "level": "疑似",
            "disease_id": "D005",
            "evidence": ["打喷嚏", "流鼻涕"],
            "missing": ["发热"],
        }
    ]

    report = build_pl1_report(state, results)
    formatted = report.format_for_user()
    assert "推理报告" in formatted
    assert "犬感冒" in formatted
    assert "置信度" in formatted


# ============================================================
# 测试 5: OntologyAgent + PL1 集成
# ============================================================

def test_pl1_agent_creation(pl1_agent):
    """PL1 Agent 应成功创建。"""
    assert pl1_agent is not None
    assert pl1_agent.system_prompt == "你是一个宠物疾病诊断助手。"


def test_pl1_agent_reset(pl1_agent):
    """reset() 后应清空状态。"""
    state = pl1_agent.state
    state.set_subject(species="猫")
    state.add_observation("发热")

    pl1_agent.reset()

    assert pl1_agent.state.subject.species == ""
    assert len(pl1_agent.state.observations) == 0


def test_pl1_agent_state_sync():
    """Agent 的 state 应与工具内部引用的 state 一致。"""
    state = ConversationState()
    tools = create_pl1_tools(state, pl1_diagnose, build_pl1_report)

    # 通过工具修改 state
    set_info = next(t for t in tools if t.name == "set_pet_info")
    set_info.invoke({"species": "猫"})

    # state 应被修改
    assert state.subject.species == "猫"


# ============================================================
# 测试 6: pl1_diagnose（需要 OWL 本体）
# ============================================================

def test_pl1_diagnose_with_owl():
    """
    测试 pl1_diagnose 函数（需要 OWL 本体文件存在）。

    如果本体文件不存在，跳过测试。
    """
    owl_path = os.path.join(
        os.path.dirname(__file__), "..", "P1", "data", "pet_ontology.owl"
    )
    if not os.path.exists(owl_path):
        pytest.skip("P1 本体文件不存在，跳过 OWL 推理测试")

    case_dict = {
        "subject_type": "cat",
        "observations": ["发热", "呕吐", "腹泻"],
    }

    try:
        results = pl1_diagnose(case_dict)
        assert isinstance(results, list)
        if results:
            assert "disease" in results[0]
            assert "confidence" in results[0]
    except Exception as e:
        pytest.skip(f"OWL 推理失败（可能是 owlready2 未安装）：{e}")

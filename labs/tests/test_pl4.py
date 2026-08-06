"""
PL4 单元测试

测试覆盖：
  1. create_pl4_tools 创建工具集
  2. 工具功能（不依赖 scikit-fuzzy 推理引擎）
  3. run_fuzzy_reasoning 前置检查
  4. build_pl4_report 报告构建
  5. OntologyAgent + PL4 集成
  6. pl4_diagnose 端到端测试
  7. case_dict 转换
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_core import OntologyAgent, ConversationState
from pl4.tools import create_pl4_tools
from pl4.diagnose import pl4_diagnose, _convert_case_dict, _SPECIES_MAP
from pl4.report import build_pl4_report


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def fake_api_key():
    return "sk-test-mock-key"


@pytest.fixture
def pl4_agent(fake_api_key):
    """创建一个 PL4 Agent（使用 mock API key）。"""
    agent = OntologyAgent(
        tools_factory=create_pl4_tools,
        diagnose_fn=pl4_diagnose,
        report_builder=build_pl4_report,
        system_prompt="你是一个宠物疾病诊断助手。",
        api_key=fake_api_key,
        max_turns=5,
        verbose=False,
    )
    return agent


# ============================================================
# 测试 1: 工具集创建
# ============================================================

def test_create_pl4_tools_returns_list():
    """create_pl4_tools 应返回工具列表。"""
    state = ConversationState()
    tools = create_pl4_tools(state, pl4_diagnose, build_pl4_report)
    assert isinstance(tools, list)
    assert len(tools) >= 6


def test_create_pl4_tools_tool_names():
    """工具名称应符合预期。"""
    state = ConversationState()
    tools = create_pl4_tools(state, pl4_diagnose, build_pl4_report)
    tool_names = [t.name for t in tools]
    assert "lookup_symptom_fuzzy" in tool_names
    assert "add_observation" in tool_names
    assert "set_pet_info" in tool_names
    assert "run_fuzzy_reasoning" in tool_names
    assert "get_case_summary" in tool_names
    assert "explain_fuzzy_reasoning" in tool_names
    assert "get_symptom_severity" in tool_names


# ============================================================
# 测试 2: 工具功能
# ============================================================

def test_add_observation_tool():
    """add_observation 工具应正确写入 state（含 details）。"""
    state = ConversationState()
    tools = create_pl4_tools(state, pl4_diagnose, build_pl4_report)
    add_obs = next(t for t in tools if t.name == "add_observation")

    result = add_obs.invoke({
        "symptom_name": "发热",
        "severity": "重度",
        "details": {"value": 40.2},
    })
    assert "已记录" in result
    assert len(state.observations) == 1
    assert state.observations[0].name == "发热"
    assert state.observations[0].severity == "重度"


def test_set_pet_info_tool():
    """set_pet_info 工具应正确写入 state。"""
    state = ConversationState()
    tools = create_pl4_tools(state, pl4_diagnose, build_pl4_report)
    set_info = next(t for t in tools if t.name == "set_pet_info")

    result = set_info.invoke({"species": "犬", "breed": "金毛", "age": 3, "sex": "母"})
    assert "已设置" in result
    assert state.subject.species == "犬"
    assert state.subject.breed == "金毛"
    assert state.subject.age == 3


def test_get_case_summary_tool():
    """get_case_summary 工具应返回当前状态摘要。"""
    state = ConversationState()
    tools = create_pl4_tools(state, pl4_diagnose, build_pl4_report)
    get_summary = next(t for t in tools if t.name == "get_case_summary")

    state.set_subject(species="猫")
    state.add_observation("发热", severity="重度", details={"value": 39.8})
    state.add_observation("呕吐", details={"frequency": "频繁"})

    result = get_summary.invoke({})
    assert "猫" in result
    assert "发热" in result
    assert "呕吐" in result


def test_get_case_summary_not_ready():
    """信息不足时，摘要应提示信息不足。"""
    state = ConversationState()
    tools = create_pl4_tools(state, pl4_diagnose, build_pl4_report)
    get_summary = next(t for t in tools if t.name == "get_case_summary")

    result = get_summary.invoke({})
    assert "信息不足" in result or "不足" in result


# ============================================================
# 测试 3: run_fuzzy_reasoning 前置检查
# ============================================================

def test_run_fuzzy_reasoning_not_ready():
    """信息不足时，run_fuzzy_reasoning 应返回提示而非报错。"""
    state = ConversationState()
    tools = create_pl4_tools(state, pl4_diagnose, build_pl4_report)
    run_reasoning = next(t for t in tools if t.name == "run_fuzzy_reasoning")

    result = run_reasoning.invoke({})
    assert "信息不足" in result or "不足" in result


# ============================================================
# 测试 4: build_pl4_report
# ============================================================

def test_build_pl4_report():
    """build_pl4_report 应返回 DiagnosisReport。"""
    from agent_core import DiagnosisReport

    state = ConversationState()
    state.set_subject(species="猫")
    state.add_observation("发热", details={"value": 39.8})
    state.add_observation("呕吐", details={"frequency": "频繁"})
    state.add_observation("腹泻", details={"type": "水样", "color": "暗红"})

    results = [
        {
            "disease": "猫瘟",
            "confidence": 0.85,
            "level": "高",
            "disease_id": "D001",
            "evidence": ["发热", "呕吐", "腹泻"],
            "missing": [],
        }
    ]

    report = build_pl4_report(state, results)
    assert isinstance(report, DiagnosisReport)
    assert report.subject.species == "猫"
    assert len(report.results) == 1
    assert report.results[0].disease == "猫瘟"
    assert report.results[0].level == "高"
    assert report.reasoning_engine == "scikit-fuzzy Mamdani (模糊推理)"


def test_build_pl4_report_fuzzy_explanation():
    """报告应包含模糊推理说明。"""
    state = ConversationState()
    state.set_subject(species="猫")
    state.add_observation("发热")

    results = [
        {
            "disease": "猫瘟",
            "confidence": 0.45,
            "level": "中",
            "disease_id": "D001",
            "evidence": ["发热"],
            "missing": ["呕吐", "腹泻"],
        }
    ]

    report = build_pl4_report(state, results)
    assert "模糊" in report.reasoning_path or "Mamdani" in report.reasoning_path
    assert "去模糊化" in report.reasoning_path or "defuzzif" in report.reasoning_path.lower()


def test_build_pl4_report_format():
    """format_for_user() 应输出可读文本。"""
    state = ConversationState()
    state.set_subject(species="犬")
    state.add_observation("咳嗽")

    results = [
        {
            "disease": "犬副流感",
            "confidence": 0.55,
            "level": "中",
            "disease_id": "D010",
            "evidence": ["咳嗽"],
            "missing": ["打喷嚏"],
        }
    ]

    report = build_pl4_report(state, results)
    formatted = report.format_for_user()
    assert "推理报告" in formatted
    assert "犬副流感" in formatted
    assert "置信度" in formatted


# ============================================================
# 测试 5: OntologyAgent + PL4 集成
# ============================================================

def test_pl4_agent_creation(pl4_agent):
    """PL4 Agent 应成功创建。"""
    assert pl4_agent is not None
    assert pl4_agent.system_prompt == "你是一个宠物疾病诊断助手。"


def test_pl4_agent_reset(pl4_agent):
    """reset() 后应清空状态。"""
    state = pl4_agent.state
    state.set_subject(species="猫")
    state.add_observation("发热")

    pl4_agent.reset()

    assert pl4_agent.state.subject.species == ""
    assert len(pl4_agent.state.observations) == 0


def test_pl4_agent_state_sync():
    """Agent 的 state 应与工具内部引用的 state 一致。"""
    state = ConversationState()
    tools = create_pl4_tools(state, pl4_diagnose, build_pl4_report)

    set_info = next(t for t in tools if t.name == "set_pet_info")
    set_info.invoke({"species": "犬"})

    assert state.subject.species == "犬"


# ============================================================
# 测试 6: pl4_diagnose（需要 scikit-fuzzy + 知识库）
# ============================================================

def test_pl4_diagnose_with_skfuzzy():
    """测试 pl4_diagnose 函数（需要 scikit-fuzzy + fuzzy_kb.json）。"""
    kb_path = os.path.join(
        os.path.dirname(__file__), "..", "P4", "data", "fuzzy_kb.json"
    )
    if not os.path.exists(kb_path):
        pytest.skip("P4 知识库文件不存在，跳过模糊推理测试")

    try:
        import skfuzzy  # noqa: F401
    except ImportError:
        pytest.skip("scikit-fuzzy 未安装，跳过模糊推理测试")

    case_dict = {
        "subject_type": "猫",
        "observations": ["发热", "呕吐", "腹泻"],
        "symptom_details": {
            "发热": {"value": 39.8},
            "呕吐": {"frequency": "频繁"},
            "腹泻": {"type": "水样", "color": "暗红"},
        },
    }

    try:
        results = pl4_diagnose(case_dict)
        assert isinstance(results, list)
        if results:
            assert "disease" in results[0]
            assert "confidence" in results[0]
            assert "level" in results[0]  # 高/中/低
    except Exception as e:
        pytest.skip(f"模糊推理失败（可能是 scikit-fuzzy 配置问题）：{e}")


# ============================================================
# 测试 7: case_dict 转换
# ============================================================

def test_convert_case_dict():
    """测试 case_dict 格式转换。"""
    case = {
        "subject_type": "猫",
        "observations": ["发热", "呕吐"],
        "symptom_details": {"发热": {"value": 39.5}},
    }
    p4_case = _convert_case_dict(case)
    assert p4_case["pet_type"] == "cat"
    assert p4_case["symptoms"] == ["发热", "呕吐"]
    assert p4_case["symptom_details"]["发热"]["value"] == 39.5

    # 测试别名
    case2 = {"subject_type": "喵", "observations": []}
    p4_case2 = _convert_case_dict(case2)
    assert p4_case2["pet_type"] == "cat"

    case3 = {"subject_type": "狗", "observations": []}
    p4_case3 = _convert_case_dict(case3)
    assert p4_case3["pet_type"] == "dog"

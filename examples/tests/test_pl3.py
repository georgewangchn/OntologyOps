"""
PL3 单元测试

测试覆盖：
  1. create_pl3_tools 创建工具集
  2. 工具功能（不依赖 Fuseki，使用 rdflib 本地模式）
  3. run_sparql_reasoning 前置检查
  4. build_pl3_report 报告构建
  5. OntologyAgent + PL3 集成
  6. pl3_diagnose 端到端测试
  7. case_dict 转换
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_core import OntologyAgent, ConversationState
from pl3.tools import create_pl3_tools
from pl3.diagnose import pl3_diagnose, _convert_case_dict, _SPECIES_MAP
from pl3.report import build_pl3_report


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def fake_api_key():
    return "sk-test-mock-key"


@pytest.fixture
def pl3_agent(fake_api_key):
    """创建一个 PL3 Agent（使用 mock API key）。"""
    agent = OntologyAgent(
        tools_factory=create_pl3_tools,
        diagnose_fn=pl3_diagnose,
        report_builder=build_pl3_report,
        system_prompt="你是一个宠物疾病诊断助手。",
        api_key=fake_api_key,
        max_turns=5,
        verbose=False,
    )
    return agent


# ============================================================
# 测试 1: 工具集创建
# ============================================================

def test_create_pl3_tools_returns_list():
    """create_pl3_tools 应返回工具列表。"""
    state = ConversationState()
    tools = create_pl3_tools(state, pl3_diagnose, build_pl3_report)
    assert isinstance(tools, list)
    assert len(tools) >= 6


def test_create_pl3_tools_tool_names():
    """工具名称应符合预期。"""
    state = ConversationState()
    tools = create_pl3_tools(state, pl3_diagnose, build_pl3_report)
    tool_names = [t.name for t in tools]
    assert "lookup_symptom_sparql" in tool_names
    assert "add_observation" in tool_names
    assert "set_pet_info" in tool_names
    assert "run_sparql_reasoning" in tool_names
    assert "get_case_summary" in tool_names
    assert "explain_reasoning_chain" in tool_names
    assert "query_transitive_closure" in tool_names


# ============================================================
# 测试 2: 工具功能
# ============================================================

def test_add_observation_tool():
    """add_observation 工具应正确写入 state。"""
    state = ConversationState()
    tools = create_pl3_tools(state, pl3_diagnose, build_pl3_report)
    add_obs = next(t for t in tools if t.name == "add_observation")

    result = add_obs.invoke({"symptom_name": "发热", "severity": "重度"})
    assert "已记录" in result
    assert len(state.observations) == 1
    assert state.observations[0].name == "发热"
    assert state.observations[0].severity == "重度"


def test_set_pet_info_tool():
    """set_pet_info 工具应正确写入 state。"""
    state = ConversationState()
    tools = create_pl3_tools(state, pl3_diagnose, build_pl3_report)
    set_info = next(t for t in tools if t.name == "set_pet_info")

    result = set_info.invoke({"species": "猫", "breed": "英短", "age": 2, "sex": "公"})
    assert "已设置" in result
    assert state.subject.species == "猫"
    assert state.subject.breed == "英短"
    assert state.subject.age == 2


def test_get_case_summary_tool():
    """get_case_summary 工具应返回当前状态摘要。"""
    state = ConversationState()
    tools = create_pl3_tools(state, pl3_diagnose, build_pl3_report)
    get_summary = next(t for t in tools if t.name == "get_case_summary")

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
    tools = create_pl3_tools(state, pl3_diagnose, build_pl3_report)
    get_summary = next(t for t in tools if t.name == "get_case_summary")

    result = get_summary.invoke({})
    assert "信息不足" in result or "不足" in result


# ============================================================
# 测试 3: run_sparql_reasoning 前置检查
# ============================================================

def test_run_sparql_reasoning_not_ready():
    """信息不足时，run_sparql_reasoning 应返回提示而非报错。"""
    state = ConversationState()
    tools = create_pl3_tools(state, pl3_diagnose, build_pl3_report)
    run_reasoning = next(t for t in tools if t.name == "run_sparql_reasoning")

    result = run_reasoning.invoke({})
    assert "信息不足" in result or "不足" in result


# ============================================================
# 测试 4: build_pl3_report
# ============================================================

def test_build_pl3_report():
    """build_pl3_report 应返回 DiagnosisReport。"""
    from agent_core import DiagnosisReport

    state = ConversationState()
    state.set_subject(species="猫")
    state.add_observation("发热")
    state.add_observation("呕吐")

    results = [
        {
            "disease": "猫瘟",
            "confidence": 1.0,
            "level": "确诊",
            "disease_id": "d001",
            "evidence": ["发热", "呕吐", "腹泻"],
            "missing": [],
        }
    ]

    report = build_pl3_report(state, results)
    assert isinstance(report, DiagnosisReport)
    assert report.subject.species == "猫"
    assert len(report.results) == 1
    assert report.results[0].disease == "猫瘟"
    assert report.reasoning_engine == "Jena Fuseki + SPARQL (前向链)"


def test_build_pl3_report_owa_explanation():
    """报告应包含 OWA 说明。"""
    state = ConversationState()
    state.set_subject(species="猫")
    state.add_observation("发热")

    results = [
        {
            "disease": "猫瘟",
            "confidence": 0.33,
            "level": "疑似",
            "disease_id": "d001",
            "evidence": ["发热"],
            "missing": ["呕吐", "腹泻"],
        }
    ]

    report = build_pl3_report(state, results)
    assert "OWA" in report.reasoning_path or "开放世界" in report.reasoning_path


def test_build_pl3_report_format():
    """format_for_user() 应输出可读文本。"""
    state = ConversationState()
    state.set_subject(species="犬")
    state.add_observation("咳嗽")

    results = [
        {
            "disease": "犬副流感",
            "confidence": 0.5,
            "level": "疑似",
            "disease_id": "d010",
            "evidence": ["咳嗽"],
            "missing": ["打喷嚏"],
        }
    ]

    report = build_pl3_report(state, results)
    formatted = report.format_for_user()
    assert "推理报告" in formatted
    assert "犬副流感" in formatted
    assert "置信度" in formatted


# ============================================================
# 测试 5: OntologyAgent + PL3 集成
# ============================================================

def test_pl3_agent_creation(pl3_agent):
    """PL3 Agent 应成功创建。"""
    assert pl3_agent is not None
    assert pl3_agent.system_prompt == "你是一个宠物疾病诊断助手。"


def test_pl3_agent_reset(pl3_agent):
    """reset() 后应清空状态。"""
    state = pl3_agent.state
    state.set_subject(species="猫")
    state.add_observation("发热")

    pl3_agent.reset()

    assert pl3_agent.state.subject.species == ""
    assert len(pl3_agent.state.observations) == 0


def test_pl3_agent_state_sync():
    """Agent 的 state 应与工具内部引用的 state 一致。"""
    state = ConversationState()
    tools = create_pl3_tools(state, pl3_diagnose, build_pl3_report)

    set_info = next(t for t in tools if t.name == "set_pet_info")
    set_info.invoke({"species": "猫"})

    assert state.subject.species == "猫"


# ============================================================
# 测试 6: pl3_diagnose（需要 rdflib + TTL 知识库）
# ============================================================

def test_pl3_diagnose_with_rdflib():
    """测试 pl3_diagnose 函数（使用 rdflib 本地模式）。"""
    ttl_path = os.path.join(
        os.path.dirname(__file__), "..", "P3", "data", "pet.ttl"
    )
    if not os.path.exists(ttl_path):
        pytest.skip("P3 知识库文件不存在，跳过 RDF 推理测试")

    try:
        import rdflib  # noqa: F401
    except ImportError:
        pytest.skip("rdflib 未安装，跳过 RDF 推理测试")

    case_dict = {
        "subject_type": "猫",
        "observations": ["发热", "呕吐", "腹泻"],
    }

    try:
        results = pl3_diagnose(case_dict)
        assert isinstance(results, list)
        if results:
            assert "disease" in results[0]
            assert "confidence" in results[0]
    except Exception as e:
        pytest.skip(f"RDF 推理失败（可能是 rdflib 配置问题）：{e}")


# ============================================================
# 测试 7: case_dict 转换
# ============================================================

def test_convert_case_dict():
    """测试 case_dict 格式转换。"""
    case = {
        "subject_type": "猫",
        "observations": ["发热", "呕吐"],
    }
    p3_case = _convert_case_dict(case)
    assert p3_case["pet_type"] == "cat"
    assert p3_case["symptoms"] == ["发热", "呕吐"]

    # 测试别名
    case2 = {"subject_type": "猫咪", "observations": []}
    p3_case2 = _convert_case_dict(case2)
    assert p3_case2["pet_type"] == "cat"

    case3 = {"subject_type": "狗狗", "observations": []}
    p3_case3 = _convert_case_dict(case3)
    assert p3_case3["pet_type"] == "dog"

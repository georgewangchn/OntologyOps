"""
agent_core 单元测试

测试覆盖：
  1. 状态同步 —— 工具写入的 state 与 Agent 读取的是同一个对象
  2. 对话连续性 —— 多轮 chat() 保留完整上下文
  3. reset() —— 清空状态并重建 Agent
  4. API key 校验 —— 空 key 抛异常
  5. tools_factory 集成 —— 工具的 diagnose_fn / report_builder 一致
  6. 优雅降级 —— _force_diagnosis 行为
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core import (
    OntologyAgent,
    ConversationState,
    DiagnosisReport,
    DiagnosisItem,
    SubjectInfo,
    ObservationEntry,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def fake_api_key():
    return "sk-test-mock-key"


@pytest.fixture
def diagnose_fn():
    def _diagnose(case_dict):
        return [
            {"disease": "普通感冒", "confidence": 0.85, "level": "确诊"},
            {"disease": "支气管炎", "confidence": 0.40, "level": "疑似"},
        ]
    return _diagnose


@pytest.fixture
def report_builder():
    def _builder(state, results):
        items = []
        for r in results:
            items.append(DiagnosisItem(
                disease=r["disease"],
                confidence=r["confidence"],
                level=r.get("level", ""),
            ))
        return DiagnosisReport(
            subject=state.subject,
            observations=state.observations,
            results=items,
            reasoning_engine="test",
            reasoning_path="mock reasoning path",
            disclaimer="测试免责声明",
        )
    return _builder


@pytest.fixture
def system_prompt():
    return "你是一个测试助手，用于验证 agent_core 行为。"


@pytest.fixture
def tools_factory():
    """创建一个工具集，其中 run_diagnosis 直接调用引擎（用于测试状态同步）。"""
    from langchain_core.tools import tool

    def _factory(state, diagnose_fn, report_builder):
        @tool
        def set_info(key: str, value: str = "") -> str:
            """设置测试信息。"""
            state.set_subject(species=key, breed=value)
            return f"已设置: {key}"

        @tool
        def add_obs(name: str) -> str:
            """添加观测。"""
            state.add_observation(name)
            return f"已记录: {name}"

        @tool
        def get_state() -> str:
            """查看状态。"""
            import json
            return json.dumps({
                "species": state.subject.species,
                "observations": [s.name for s in state.observations],
                "ready": state.is_ready_for_reasoning(),
            }, ensure_ascii=False)

        @tool
        def run() -> str:
            """直接执行推理。"""
            if not state.is_ready_for_reasoning():
                return "信息不足"
            case = state.to_case_dict()
            results = diagnose_fn(case)
            report = report_builder(state, results)
            return report.format_for_user()

        return [set_info, add_obs, get_state, run]

    return _factory


def make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, api_key="sk-test-key"):
    return OntologyAgent(
        tools_factory=tools_factory,
        diagnose_fn=diagnose_fn,
        report_builder=report_builder,
        system_prompt=system_prompt,
        api_key=api_key,
        max_turns=5,
        verbose=False,
    )


# ============================================================
# P0: 状态同步
# ============================================================

def test_state_same_object_after_init(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    """Agent 创建后，tools 内部的 state 就是 self.state（同一对象）"""
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)
    original_id = id(agent.state)

    # 通过 _rebuild 重建后，state 是新对象但 tools 也捕获新对象
    agent._rebuild()
    new_id = id(agent.state)
    assert new_id != original_id, "rebuild 应创建新 state 对象"


def test_tools_write_to_agent_state(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    """工具写入的数据能通过 agent.state 读取（验证单一状态源）"""
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)

    # 手动调用工具（模拟 LangGraph 的 tool calling）
    tools = agent.tools_factory(agent.state, agent.diagnose_fn, agent.report_builder)
    set_info_tool = next(t for t in tools if t.name == "set_info")
    add_obs_tool = next(t for t in tools if t.name == "add_obs")

    set_info_tool.invoke({"key": "猫", "value": "英短"})
    add_obs_tool.invoke({"name": "发热"})
    add_obs_tool.invoke({"name": "呕吐"})

    # 验证 agent.state 和 tools 看到的是同一份数据
    assert agent.state.subject.species == "猫"
    assert agent.state.subject.breed == "英短"
    assert len(agent.state.observations) == 2
    assert agent.state.observations[0].name == "发热"
    assert agent.state.observations[1].name == "呕吐"
    assert agent.state.is_ready_for_reasoning()


# ============================================================
# P0: 对话连续性
# ============================================================

def test_messages_recorded(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    """add_user_message 和 add_assistant_message 正常记录"""
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)

    agent.state.add_user_message("你好")
    agent.state.add_assistant_message("你好，有什么可以帮你的？")

    assert len(agent.state.messages) == 2
    assert agent.state.messages[0]["role"] == "user"
    assert agent.state.messages[1]["role"] == "assistant"
    assert agent.state.turn_count == 1


def test_messages_trimmed(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    """消息超过 max_messages 时自动裁剪"""
    state = ConversationState(max_messages=5)
    for i in range(10):
        state.add_user_message(f"消息 {i}")
    assert len(state.messages) == 5
    assert state.messages[0]["content"] == "消息 5"


# ============================================================
# reset()
# ============================================================

def test_reset_clears_state(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    """reset() 清空 state 并重建 agent"""
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)

    tools = agent.tools_factory(agent.state, agent.diagnose_fn, agent.report_builder)
    set_info_tool = next(t for t in tools if t.name == "set_info")
    add_obs_tool = next(t for t in tools if t.name == "add_obs")

    set_info_tool.invoke({"key": "狗"})
    add_obs_tool.invoke({"name": "咳嗽"})

    assert agent.state.subject.species == "狗"

    agent.reset()

    assert agent.state.subject.species == ""
    assert len(agent.state.observations) == 0
    assert agent.state.turn_count == 0
    assert len(agent.state.messages) == 0


def test_reset_new_tools_write_to_new_state(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    """reset 后，工具写入的是新的 state"""
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)

    # 第一轮
    tools = agent.tools_factory(agent.state, agent.diagnose_fn, agent.report_builder)
    set_info_tool = next(t for t in tools if t.name == "set_info")
    set_info_tool.invoke({"key": "狗"})

    agent.reset()

    # reset 后 tools 是新的（通过 _rebuild 创建）
    new_tools = agent.tools_factory(agent.state, agent.diagnose_fn, agent.report_builder)
    new_set_info = next(t for t in new_tools if t.name == "set_info")
    new_set_info.invoke({"key": "猫"})

    assert agent.state.subject.species == "猫", "reset后工具应写入新state"


# ============================================================
# API key 校验
# ============================================================

def test_missing_api_key_raises(tools_factory, diagnose_fn, report_builder, system_prompt):
    """空 api_key 应抛出 ValueError"""
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OntologyAgent(
            tools_factory=tools_factory,
            diagnose_fn=diagnose_fn,
            report_builder=report_builder,
            system_prompt=system_prompt,
            api_key="",
        )


# ============================================================
# tools_factory 集成
# ============================================================

def test_tools_factory_receives_correct_params(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    """_rebuild 传递给 tools_factory 的参数与 agent 一致"""
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)

    tools = agent.tools_factory(agent.state, agent.diagnose_fn, agent.report_builder)
    tool_names = [t.name for t in tools]
    assert "set_info" in tool_names
    assert "add_obs" in tool_names
    assert "get_state" in tool_names
    assert "run" in tool_names


# ============================================================
# 优雅降级
# ============================================================

def test_force_diagnosis_when_ready(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    """信息足够时 _force_diagnosis 应返回报告"""
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)

    agent.state.set_subject(species="猫")
    agent.state.add_observation("发热")
    agent.state.add_observation("呕吐")

    result = agent._force_diagnosis()
    assert "推理报告" in result
    assert "普通感冒" in result
    assert "测试免责声明" in result


def test_force_diagnosis_when_not_ready(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    """信息不足时 _force_diagnosis 应返回提示"""
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)

    result = agent._force_diagnosis()
    assert "信息不足" in result
    assert "重新开始" in result


# ============================================================
# ConversationState
# ============================================================

def test_to_case_dict(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)

    agent.state.set_subject(species="猫", breed="英短", age=12, sex="公")
    agent.state.add_observation("发热", severity="重度", details={"体温": 40.2})
    agent.state.add_observation("呕吐")

    case = agent.state.to_case_dict()
    assert case["subject_type"] == "猫"
    assert case["breed"] == "英短"
    assert case["age"] == 12
    assert "发热" in case["observations"]
    assert "呕吐" in case["observations"]
    assert "observation_details" in case
    assert case["observation_details"]["发热"]["severity"] == "重度"
    assert case["observation_details"]["发热"]["体温"] == 40.2


def test_observation_dedup(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)

    agent.state.add_observation("发热", severity="轻度")
    agent.state.add_observation("发热", severity="重度")

    assert len(agent.state.observations) == 1
    assert agent.state.observations[0].severity == "重度"


def test_should_clarify(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key):
    agent = make_agent(tools_factory, diagnose_fn, report_builder, system_prompt, fake_api_key)

    # 无物种 → 需要追问
    assert agent.state.should_clarify()

    agent.state.set_subject(species="猫")
    # 有物种但观测不足 → 需要追问
    assert agent.state.should_clarify()

    agent.state.add_observation("发热")
    agent.state.add_observation("呕吐")
    # 信息足够 → 不需要追问
    assert not agent.state.should_clarify()
    assert agent.state.is_ready_for_reasoning()


# ============================================================
# DiagnosisReport
# ============================================================

def test_report_top_diagnosis():
    report = DiagnosisReport(
        results=[
            DiagnosisItem(disease="A", confidence=0.5, level="确诊"),
            DiagnosisItem(disease="B", confidence=0.9, level="疑似"),
            DiagnosisItem(disease="C", confidence=0.3, level="排除"),
        ]
    )
    top = report.top_diagnosis()
    assert top is not None
    assert top.disease == "B"


def test_report_top_diagnosis_all_excluded():
    report = DiagnosisReport(
        results=[
            DiagnosisItem(disease="C", confidence=0.3, level="排除"),
        ]
    )
    assert report.top_diagnosis() is None


def test_report_to_dict():
    report = DiagnosisReport(
        subject=SubjectInfo(species="猫"),
        observations=[ObservationEntry(name="发热")],
        results=[DiagnosisItem(disease="感冒", confidence=0.8, level="确诊")],
        reasoning_engine="OWL",
        reasoning_path="发热 → 感冒",
        disclaimer="测试免责",
    )
    d = report.to_dict()
    assert "猫" in d["subject"]
    assert d["observations"] == ["发热"]
    assert d["reasoning_engine"] == "OWL"
    assert len(d["results"]) == 1

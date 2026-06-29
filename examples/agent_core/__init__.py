"""
Agent Core —— 基于 LangGraph 的通用本体推理 Agent 框架

核心组件：
  - OntologyAgent       — 基于 langchain.agents.create_react_agent
  - ConversationState   — 对话状态管理（领域无关）
  - DiagnosisReport     — 统一推理报告结构
  - SubjectInfo        — 领域对象信息（通用）
  - ObservationEntry   — 观测记录（通用）
  - Tool / ToolRegistry — 轻量工具注册（供 PL* 模块使用）

换场景 = 换 tools_factory + diagnose_fn + report_builder + system_prompt。
Agent 核心不动。

Usage:
    from agent_core import OntologyAgent

    agent = OntologyAgent(
        tools_factory=create_pl_tools,        # (state, diagnose_fn, report_builder) -> [Tool]
        diagnose_fn=domain_diagnose,          # (case_dict) -> results
        report_builder=build_domain_report,    # (state, results) -> DiagnosisReport
        system_prompt="你是一个领域推理助手...",  # 领域角色定义
    )
    response = agent.chat("问题描述…")
"""

from agent_core.agent import OntologyAgent
from agent_core.tool_registry import Tool, ToolRegistry
from agent_core.conversation import (
    ConversationState,
    DiagnosisReport,
    DiagnosisItem,
    SubjectInfo,
    ObservationEntry,
)

__all__ = [
    "OntologyAgent",
    "Tool",
    "ToolRegistry",
    "ConversationState",
    "DiagnosisReport",
    "DiagnosisItem",
    "SubjectInfo",
    "ObservationEntry",
]

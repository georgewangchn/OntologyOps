"""
Ontology Agent 核心（基于 LangGraph）

基于 langchain.agents.create_react_agent 的通用 Agent 框架。
核心职责：
  1. 管理对话循环（Think → Act → Observe）
  2. 通过注入的 tools 与领域推理引擎交互
  3. 将推理结果以统一的 DiagnosisReport 格式返回

LangGraph 负责：
  - ReAct 循环调度
  - 工具调用与结果路由
  - 多轮交互的递归控制

agent_core 只提供 Agent 循环 + 状态管理，不内置任何领域工具。
换场景 = 换 tools_factory + diagnose_fn + report_builder + system_prompt。
"""

import logging
import os
from typing import Callable, Optional

from langchain.agents import create_agent as create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
)

from agent_core.conversation import ConversationState

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
DEFAULT_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# ToolsFactory: (state, diagnose_fn, report_builder) -> list of LangChain Tool
ToolsFactory = Callable[..., list]


class OntologyAgent:
    """
    基于 LangGraph 的通用本体推理 Agent。

    Agent 核心是领域无关的 —— 它只管理对话和工具调度。
    领域知识通过 tools_factory + diagnose_fn + report_builder + system_prompt 注入。

    Usage:
        agent = OntologyAgent(
            tools_factory=create_pl1_tools,
            diagnose_fn=p1_diagnose,
            report_builder=build_p1_report,
            system_prompt="你是一个兽医诊断助手...",
        )
        response = agent.chat("猫咪发烧了，怎么办？")
    """

    def __init__(
        self,
        tools_factory: ToolsFactory,
        diagnose_fn: Callable,
        report_builder: Callable,
        system_prompt: str,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str = DEFAULT_API_KEY,
        base_url: str = DEFAULT_BASE_URL,
        max_turns: int = 15,
        verbose: bool = False,
    ):
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY 未设置。请通过参数 api_key 传入或设置环境变量。"
            )

        self.tools_factory = tools_factory
        self.diagnose_fn = diagnose_fn
        self.report_builder = report_builder
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.verbose = verbose

        self.model = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,
        )

        self._rebuild()

    # ============================================================
    # 公共接口
    # ============================================================

    def chat(self, user_message: str) -> str:
        """
        处理一条用户消息，返回 Agent 的回复文本。

        每次调用保持完整对话上下文 —— Agent 知道之前说过什么、
        调用过什么工具、得到过什么结果。
        """
        self.state.add_user_message(user_message)
        messages = self._build_messages()

        try:
            result = self._agent.invoke(
                {"messages": messages},
                config={"recursion_limit": self.max_turns * 3},
            )

            last_msg = result["messages"][-1]
            content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

            if content:
                self.state.add_assistant_message(content)
                return content

            return self._force_diagnosis()

        except Exception as e:
            logger.error(f"Agent invoke failed: {e}")
            return self._force_diagnosis()

    def reset(self):
        """清空对话状态，重建 Agent（新会话重新开始）。"""
        self._rebuild()

    # ============================================================
    # 内部
    # ============================================================

    def _rebuild(self):
        """
        创建/重建 state 和 LangGraph agent。

        顺序至关重要：先创建 state，再用它构建 tools，
        确保工具闭包捕获的 state 与 Agent 读取的是同一个对象。
        reset() 时也走这里，保证 state 与 tools 始终同步。
        """
        self.state = ConversationState()
        tools = self.tools_factory(
            self.state,
            self.diagnose_fn,
            self.report_builder,
        )
        self._agent = create_react_agent(
            model=self.model,
            tools=tools,
        )

    def _build_messages(self) -> list:
        """
        构建发送给 LangGraph 的完整消息列表。

        包含 system prompt + 完整对话历史（user + assistant）。
        LangGraph 内部产生的 ToolMessage 不跨轮保留——
        当前设计假设短对话（3-5轮）中 assistant 的文本摘要足以传递工具结果。
        如需长链条推理，应在此处重建 ToolMessage 历史。
        """
        messages = [SystemMessage(content=self.system_prompt)]

        for msg in self.state.messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not content:
                continue
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        if self.verbose:
            logger.info(
                f"Messages: {len(messages)} total "
                f"(system + {self.state.turn_count} turns history)"
            )

        return messages

    def _force_diagnosis(self) -> str:
        """
        LangGraph 循环超限或异常时的安全兜底。

        直接绕过 LLM 调用诊断引擎，基于当前 state 中已收集的信息。
        """
        if self.state.is_ready_for_reasoning():
            case_dict = self.state.to_case_dict()
            try:
                results = self.diagnose_fn(case_dict)
            except Exception as e:
                return f"推理引擎出错：{e}"

            report = self.report_builder(self.state, results)
            self.state.current_report = report
            return report.format_for_user()

        return (
            "抱歉，当前信息不足以做出可靠推理。请提供更多信息后重试。\n"
            "你也可以输入「重新开始」清空当前会话。"
        )

"""
工具注册表（Tool Registry）

管理域专用工具的注册、查询和分组。

与旧版本的区别：
  - 不再需要 to_openai_schema()（LangChain @tool 装饰器自动生成）
  - 不再需要 execute_tool_calls()（LangGraph 自动调度）
  - ToolRegistry 退化为轻量命名空间 + 工具列表管理器
"""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """
    工具元数据定义。

    LangChain @tool 装饰器已自动处理 schema 生成和执行，
    Tool 仅保留 name / description / func 用于注册和文档。

    Attributes:
        name: 工具名（LLM 看到的标识符）
        description: 工具用途描述
        func: 可调用对象（LangChain Tool 实例或普通函数）
    """

    name: str
    description: str
    func: Callable


class ToolRegistry:
    """
    工具注册表 —— 管理一组工具的注册和查询。

    换领域 = 换工具集，Agent 核心不动。

    Usage:
        registry = ToolRegistry()
        registry.register(Tool(name="lookup_symptom_owl", ...))
        tools = registry.get_langchain_tools()  # 直接喂给 create_react_agent
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: "Tool") -> "ToolRegistry":
        """注册一个工具。返回 self 以支持链式调用。"""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting.")
        self._tools[tool.name] = tool
        return self

    def register_many(self, tools: list["Tool"]) -> "ToolRegistry":
        """批量注册。"""
        for t in tools:
            self.register(t)
        return self

    def get(self, name: str) -> Optional["Tool"]:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def get_langchain_tools(self) -> list:
        """
        以 LangChain 可消费的格式返回所有工具。

        Returns:
            LangChain Tool 实例列表，可直接传给 create_react_agent(tools=...)
        """
        return [t.func for t in self._tools.values()]

"""
对话状态与推理报告 (Conversation State)

职责：
  1. 管理 Agent 与用户的完整对话历史（messages）。
  2. 跟踪领域对象信息（病例/设备/事件/合同等）的累积状态。
  3. 定义统一的推理报告结构，供所有 PL Agent 使用。
  4. 追问策略 —— 判断何时需要追问、何时可以开始推理。

设计原则：
  - 状态是纯数据，不含推理逻辑。Agent 负责决策，State 负责记录。
  - 报告结构统一（P1-P5 都输出同一个 DiagnosisReport），方便对比。
  - SubjectInfo / ObservationEntry 是通用领域模型，所有领域共用。
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SubjectInfo:
    """当前正在处理的领域对象信息（病例/设备/合同/事件等）。"""

    species: str = ""             # 领域对象类型标识（物种/设备类型/合同类型…）
    breed: str = ""               # 子类别/型号（可选）
    age: Optional[int] = None     # 周期/年限/版本（可选）
    sex: str = ""                 # 附加属性（可选）

    def is_complete(self) -> bool:
        """核心标识是否已设置 —— 没有类型就无法过滤无关项。"""
        return bool(self.species)

    def summary(self) -> str:
        parts = [f"类型: {self.species or '未知'}"]
        if self.breed:
            parts.append(f"子类别: {self.breed}")
        if self.age is not None:
            parts.append(f"周期: {self.age}")
        if self.sex:
            parts.append(f"属性: {self.sex}")
        return " | ".join(parts)


@dataclass
class ObservationEntry:
    """一条观测记录（症状/故障现象/条款异常/事件特征）。"""

    name: str                               # 观测名称
    severity: str = ""                      # 严重程度/影响等级（可选）
    details: dict = field(default_factory=dict)  # 附加详情（数值、上下文等）


@dataclass
class DiagnosisItem:
    """
    单条推理结果。

    Attributes:
        disease: 结论名称
        confidence: 置信度（0.0 - 1.0）
        level: 等级（"确诊" / "疑似" / "排除"）
        disease_id: 知识库中的标识
        evidence: 支撑证据列表
        missing: 缺失的关键观测
    """

    disease: str
    confidence: float
    level: str = ""
    disease_id: str = ""
    evidence: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "disease": self.disease,
            "confidence": round(self.confidence, 3),
            "level": self.level,
            "disease_id": self.disease_id,
            "evidence": self.evidence,
            "missing": self.missing,
        }


@dataclass
class DiagnosisReport:
    """
    统一的推理报告。所有 PL Agent 输出此结构。

    既是 Agent 对用户的最终回答，也是下游程序可消费的数据。
    """

    subject: SubjectInfo = field(default_factory=SubjectInfo)
    observations: list[ObservationEntry] = field(default_factory=list)
    results: list[DiagnosisItem] = field(default_factory=list)
    reasoning_engine: str = ""          # "OWL" / "Prolog" / "SPARQL" / "Fuzzy" / "Hybrid"
    reasoning_path: str = ""            # 人类可读的推理路径描述
    disclaimer: str = ""

    def top_diagnosis(self) -> Optional[DiagnosisItem]:
        """返回置信度最高的结果（排除已排除项）。"""
        active = [r for r in self.results if r.level != "排除"]
        if not active:
            return None
        return max(active, key=lambda r: r.confidence)

    def to_dict(self) -> dict:
        return {
            "subject": self.subject.summary(),
            "observations": [s.name for s in self.observations],
            "results": [r.to_dict() for r in self.results],
            "reasoning_engine": self.reasoning_engine,
            "reasoning_path": self.reasoning_path,
            "disclaimer": self.disclaimer,
        }

    def format_for_user(self) -> str:
        """生成面向最终用户的推理报告文本。"""
        if not self.results:
            return "推理引擎未返回任何结果。"

        lines = [
            "## 推理报告",
            "",
            f"**对象信息**：{self.subject.summary()}",
            f"**观测记录**：{'、'.join(s.name for s in self.observations) if self.observations else '无'}",
            "",
            "### 推理结果",
            "",
        ]

        for i, item in enumerate(self.results[:5], 1):
            level_icon = {"确诊": "●", "疑似": "○", "排除": "✕"}.get(item.level, "?")
            lines.append(
                f"{i}. {level_icon} **{item.disease}** — 置信度 {item.confidence:.0%}"
            )
            if item.evidence:
                lines.append(f"   证据：{'、'.join(item.evidence)}")
            if item.missing:
                lines.append(f"   缺失：{'、'.join(item.missing)}")

        if self.reasoning_path:
            lines.append("")
            lines.append("### 推理路径")
            lines.append(self.reasoning_path)

        lines.append("")
        lines.append(f"*推理引擎：{self.reasoning_engine}*")
        if self.disclaimer:
            lines.append(f"*{self.disclaimer}*")

        return "\n".join(lines)


class ConversationState:
    """
    管理整个对话的状态。

    职责：
      - 记录 user / assistant 消息（供 Agent 维持上下文）
      - 跟踪领域对象和观测的累积
      - 判断信息是否足够启动推理

    Usage:
        state = ConversationState()
        state.add_user_message("猫咪发烧，不吃东西")
        state.add_assistant_message("请问猫咪体温多少度？")
        if state.is_ready_for_reasoning():
            case_dict = state.to_case_dict()
            ...
    """

    def __init__(self, max_messages: int = 40):
        self.messages: list[dict] = []
        self.max_messages = max_messages
        self.subject = SubjectInfo()
        self.observations: list[ObservationEntry] = []
        self.turn_count: int = 0
        self.current_report: Optional[DiagnosisReport] = None

        self.min_observations_for_reasoning: int = 2

    # ---- 消息管理 ----

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """添加一条消息到历史。自动裁剪旧消息。"""
        msg = {"role": role, "content": content, **kwargs}
        self.messages.append(msg)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def add_user_message(self, content: str) -> None:
        self.turn_count += 1
        self.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        self.add_message("assistant", content)

    # ---- 领域对象管理 ----

    def set_subject(
        self, species: str, breed: str = "", age: int = None, sex: str = ""
    ):
        """设置当前领域对象的基本信息。"""
        self.subject = SubjectInfo(species=species, breed=breed, age=age, sex=sex)

    def add_observation(self, name: str, severity: str = "", details: dict = None):
        """添加一条观测记录；同名观测会自动合并详情。"""
        for s in self.observations:
            if s.name == name:
                if severity:
                    s.severity = severity
                if details:
                    s.details.update(details)
                return
        self.observations.append(
            ObservationEntry(name=name, severity=severity, details=details or {})
        )

    # ---- 追问策略 ----

    def should_clarify(self) -> bool:
        """判断当前信息是否不足以启动推理，需要继续追问。"""
        if not self.subject.is_complete():
            return True
        if len(self.observations) < self.min_observations_for_reasoning:
            return True
        return False

    def is_ready_for_reasoning(self) -> bool:
        """信息是否已足够，可以启动推理。"""
        return not self.should_clarify()

    # ---- 供推理引擎的输入 ----

    def to_case_dict(self) -> dict:
        """
        将当前对话状态转换为推理引擎所需的统一输入格式。

        这是 Agent 与 P1-P5 推理引擎之间的桥梁。
        key 名使用领域无关术语（subject_type / observations）。
        各 PL 模块在消费时自行映射为自己领域的语义。
        """
        case = {
            "subject_type": self.subject.species,
            "observations": [s.name for s in self.observations],
        }
        if self.subject.breed:
            case["breed"] = self.subject.breed
        if self.subject.age is not None:
            case["age"] = self.subject.age

        details = {}
        for s in self.observations:
            if s.severity or s.details:
                item = {}
                if s.severity:
                    item["severity"] = s.severity
                item.update(s.details)
                details[s.name] = item
        if details:
            case["observation_details"] = details

        return case

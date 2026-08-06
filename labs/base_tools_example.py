"""
PL 参考工具集模板（基于 LangChain @tool 装饰器）

这是创建 PL* 工具的参考模板，展示了标准的 tools_factory 模式：
  tools_factory(state, diagnose_fn, report_builder) -> list[Tool]

每个 PL 模块应创建自己的 tools_factory，根据领域需求定制工具。
此文件仅供 PL 开发者参考，不被 agent_core 直接引用。

核心模式：
  1. 用 @tool 装饰器定义每个工具（LangChain 自动生成 OpenAI schema）
  2. 工具通过闭包捕获 state（Agent 传入，保证单状态源）
  3. 工具通过闭包捕获 diagnose_fn 和 report_builder（领域推理函数）
  4. tools_factory 返回 LangChain Tool 列表，直接喂给 create_react_agent

换场景 = 换 tools_factory + diagnose_fn + report_builder + system_prompt
"""

from agent_core.conversation import ConversationState, DiagnosisReport


def create_base_tools(state: ConversationState, diagnose_fn, report_builder):
    """
    创建兽医诊断基础工具集。

    此实现展示了四种典型工具模式：
      - 数据登记工具（set_subject_info） — 确认领域对象基本信息
      - 逐条采集工具（add_observation） — 记录观测/症状
      - 状态查询工具（get_case_summary）  — 检查信息收集进度
      - 推理触发工具（run_reasoning）     — 信息足够后启动推理引擎

    其他领域（法律、工程、金融）可以复用相同模式，替换工具名和描述。

    技术要点：
      - state.set_subject() / state.add_observation() 是 agent_core 通用 API
      - state.is_ready_for_reasoning() 判断信息是否足够
      - state.to_case_dict() 将状态转换为推理引擎输入
    """
    from langchain_core.tools import tool

    @tool
    def set_subject_info(
        species: str,
        breed: str = "",
        age: int = 0,
        sex: str = "",
    ) -> str:
        """登记领域对象的基本信息（通用模板，宠医场景下为宠物信息）。

        这是推理的第一步：确定对象类型后，推理引擎才知道该查哪些规则。
        类型标识是必需的，其他信息可选但有助于提高推理精度。

        Args:
            species: 对象类型标识，如'猫'或'狗'（必填）
            breed: 子类别，如'英短'、'金毛'（可选）
            age: 周期/年限（可选）
            sex: 附加属性（可选）
        """
        state.set_subject(
            species=species,
            breed=breed,
            age=age if age > 0 else None,
            sex=sex,
        )
        return f"已登记：{state.subject.summary()}"

    @tool
    def add_obs(
        name: str,
        severity: str = "",
        detail: str = "",
    ) -> str:
        """添加一条观测记录（症状/故障现象/条款异常）。

        每次调用添加一条观测。使用标准术语（如'发热'而非'身体烫'）。
        severity 用于度量严重程度，detail 可附带额外数值描述。

        Args:
            name: 观测名称（标准术语），如'发热'、'呕吐'、'腹泻'
            severity: 严重程度：轻度/中度/重度（可选）
            detail: 额外描述，格式如'体温:40.2, 颜色:暗红'（可选）
        """
        details = {}
        if detail:
            for part in detail.split(","):
                part = part.strip()
                if ":" in part:
                    k, v = part.split(":", 1)
                    details[k.strip()] = v.strip()
                else:
                    details["note"] = part

        for k in details:
            try:
                details[k] = float(details[k])
            except (ValueError, TypeError):
                pass

        state.add_observation(name, severity=severity, details=details)
        return f"已记录观测：{name}" + (
            f"（{severity}）" if severity else ""
        ) + (
            f" [{details}]" if details else ""
        )

    @tool
    def get_case_summary() -> str:
        """查看当前病例摘要。

        在调用 run_reasoning 之前使用此工具，确认物种已登记、
        至少记录了 2 条观测。如果 ready_for_reasoning 为 false，
        需要继续追问用户。
        """
        import json

        summary = {
            "subject": state.subject.summary(),
            "observations_count": len(state.observations),
            "observations": [s.name for s in state.observations],
            "severity_available": any(s.severity for s in state.observations),
            "ready_for_reasoning": state.is_ready_for_reasoning(),
        }
        return json.dumps(summary, ensure_ascii=False)

    @tool
    def run_reasoning() -> str:
        """执行推理引擎，基于已收集的信息进行推理诊断。

        调用前确保已登记对象类型和至少 2 条观测。
        返回完整的推理报告（包含置信度、证据、推理路径）。
        """
        if not state.subject.is_complete():
            return "错误：尚未登记对象类型信息。请先调用 set_subject_info。"
        if len(state.observations) < state.min_observations_for_reasoning:
            return (
                f"错误：观测不足（当前 {len(state.observations)} 条，"
                f"至少需要 {state.min_observations_for_reasoning} 条）。"
                "请继续收集观测信息。"
            )

        case_dict = state.to_case_dict()
        try:
            results = diagnose_fn(case_dict)
        except Exception as e:
            return f"推理引擎错误：{str(e)}"

        report = report_builder(state, results)
        state.current_report = report
        return report.format_for_user()

    return [
        set_subject_info,
        add_obs,
        get_case_summary,
        run_reasoning,
    ]

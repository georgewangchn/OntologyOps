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
      - 数据登记工具（set_pet_info）
      - 逐条采集工具（add_symptom）
      - 状态查询工具（get_case_summary）
      - 推理触发工具（run_diagnosis）

    其他领域（法律、工程、金融）可以复用相同模式，替换工具名和描述。
    """
    from langchain_core.tools import tool

    @tool
    def set_pet_info(
        species: str,
        breed: str = "",
        age: int = 0,
        sex: str = "",
    ) -> str:
        """登记宠物的基本信息。

        这是诊断的第一步：确定物种后，推理引擎才知道该查哪些疾病。
        物种是必需的，其他信息可选但有助于提高诊断精度。

        Args:
            species: 物种，如'猫'或'狗'（必填）
            breed: 品种，如'英短'、'金毛'（可选）
            age: 年龄，单位为月（可选）
            sex: 性别，'公'或'母'（可选）
        """
        state.set_patient(
            species=species,
            breed=breed,
            age=age if age > 0 else None,
            sex=sex,
        )
        return f"已登记：{state.patient.summary()}"

    @tool
    def add_symptom(
        name: str,
        severity: str = "",
        detail: str = "",
    ) -> str:
        """添加一条观察到的症状。

        每次调用添加一个症状。症状名使用标准术语（如'发热'而非'身体烫'）。
        severity 用于模糊推理，detail 可附带额外数值描述。

        Args:
            name: 症状名称（标准术语），如'发热'、'呕吐'、'腹泻'
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

        state.add_symptom(name, severity=severity, details=details)
        return f"已记录症状：{name}" + (
            f"（{severity}）" if severity else ""
        ) + (
            f" [{details}]" if details else ""
        )

    @tool
    def get_case_summary() -> str:
        """查看当前病例摘要。

        在调用 run_diagnosis 之前使用此工具，确认物种已登记、
        至少记录了 2 个症状。如果 ready_for_diagnosis 为 false，
        需要继续追问用户。
        """
        import json

        summary = {
            "patient": state.patient.summary(),
            "symptoms_count": len(state.symptoms),
            "symptoms": [s.name for s in state.symptoms],
            "severity_available": any(s.severity for s in state.symptoms),
            "ready_for_diagnosis": state.is_ready_for_diagnosis(),
        }
        return json.dumps(summary, ensure_ascii=False)

    @tool
    def run_diagnosis() -> str:
        """执行推理引擎，基于已收集的病例信息进行诊断。

        调用前确保已登记物种和至少 2 个症状。
        返回完整的诊断报告（包含置信度、证据、推理路径）。
        """
        if not state.patient.is_complete():
            return "错误：尚未登记宠物物种信息。请先调用 set_pet_info。"
        if len(state.symptoms) < state.min_symptoms_for_diagnosis:
            return (
                f"错误：症状不足（当前 {len(state.symptoms)} 个，"
                f"至少需要 {state.min_symptoms_for_diagnosis} 个）。"
                "请继续收集症状。"
            )

        case_dict = state.to_case_dict()
        try:
            results = diagnose_fn(case_dict)
        except Exception as e:
            return f"诊断引擎错误：{str(e)}"

        report = report_builder(state, results)
        return report.format_for_user()

    return [
        set_pet_info,
        add_symptom,
        get_case_summary,
        run_diagnosis,
    ]

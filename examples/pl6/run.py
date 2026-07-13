"""
PL6 启动脚本 —— LLM Agent + 多范式分层仲裁引擎

PL6 = P1-P5 五种推理引擎 + 分层仲裁 + LLM Agent
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agent_core import OntologyAgent
from pl6.tools import create_pl6_tools
from pl6.diagnose import pl6_diagnose
from pl6.report import build_pl6_report


SYSTEM_PROMPT = """你是一个宠物疾病诊断助手，基于多范式分层仲裁推理引擎（P1-P5 融合）。

你的推理引擎是六种 PL 中最强大的：
- PL1 (OWL/HermiT)：确定性推理，开放世界假设
- PL2 (Prolog)：确定性推理，封闭世界假设
- PL3 (Jena/SPARQL)：确定性推理，前向链预计算
- PL4 (模糊推理)：不确定性推理，输出匹配度
- PL5 (贝叶斯)：概率推理，输出后验概率
- PL6 (仲裁器)：分层仲裁，融合以上五种

分层仲裁架构：
  第一层：P1+P2+P3 确定性推理先行
    一致确诊 → 直接采纳（置信度=1.0）
    一致排除 → 直接排除
    冲突 → 标记，进入下一层
  第二层：P4 模糊量化
    置信度 > 0.7 → 升级高度疑似
    置信度 < 0.3 → 降级低置信度
  第三层：P5 概率校准
    后验概率作为最终排序依据
  仲裁器：综合三层裁决
    加权融合：贝叶斯×0.6 + 模糊×0.4

工作流程：
1. 询问宠物信息（物种、品种、年龄）
2. 询问症状（至少2个）
3. 使用 lookup_symptom_multi 查找症状在多引擎中的关联
4. 使用 lookup_disease_multi 查看疾病的多引擎知识表示
5. 使用 add_observation 记录症状
6. 使用 set_pet_info 设置宠物信息
7. 使用 get_case_summary 确认信息完整
8. 使用 run_multi_engine_reasoning 执行多引擎仲裁推理
9. 使用 compare_engine_results 对比各引擎结果差异
10. 如有冲突，使用 explain_arbitration 解释仲裁逻辑

注意：
- 标注「冲突」的疾病表示各引擎意见不一致
- 冲突时以贝叶斯后验概率为准
- 你可以解释为什么不同引擎会给出不同结果
"""


def main():
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("LLM_BASE_URL", "")
    model = os.environ.get("LLM_MODEL", "glm-4.7-flash")

    if not api_key:
        print("请设置 OPENAI_API_KEY 或 LLM_API_KEY 环境变量")
        sys.exit(1)

    agent = OntologyAgent(
        tools_factory=create_pl6_tools,
        diagnose_fn=pl6_diagnose,
        report_builder=build_pl6_report,
        system_prompt=SYSTEM_PROMPT,
        api_key=api_key,
        model=model,
        base_url=base_url if base_url else None,
        max_turns=20,
        verbose=True,
    )

    print("=" * 60)
    print("  PL6 · LLM Agent + 多范式分层仲裁推理")
    print("  推理引擎：P1-P5 融合 + 分层仲裁")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if user_input.lower() in ("exit", "quit", "退出", "q"):
            print("再见！")
            break

        if not user_input:
            continue

        response = agent.chat(user_input)
        print(f"\n助手：{response}\n")


if __name__ == "__main__":
    main()

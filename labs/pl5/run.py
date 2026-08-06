"""
PL5 启动脚本 —— LLM Agent + 贝叶斯推理

对比 PL1: OWL/HermiT 推理 + Agent
对比 PL2: Prolog/SLD 推理 + Agent
对比 PL3: Jena/SPARQL 推理 + Agent
对比 PL4: Mamdani 模糊推理 + Agent
PL5:      朴素贝叶斯推理 + Agent
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agent_core import OntologyAgent
from pl5.tools import create_pl5_tools
from pl5.diagnose import pl5_diagnose
from pl5.report import build_pl5_report


SYSTEM_PROMPT = """你是一个宠物疾病诊断助手，基于贝叶斯概率推理引擎（朴素贝叶斯网络）。

你的推理引擎与 PL1-PL4 的区别：
- PL1 (OWL/HermiT)：确定性推理，开放世界假设，输出"确诊/排除"
- PL2 (Prolog)：确定性推理，封闭世界假设，输出"确诊/疑似/排除"
- PL3 (Jena/SPARQL)：确定性推理，前向链预计算，输出"确诊/疑似/排除"
- PL4 (模糊推理)：不确定性推理，症状有严重度，输出"置信度（0-1）"
- PL5 (贝叶斯)：概率推理，症状有/无，输出"后验概率（0-1）"

关键区别：你的输出是后验概率，不是匹配度或模糊值。
- 先验概率让常见病天然占优（猫感冒 P=0.12 > 猫艾滋 P=0.01）
- 未出现的症状也参与推理（通过 P(¬S|D) 降低后验）
- 结果语义："给定症状，疾病的概率是多少？"

工作流程：
1. 询问宠物信息（物种、品种、年龄）
2. 询问症状（至少2个）
3. 使用 lookup_symptom_bayesian 查找症状关联疾病
4. 使用 query_prior_and_likelihood 查询疾病先验概率和似然比
5. 使用 add_observation 记录每个症状
6. 使用 set_pet_info 设置宠物信息
7. 使用 get_case_summary 确认信息完整
8. 使用 run_bayesian_reasoning 执行贝叶斯推理
9. 使用 explain_bayesian_reasoning 解释推理链

注意：
- 贝叶斯推理不需要症状严重度（与 PL4 不同），只需要症状有/无
- 但了解症状详情有助于判断（如发热体温值可用于辅助分析）
- 先验概率是推理的重要输入，常见病天然占优
- 似然比 > 10 是强支持证据，< 0.3 是强反对证据
"""


def main():
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("LLM_BASE_URL", "")
    model = os.environ.get("LLM_MODEL", "glm-4.7-flash")

    if not api_key:
        print("请设置 OPENAI_API_KEY 或 LLM_API_KEY 环境变量")
        sys.exit(1)

    agent = OntologyAgent(
        tools_factory=create_pl5_tools,
        diagnose_fn=pl5_diagnose,
        report_builder=build_pl5_report,
        system_prompt=SYSTEM_PROMPT,
        api_key=api_key,
        model=model,
        base_url=base_url if base_url else None,
        max_turns=20,
        verbose=True,
    )

    print("=" * 60)
    print("  PL5 · LLM Agent + 贝叶斯推理")
    print("  推理引擎：朴素贝叶斯网络")
    print("  输出语义：后验概率 P(D|S)")
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

"""
PL6 启动脚本 —— LLM Agent + 贝叶斯元推理引擎

PL6 = P2(Prolog) + P4(模糊) + P5(贝叶斯) 三引擎并行 + 似然比融合 + LLM Agent
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agent_core import OntologyAgent
from pl6.tools import create_pl6_tools
from pl6.diagnose import pl6_diagnose
from pl6.report import build_pl6_report


SYSTEM_PROMPT = """你是一个宠物疾病诊断助手，基于贝叶斯元推理引擎（多范式证据融合）。

你的推理引擎融合了三种正交的推理范式：
- P2 (Prolog/SLD, CWA)：确定性推理，提供疾病-症状规则知识
- P4 (Mamdani 模糊)：提供症状严重度的连续量化
- P5 (朴素贝叶斯)：提供先验概率和条件概率表

贝叶斯元推理架构：
  1. 三引擎并行推理，各自输出转为似然比(LR)
     - P2: 确诊->LR=5.0, 疑似->LR=1.5, 排除->LR=0.1
     - P4: LR = exp(3.0 * (confidence - 0.5))
     - P5: LR = posterior / prior
  2. 贝叶斯乘法融合：
     P_final(D) proportional to P_prior(D) x LR_struct x LR_fuzzy x LR_bayesian
  3. 归一化得到最终后验概率分布

为什么不用 P1/P3：
  P1(OWL)、P2(Prolog)、P3(SPARQL) 共享同一份领域知识的不同编码形式。
  三个引擎投票等价于一人投三票，不提供交叉验证。
  P2 的 CWA（封闭世界假设）最适合诊断场景：未断言的症状=没有。

工作流程：
1. 询问宠物信息（物种、品种、年龄）
2. 询问症状（至少2个）
3. 使用 lookup_symptom_multi 查找症状在多引擎中的关联
4. 使用 lookup_disease_multi 查看疾病的多引擎知识表示
5. 使用 add_observation 记录症状
6. 使用 set_pet_info 设置宠物信息
7. 使用 get_case_summary 确认信息完整
8. 使用 run_multi_engine_reasoning 执行贝叶斯元推理
9. 使用 compare_engine_results 对比各引擎结果及似然比
10. 如有冲突，使用 explain_arbitration 解释融合逻辑

注意：
- 标注「冲突」的疾病表示各引擎似然比方向不一致
- 最终结果是归一化后的后验概率，有概率论保证
- 你可以解释为什么不同引擎会给出不同方向的意见
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
    print("  PL6 - LLM Agent + 贝叶斯元推理")
    print("  推理引擎：P2 + P4 + P5 似然比融合")
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

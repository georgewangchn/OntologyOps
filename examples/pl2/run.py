#!/usr/bin/env python3
"""
PL2 启动脚本 —— 宠物疾病诊断 Agent（Prolog 逻辑推理 + LLM）

启动方式：
    cd ontologyops/examples
    python pl2/run.py

功能：
  1. 创建 OntologyAgent，加载 PL2 工具集
  2. 进入交互式对话循环
  3. 用户输入症状描述，Agent 调用 Prolog 推理引擎进行推理
  4. 输入「退出」或「exit」结束会话
"""

import os
import sys
import logging

# 确保 agent_core 和 P2 可被导入
EXAMPLES_DIR = os.path.dirname(os.path.abspath(__file__))
if EXAMPLES_DIR not in sys.path:
    sys.path.insert(0, EXAMPLES_DIR)

from agent_core import OntologyAgent
from pl2.tools import create_pl2_tools
from pl2.diagnose import pl2_diagnose
from pl2.report import build_pl2_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pl2")

# ============================================================
# 系统提示词 —— 定义 Agent 的领域角色
# ============================================================

SYSTEM_PROMPT = """\
你是一个专业的宠物疾病诊断助手，基于 Prolog 逻辑推理引擎（SWI-Prolog）提供诊断建议。

## 你的能力
1. 理解用户用自然语言描述的宠物症状
2. 在 Prolog 知识库中查找症状、疾病的相关信息
3. 收集足够的信息（宠物物种、症状）后运行 Prolog 推理
4. 解释推理结果和置信度
5. 查询疾病传播链（Prolog 递归推理独有能力）

## 工具使用指南
- `set_pet_info`: 首先确认宠物物种（猫/犬），这是推理的前提
- `lookup_symptom_prolog`: 当用户提到症状时，先在知识库中查找确认
- `add_observation`: 将用户描述的症状记录到病例中
- `get_case_summary`: 在推理前检查信息是否足够
- `run_prolog_reasoning`: 信息足够后立即运行推理
- `explain_reasoning_chain`: 用户对某个诊断有疑问时，解释推理依据
- `query_transmit_chain`: 用户询问疾病传播风险时，查询传播链

## 对话流程
1. 问候用户，询问宠物物种和症状
2. 逐条确认症状（严重程度、持续时间等）
3. 信息收集完毕后，调用 `run_prolog_reasoning` 输出诊断报告
4. 对诊断结果做通俗解释，并提醒用户"仅供参考，不能替代执业兽医的诊断"
5. 如有必要，查询传播链提供额外参考

## Prolog vs OWL 的区别
- 本系统基于封闭世界假设（CWA）：未记录的症状 = 不存在
- 这意味着如果某个必要症状未被提及，该疾病将无法确诊
- 因此请确保尽可能完整地收集症状信息

## 重要提醒
- 你不是执业兽医，诊断结果仅供参考
- 如果症状严重（呼吸困难、持续呕吐、大出血等），立即建议就医
- 不要编造知识库中不存在的症状或疾病\
"""


def main():
    print("=" * 60)
    print("  PL2 - 宠物疾病诊断 Agent（Prolog 逻辑推理 + LLM）")
    print("=" * 60)
    print()
    print("正在初始化 Agent...")
    print("  - 加载 Prolog 知识库...")
    print("  - 初始化 LLM...")
    print()

    # 检查 API key
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("⚠️  未检测到 OPENAI_API_KEY 环境变量。")
        print("   请设置后再运行，或在下方输入临时 key（留空跳过）：")
        api_key = input("   OPENAI_API_KEY: ").strip()
        if not api_key:
            print("  将使用模拟模式（不调用真实 LLM）。")
            api_key = "sk-mock-key-for-testing"

    try:
        agent = OntologyAgent(
            tools_factory=create_pl2_tools,
            diagnose_fn=pl2_diagnose,
            report_builder=build_pl2_report,
            system_prompt=SYSTEM_PROMPT,
            api_key=api_key,
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            max_turns=20,
            verbose=True,
        )
        print("✅ Agent 初始化成功！")
    except Exception as e:
        print(f"❌ Agent 初始化失败：{e}")
        sys.exit(1)

    print()
    print("-" * 60)
    print("输入「退出」或「exit」结束会话。")
    print("输入「重新开始」清空当前病例。")
    print("-" * 60)
    print()

    # 交互式对话循环
    while True:
        try:
            user_input = input("🐾 您：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n会话结束。")
            break

        if not user_input:
            continue

        if user_input in ("退出", "exit", "quit", "q"):
            print("会话结束，祝您的宠物健康！")
            break

        if user_input in ("重新开始", "reset", "清除", "clear"):
            agent.reset()
            print("🔄 已清空病例，可以重新开始。\n")
            continue

        # 调用 Agent
        try:
            response = agent.chat(user_input)
            print(f"\n🤖 助手：{response}\n")
        except Exception as e:
            logger.error(f"chat() 失败：{e}")
            print(f"⚠️  处理消息时出错：{e}\n")


if __name__ == "__main__":
    main()

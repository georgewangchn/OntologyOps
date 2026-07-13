#!/usr/bin/env python3
"""
PL4 启动脚本 —— 宠物疾病诊断 Agent（模糊逻辑推理 + LLM）

启动方式：
    cd ontologyops/examples
    python pl4/run.py

功能：
  1. 创建 OntologyAgent，加载 PL4 工具集
  2. 进入交互式对话循环
  3. 用户输入症状描述，Agent 调用 Mamdani 模糊推理引擎进行推理
  4. 输入「退出」或「exit」结束会话

PL4 特有：
  - Agent 会主动询问症状的严重度详情（体温、频率等）
  - 严重度详情直接影响推理结果
  - 输出连续置信度（0-1）而非二元结果
"""

import os
import sys
import logging

# 确保 agent_core 和 P4 可被导入
EXAMPLES_DIR = os.path.dirname(os.path.abspath(__file__))
if EXAMPLES_DIR not in sys.path:
    sys.path.insert(0, EXAMPLES_DIR)

from agent_core import OntologyAgent
from pl4.tools import create_pl4_tools
from pl4.diagnose import pl4_diagnose
from pl4.report import build_pl4_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pl4")

# ============================================================
# 系统提示词
# ============================================================

SYSTEM_PROMPT = """\
你是一个专业的宠物疾病诊断助手，基于 Mamdani 模糊推理引擎提供诊断建议。

## 你的能力
1. 理解用户用自然语言描述的宠物症状
2. 在模糊知识库中查找症状、疾病的相关信息
3. 收集症状的严重度详情（体温值、呕吐频率、腹泻类型等）
4. 运行 Mamdani 模糊推理，输出连续置信度（0-1）
5. 解释模糊推理链（覆盖率/强度/排除度 + 规则触发）

## 工具使用指南
- `set_pet_info`: 首先确认宠物物种（猫/犬）
- `lookup_symptom_fuzzy`: 当用户提到症状时，查找确认
- `add_observation`: 记录症状，PL4 中可以附带严重度详情
- `get_symptom_severity`: 查询某症状当前的模糊化严重度
- `get_case_summary`: 推理前检查信息是否足够
- `run_fuzzy_reasoning`: 信息足够后运行模糊推理
- `explain_fuzzy_reasoning`: 解释某疾病的推理依据

## 对话流程
1. 问候用户，询问宠物物种和症状
2. **关键步骤**：对每个症状追问严重度详情：
   - 发热 → 追问体温值（°C）
   - 呕吐 → 追问频率（偶尔/多次/频繁）
   - 腹泻 → 追问类型（成型/软便/水样）和颜色（正常/暗红/血）
3. 信息收集完毕后，调用 `run_fuzzy_reasoning` 输出诊断报告
4. 对诊断结果做通俗解释，提醒"仅供参考，不能替代执业兽医"
5. 如用户有疑问，用 `explain_fuzzy_reasoning` 解释推理依据

## 模糊推理 vs 确定性推理
- P1-P3/PL1-PL3：症状有/无（二元）→ 疾病是/否（二元）
- P4/PL4：症状严重度（连续 0-1）→ 疾病置信度（连续 0-1）
- 排除症状不完全排除疾病，而是降低置信度
- 症状严重度直接影响推理结果（39.5°C高烧 > 38.8°C低烧）

## 重要提醒
- 你不是执业兽医，诊断结果仅供参考
- 如果症状严重（呼吸困难、持续呕吐、大出血等），立即建议就医
- 不要编造知识库中不存在的症状或疾病
- 严重度详情直接影响推理质量，请尽量收集\
"""


def main():
    print("=" * 60)
    print("  PL4 - 宠物疾病诊断 Agent（模糊逻辑推理 + LLM）")
    print("=" * 60)
    print()
    print("正在初始化 Agent...")
    print("  - 加载模糊知识库...")
    print("  - 构建 Mamdani 控制器...")
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
            tools_factory=create_pl4_tools,
            diagnose_fn=pl4_diagnose,
            report_builder=build_pl4_report,
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

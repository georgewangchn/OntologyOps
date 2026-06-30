# PL1 · LLM Agent + OWL 本体推理（教学演示版）

> **多范式推理实战营 — 项目 5/6**
> 推理范式：**LangGraph Agent + OWL 本体推理（HermiT + SWRL）**
> 前置项目：[P1 · OWL / HermiT 本体推理](../P1/README.md)

> 📖 本项目将 P1 的纯推理引擎用 LLM Agent 包装，让用户用自然语言描述宠物症状，Agent 自动完成查本体、收集信息、触发推理、解释结果的全流程。

---

## 项目概述

P1 构建了一个完整的 OWL 本体推理引擎——HermiT + SWRL + 三层排除过滤，能从症状列表精确推导疾病。但 P1 的使用门槛很高：用户需要传结构化 JSON、症状名称必须精确匹配本体 label、物种要用英文。

**PL1 解决的问题**：推理引擎再强大，如果用户不会用，价值就归零。

核心思路：

> **用 LLM Agent 充当「翻译层」，用户说自然语言，Agent 自动查本体、收集信息、触发推理，再把结果翻译成人类可读的诊断报告。**

LLM 负责「听懂人话」，本体推理负责「说对话」。一个负责不确定性，一个负责确定性，合在一起才是企业决策需要的智能体。

### 与 P1 的关系

| 维度 | P1（纯推理引擎） | PL1（LLM Agent 增强） |
|------|------------------|----------------------|
| 输入方式 | 结构化 JSON | 自然语言对话 |
| 术语处理 | 必须精确匹配本体 label | LLM 自动对齐（"发烧" → "发热"） |
| 信息收集 | 用户自行准备完整症状列表 | Agent 主动追问，逐步收集 |
| 推理触发 | 手动调用 `diagnose()` | Agent 判断信息足够后自动触发 |
| 结果解释 | `List[Tuple[ThingClass, float]]` | 格式化诊断报告 + 推理路径说明 |
| 交互方式 | 一次性 API 调用 | 多轮对话，可追问、可解释 |
| 适用场景 | 开发者集成 | 面向终端用户 |
| 推理引擎 | OWL/HermiT（直接） | OWL/HermiT（通过桥接层，共享） |

**关键点**：PL1 没有修改 P1 的推理引擎，只是在外面包了一层 Agent。P1 的推理能力（三层推理、排除过滤、置信度计算）完全保留。

---

## 技术架构

### 通用 Agent 框架 + 领域工具注入

PL1 的核心设计是**关注点分离**：Agent 循环（LangGraph）与领域知识（OWL 本体）完全解耦。

```
用户自然语言
    ↓
OntologyAgent (agent_core)
  ├── System Prompt (角色定义)
  ├── 7 个 @tool (领域工具)
  └── ConversationState (对话状态)
      ↓ LangGraph ReAct 循环：Think → Act → Observe → Repeat
    ↓
P1 OWL 推理引擎 (共享)
  HermiT 推理机 + SWRL 规则 + 三层排除过滤
```

### 四个注入点

`OntologyAgent` 是领域无关的通用框架（`agent_core/agent.py`）。换场景只需要替换四个注入点：

| 注入点 | PL1 中的实现 | 作用 |
|--------|-------------|------|
| `tools_factory` | `create_pl1_tools` | 创建 7 个 LangChain 工具 |
| `diagnose_fn` | `pl1_diagnose` | 桥接 P1 的 OWL 推理引擎 |
| `report_builder` | `build_pl1_report` | 格式化为统一 `DiagnosisReport` |
| `system_prompt` | 宠物诊断助手角色定义 | 约束 Agent 的行为规范 |

```python
agent = OntologyAgent(
    tools_factory=create_pl1_tools,
    diagnose_fn=pl1_diagnose,
    report_builder=build_pl1_report,
    system_prompt=SYSTEM_PROMPT,
    api_key="sk-xxx",
    model="gpt-4o",
)
```

这意味着 PL2（Prolog）、PL3（Jena/SPARQL）、PL4（模糊逻辑）只需要实现自己的四个注入点，Agent 框架零改动复用。

---

## 七个工具

PL1 提供 7 个 LangChain `@tool` 装饰的工具（`tools.py`），覆盖**查询 → 收集 → 推理 → 解释**全流程：

| # | 工具名 | 功能 | 类别 |
|---|--------|------|------|
| 1 | `lookup_symptom_owl` | 在 OWL 本体中查找症状，返回名称、ID、常见于哪些疾病 | 查询 |
| 2 | `lookup_disease_owl` | 查找疾病，返回必要症状、排除症状、物种约束 | 查询 |
| 3 | `add_observation` | 向 ConversationState 添加一条观测记录 | 收集 |
| 4 | `set_pet_info` | 设置宠物基本信息（物种/品种/年龄/性别） | 收集 |
| 5 | `run_dl_reasoning` | 运行 HermiT DL 推理，返回诊断报告 | 推理 |
| 6 | `explain_subsumption` | 解释为什么某疾病被推理出来 | 解释 |
| 7 | `get_case_summary` | 返回当前病例摘要 | 解释 |

工具通过模块级缓存 `_get_onto()` 懒加载 OWL 本体，避免重复加载。依赖路径指向 `examples/P1/data/pet_ontology.owl`。

---

## 诊断桥接层

P1 的 `diagnose()` 函数有自己的输入格式和输出格式，与 agent_core 的通用格式不同。`diagnose.py` 是两者之间的适配器。

### 输入转换

```python
# agent_core 通用格式 → P1 格式
_SPECIES_MAP = {
    "猫": "cat", "喵": "cat", "猫咪": "cat",
    "狗": "dog", "犬": "dog", "狗狗": "dog",
}
```

用户说"猫咪"，Agent 记录为 `species="猫"`，PL1 桥接层转换为 `"cat"` 传给 P1。

### 输出转换

```python
# P1 返回: List[Tuple[owlready2.ThingClass, float]]
# agent_core 期望: List[Dict]
```

### 降级诊断

当 P1 的 `diagnose()` 函数因任何原因失败时（owlready2 未安装、本体文件损坏等），PL1 有一个降级策略：手动计算必要症状匹配度。保证即使没有 HermiT 推理机，也能给出基本结果。

### 置信度等级

| 置信度 | 等级 | 图标 |
|--------|------|------|
| >= 0.85 | 确诊 | ● |
| >= 0.50 | 疑似 | ○ |
| < 0.50 | 排除 | ✕ |

---

## 项目结构

```
pl1/
├── README.md           # 本文档
├── __init__.py         # 模块入口
├── run.py              # 启动脚本（交互式对话循环 + 系统提示词）
├── tools.py            # 7 个 LangChain @tool 工具
├── diagnose.py         # 诊断桥接（格式转换 + 降级诊断）
└── report.py           # 报告构建（DiagnosisReport + 推理路径说明）

依赖：
├── agent_core/         # 通用 Agent 框架（OntologyAgent + ConversationState）
│   ├── agent.py        # LangGraph ReAct Agent
│   ├── conversation.py # 对话状态 + 诊断报告数据结构
│   ├── tool_registry.py# 工具注册表
│   └── requirements.txt
└── P1/                 # OWL 推理引擎（共享）
    ├── src/reasoner.py # HermiT 推理 + 三层推理 + 排除逻辑
    ├── src/diagnosis.py# 诊断主流程
    └── data/pet_ontology.owl  # 本体文件 (35.7KB)

测试：
└── tests/test_pl1.py   # 6 组单元测试
```

---

## 环境准备

### 1. 安装依赖

```bash
cd ontologyops/examples
pip install -r agent_core/requirements.txt
# agent_core 依赖：langgraph, langchain, langchain-openai, langchain-core, pytest
```

### 2. P1 本体（共享）

PL1 依赖 P1 的本体文件，确保 `P1/data/pet_ontology.owl` 存在。如需重新构建本体：

```bash
cd P1
bash setup_env.sh       # 安装 owlready2 中文补丁版
cd src && python onto_builder.py   # 构建本体
```

### 3. LLM API

```bash
export OPENAI_API_KEY=sk-xxx
# 可选：换模型或 API 地址
export OPENAI_MODEL=gpt-4o
export OPENAI_BASE_URL=https://api.openai.com/v1
```

---

## 运行

### 交互式对话

```bash
cd ontologyops/examples
python pl1/run.py
```

启动后进入交互式对话：

```
============================================================
  PL1 - 宠物疾病诊断 Agent（OWL DL + LLM）
============================================================

输入「退出」或「exit」结束会话。
输入「重新开始」清空当前病例。

🐾 您：我的猫又吐又拉，还发烧
🤖 助手：我来帮您分析一下。首先确认一下，是猫咪对吧？

🐾 您：对，英短，3岁

🤖 助手：好的，英短，3岁。您提到的症状我确认一下...
        信息收集完毕，正在运行推理...

## 推理报告

**对象信息**：类型: 猫 | 子类别: 英短 | 周期: 3
**观测记录**：发热、呕吐、腹泻、精神萎靡

### 推理结果

1. ● **猫瘟** — 置信度 99%
   证据：发热、呕吐、腹泻

2. ○ **犬细小病毒** — 置信度 77%
   证据：呕吐、腹泻
   缺失：精神萎靡

---
*推理引擎：OWL-DL (HermiT) + SWRL*
*本结果由 OWL 本体推理引擎生成，仅供参考，不能替代执业兽医的诊断。*
```

### 运行测试

```bash
cd ontologyops/examples
python -m pytest tests/test_pl1.py -v
```

测试覆盖（6 组）：

| 测试组 | 覆盖内容 |
|--------|---------|
| 工具集创建 | `create_pl1_tools` 返回 7 个工具，名称正确 |
| 工具功能 | `add_observation` / `set_pet_info` / `get_case_summary` 正确写入和读取 state |
| 推理前置检查 | 信息不足时 `run_dl_reasoning` 返回提示而非报错 |
| 报告构建 | `build_pl1_report` 生成正确的 `DiagnosisReport`，`format_for_user` 输出可读文本 |
| Agent 集成 | `OntologyAgent` 创建成功、`reset()` 清空状态、工具与 state 同步 |
| OWL 推理 | `pl1_diagnose` 端到端测试（本体文件存在时运行，不存在时跳过） |

测试不依赖外部服务（OpenAI API），OWL 本体测试有降级跳过机制。

---

## 对话流程示例

以"猫瘟"为例，Agent 的完整交互过程：

```
🐾 用户：我的猫又吐又拉，还发烧，精神也不好

🤖 Agent 自动决策：
  1. 术语对齐：查本体后发现"发烧"应为"发热"，自动修正
  2. 追问判断：通过 get_case_summary() 检查信息是否足够
  3. 推理时机：等信息足够后才触发 run_dl_reasoning
  4. 解释响应：用户问"为什么"时，调用 explain_subsumption 展示依据

工具调用序列：
  set_pet_info(species="猫")
  lookup_symptom_owl("发烧") → "是否指「发热」？"
  add_observation("发热", severity="重度")
  add_observation("呕吐")
  add_observation("腹泻")
  add_observation("精神萎靡")
  get_case_summary() → ✅ 信息已足够
  run_dl_reasoning() → 诊断报告
```

---

## Agent 兜底机制

LLM 有时候会"卡住"——循环调用工具但不推进推理，或者工具调用序列超出限制。`OntologyAgent._force_diagnosis()` 提供安全兜底：

当 LangGraph 的 `recursion_limit`（默认 `max_turns * 3`）耗尽时，Agent 不返回错误，而是直接用已收集的信息调用推理引擎，保证用户至少能得到一个诊断结果。

---

## PL 系列路线图

| 编号 | 对应范式 | 推理引擎 | 状态 |
|------|---------|---------|------|
| **PL1** | OWL/HermiT 本体推理 | HermiT + SWRL | ✅ 已完成 |
| PL2 | Prolog 逻辑推理 | SWI-Prolog | 规划中 |
| PL3 | Jena/SPARQL 三元组推理 | Apache Jena | 规划中 |
| PL4 | 模糊逻辑推理 | FuzzyOWL | 规划中 |
| PL5 | 多范式融合引擎 | 上述全部 | 规划中 |

每个 PL 复用同一个 `agent_core` 框架，只需实现自己的四个注入点。最终 PL5 将融合所有推理范式，Agent 根据问题特征自动选择最合适的推理引擎。

---

## 参考资料

1. LangGraph 文档：https://langchain-ai.github.io/langgraph/
2. LangChain Tools：https://python.langchain.com/docs/modules/tools/
3. owlready2 官方文档：https://owlready2.readthedocs.io/
4. Owlready2-Chinese（中文补丁）：https://github.com/georgewangchn/Owlready2-Chinese
5. [P1 · OWL / HermiT 本体推理](../P1/README.md) — PL1 的推理引擎基础
6. [PL1 博客文章](https://senlinpubu.top/blog/pl1-agent-reasoning/) — 完整技术讲解
7. 《当 LLM 不够用了——本体推理的企业决策实践》

---

*作者：森林瀑布 | 项目类型：多范式推理实战营 PL1 | 最后更新：2026-06-30*

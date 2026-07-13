# PL2 · LLM Agent + Prolog 逻辑推理（教学演示版）

> **多范式推理实战营 — 项目 6/6（PL 系列）**
> 推理范式：**LangGraph Agent + Prolog 逻辑推理（SWI-Prolog + SLD 归结）**
> 前置项目：[P2 · Prolog 逻辑推理](../P2/README.md)

> 📖 本项目将 P2 的 Prolog 推理引擎用 LLM Agent 包装，让用户用自然语言描述宠物症状，Agent 自动完成查知识库、收集信息、触发推理、解释结果的全流程。

---

## 项目概述

P2 构建了一个完整的 Prolog 规则推理引擎——Horn 子句 + SLD 归结 + 封闭世界假设（CWA），能从症状列表推导疾病并计算置信度。但 P2 的使用门槛与 P1 一样高：用户需要传结构化 JSON、症状名称必须精确匹配 Prolog 原子、物种要用英文。

**PL2 解决的问题**：和 PL1 一样——推理引擎再强大，如果用户不会用，价值就归零。

核心思路：

> **用 LLM Agent 充当「翻译层」，用户说自然语言，Agent 自动查 Prolog 知识库、收集信息、触发 SLD 归结推理，再把结果翻译成人类可读的诊断报告。**

LLM 负责「听懂人话」，Prolog 推理负责「说对话」。一个负责不确定性，一个负责确定性。

### 与 PL1 的对比

| 维度 | PL1（OWL Agent） | PL2（Prolog Agent） |
|------|------------------|---------------------|
| 推理引擎 | HermiT（Tableau 算法） | SWI-Prolog（SLD 归结） |
| 世界假设 | 开放世界（OWA） | 封闭世界（CWA） |
| 否定语义 | 不能从"未断言"推断"不存在" | `\+`（negation as failure） |
| 递归推理 | ❌ | ✅ 原生支持 |
| 传播链查询 | ❌ | ✅ `query_transmit_chain` |
| 工具数量 | 7 | 8（多一个传播链工具） |
| Agent 框架 | agent_core（共享） | agent_core（共享） |

**关键差异**：PL2 多了一个 `query_transmit_chain` 工具，利用 Prolog 的递归推理能力查询疾病传播链。这是 OWL/SWRL 无法实现的。

---

## 技术架构

### 通用 Agent 框架 + 领域工具注入

PL2 与 PL1 共享同一个 `agent_core` 框架，只是四个注入点不同：

```
用户自然语言
    ↓
OntologyAgent (agent_core)        ← 与 PL1 完全相同
  ├── System Prompt (角色定义)
  ├── 8 个 @tool (领域工具)        ← PL2 特有
  └── ConversationState (对话状态)
      ↓ LangGraph ReAct 循环：Think → Act → Observe → Repeat
    ↓
P2 Prolog 推理引擎 (共享)
  SWI-Prolog + Horn 子句 + SLD 归结 + CWA
```

### 四个注入点

| 注入点 | PL1 中的实现 | PL2 中的实现 |
|--------|-------------|-------------|
| `tools_factory` | `create_pl1_tools` | `create_pl2_tools` |
| `diagnose_fn` | `pl1_diagnose` | `pl2_diagnose` |
| `report_builder` | `build_pl1_report` | `build_pl2_report` |
| `system_prompt` | OWL 诊断助手 | Prolog 诊断助手 |

```python
agent = OntologyAgent(
    tools_factory=create_pl2_tools,
    diagnose_fn=pl2_diagnose,
    report_builder=build_pl2_report,
    system_prompt=SYSTEM_PROMPT,
    api_key="sk-xxx",
    model="gpt-4o",
)
```

---

## 八个工具

PL2 提供 8 个 LangChain `@tool` 工具，比 PL1 多一个传播链查询：

| # | 工具名 | 功能 | 类别 |
|---|--------|------|------|
| 1 | `lookup_symptom_prolog` | 在 Prolog 知识库中查找症状，返回关联疾病 | 查询 |
| 2 | `lookup_disease_prolog` | 查找疾病，返回必要症状、排除症状、物种约束 | 查询 |
| 3 | `add_observation` | 向 ConversationState 添加一条观测记录 | 收集 |
| 4 | `set_pet_info` | 设置宠物基本信息（物种/品种/年龄/性别） | 收集 |
| 5 | `run_prolog_reasoning` | 运行 Prolog SLD 推理，返回诊断报告 | 推理 |
| 6 | `explain_reasoning_chain` | 解释某疾病的推理链 | 解释 |
| 7 | `query_transmit_chain` | 查询疾病传播链（Prolog 递归独有） | 解释 |
| 8 | `get_case_summary` | 返回当前病例摘要 | 解释 |

---

## 项目结构

```
pl2/
├── README.md           # 本文档
├── __init__.py         # 模块入口
├── run.py              # 启动脚本（交互式对话循环 + 系统提示词）
├── tools.py            # 8 个 LangChain @tool 工具
├── diagnose.py         # 诊断桥接（格式转换 + 降级诊断）
└── report.py           # 报告构建（DiagnosisReport + 推理路径说明）

依赖：
├── agent_core/         # 通用 Agent 框架（与 PL1 共享）
├── P2/                 # Prolog 推理引擎（共享）
│   ├── src/reasoner.py # pyswip 推理引擎
│   ├── src/rules.pl    # Prolog 规则（6 条）
│   └── data/pet_kb.pl  # 知识库文件
└── tests/test_pl2.py   # 单元测试
```

---

## 环境准备

### 1. 安装依赖

```bash
cd ontologyops/examples
pip install -r agent_core/requirements.txt
# agent_core 依赖：langgraph, langchain, langchain-openai, langchain-core, pytest
```

### 2. SWI-Prolog

```bash
# macOS
brew install swi-prolog

# Ubuntu/Debian
sudo apt-get install swi-prolog
```

### 3. pyswip + P2 知识库

```bash
pip install pyswip

cd P2 && python src/kb_builder.py   # 构建知识库
```

### 4. LLM API

```bash
export OPENAI_API_KEY=sk-xxx
export OPENAI_MODEL=gpt-4o
export OPENAI_BASE_URL=https://api.openai.com/v1
```

---

## 运行

### 交互式对话

```bash
cd ontologyops/examples
python pl2/run.py
```

### 运行测试

```bash
cd ontologyops/examples
python -m pytest tests/test_pl2.py -v
```

测试覆盖（7 组）：

| 测试组 | 覆盖内容 |
|--------|---------|
| 工具集创建 | `create_pl2_tools` 返回 8 个工具，名称正确 |
| 工具功能 | `add_observation` / `set_pet_info` / `get_case_summary` 正确写入和读取 state |
| 推理前置检查 | 信息不足时 `run_prolog_reasoning` 返回提示而非报错 |
| 报告构建 | `build_pl2_report` 生成正确的 `DiagnosisReport`，包含 CWA 说明 |
| Agent 集成 | `OntologyAgent` 创建成功、`reset()` 清空状态、工具与 state 同步 |
| Prolog 推理 | `pl2_diagnose` 端到端测试（环境就绪时运行，否则跳过） |
| 格式转换 | `_convert_case_dict` 物种映射正确 |

---

## CWA vs OWA 的实践影响

```
病例：猫，发热 + 呕吐，未记录是否腹泻

PL1（OWA）：HermiT 不能因"未断言腹泻"就判定"没有腹泻"
  → 需要显式的排除症状断言才能排除疾病
  → 猫瘟可能仍然确诊（如果其他条件满足）

PL2（CWA）：\+ has(case, '腹泻') 成功（因为没有这个事实）
  → 未记录 = 不存在
  → 猫瘟无法确诊（因为必要症状"腹泻"缺失）
  → 只能给出"疑似"判断
```

这意味着 PL2 对信息完整性的要求更高——少一条症状，可能就从"确诊"降为"疑似"。Agent 需要更积极地追问。

---

## PL 系列路线图

| 编号 | 对应范式 | 推理引擎 | 状态 |
|------|---------|---------|------|
| PL1 | OWL/HermiT 本体推理 | HermiT + SWRL | ✅ 已完成 |
| **PL2** | **Prolog 逻辑推理** | **SWI-Prolog** | **✅ 已完成** |
| PL3 | Jena/SPARQL 三元组推理 | Apache Jena | 规划中 |
| PL4 | 模糊逻辑推理 | FuzzyOWL | 规划中 |
| PL5 | 多范式融合引擎 | 上述全部 | 规划中 |

---

## 参考资料

1. [P2 · Prolog 逻辑推理](../P2/README.md) — PL2 的推理引擎基础
2. [PL1 · LLM Agent / OWL 推理](../pl1/README.md) — 对比项目
3. SWI-Prolog 文档：https://www.swi-prolog.org/
4. pyswip 文档：https://github.com/yuce/pyswip
5. [PL2 博客文章](https://senlinpubu.top/blog/pl2-prolog-agent/) — 完整技术讲解
6. 《当 LLM 不够用了——本体推理的企业决策实践》

---

*作者：森林瀑布 | 项目类型：多范式推理实战营 PL2 | 最后更新：2026-07-13*

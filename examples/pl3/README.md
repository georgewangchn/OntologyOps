# PL3 · LLM Agent + Jena/SPARQL 三元组推理（教学演示版）

> **多范式推理实战营 — 项目 7/8（PL 系列）**
> 推理范式：**LangGraph Agent + Jena 前向链 + SPARQL 查询推理一体化**
> 前置项目：[P3 · Jena/SPARQL 三元组推理](../P3/README.md)

> 📖 本项目将 P3 的 Jena/SPARQL 推理引擎用 LLM Agent 包装，让用户用自然语言描述宠物症状，Agent 自动完成查 RDF 知识库、收集信息、触发前向链推理、解释结果的全流程。

---

## 项目概述

P3 构建了一个完整的 Jena Fuseki + SPARQL 推理引擎——前向链预计算 + SPARQL 查询推理一体化 + 传递闭包预计算。但 P3 的使用门槛与 P1/P2 一样高：用户需要传结构化 JSON、症状名称必须精确匹配 RDF 资源 URI、物种要用英文。

**PL3 解决的问题**：和 PL1/PL2 一样——推理引擎再强大，如果用户不会用，价值就归零。

核心思路：

> **用 LLM Agent 充当「翻译层」，用户说自然语言，Agent 自动查 RDF 知识库、收集信息、触发 SPARQL 推理，再把结果翻译成人类可读的诊断报告。**

LLM 负责「听懂人话」，SPARQL 推理负责「说对话」。一个负责不确定性，一个负责确定性。

### 与 PL1/PL2 的对比

| 维度 | PL1（OWL Agent） | PL2（Prolog Agent） | PL3（SPARQL Agent） |
|------|------------------|---------------------|---------------------|
| 推理引擎 | HermiT（Tableau 算法） | SWI-Prolog（SLD 归结） | Jena（前向链 + SPARQL） |
| 世界假设 | 开放世界（OWA） | 封闭世界（CWA） | 开放世界（OWA） |
| 推理时机 | 查询前一次性推理 | 查询时实时推理 | 数据写入时预计算 |
| 传递闭包 | 声明式（TransitiveProperty） | 递归查询时计算 | 预计算（物化视图） |
| 递归推理 | ❌ | ✅ 原生支持 | ❌（但传递闭包预计算） |
| 工具数量 | 7 | 8 | 8 |
| Agent 框架 | agent_core（共享） | agent_core（共享） | agent_core（共享） |

**关键差异**：PL3 的 `query_transitive_closure` 展示了 Jena 前向链预计算的能力——传递闭包在数据加载时就算好了，查询时直接读取，不需要递归。

---

## 技术架构

### 通用 Agent 框架 + 领域工具注入

PL3 与 PL1/PL2 共享同一个 `agent_core` 框架，只是四个注入点不同：

```
用户自然语言
    ↓
OntologyAgent (agent_core)        ← 与 PL1/PL2 完全相同
  ├── System Prompt (角色定义)
  ├── 8 个 @tool (领域工具)        ← PL3 特有
  └── ConversationState (对话状态)
      ↓ LangGraph ReAct 循环：Think → Act → Observe → Repeat
    ↓
P3 Jena/SPARQL 推理引擎 (共享)
  rdflib 本地模式 / Jena Fuseki + 前向链 + SPARQL
```

### 四个注入点

| 注入点 | PL1 | PL2 | PL3 |
|--------|-----|-----|-----|
| `tools_factory` | `create_pl1_tools` | `create_pl2_tools` | `create_pl3_tools` |
| `diagnose_fn` | `pl1_diagnose` | `pl2_diagnose` | `pl3_diagnose` |
| `report_builder` | `build_pl1_report` | `build_pl2_report` | `build_pl3_report` |
| `system_prompt` | OWL 诊断助手 | Prolog 诊断助手 | SPARQL 诊断助手 |

---

## 八个工具

PL3 提供 8 个 LangChain `@tool` 工具：

| # | 工具名 | 功能 | 类别 |
|---|--------|------|------|
| 1 | `lookup_symptom_sparql` | 在 RDF 知识库中查找症状，返回关联疾病 | 查询 |
| 2 | `lookup_disease_sparql` | 查找疾病，返回必要症状、排除症状、物种约束 | 查询 |
| 3 | `add_observation` | 向 ConversationState 添加一条观测记录 | 收集 |
| 4 | `set_pet_info` | 设置宠物基本信息（物种/品种/年龄/性别） | 收集 |
| 5 | `run_sparql_reasoning` | 运行 Jena 前向链 + SPARQL 推理，返回诊断报告 | 推理 |
| 6 | `explain_reasoning_chain` | 解释某疾病的推理链（含 OWA 说明） | 解释 |
| 7 | `query_transitive_closure` | 查询疾病传播的传递闭包（前向链预计算） | 解释 |
| 8 | `get_case_summary` | 返回当前病例摘要 | 解释 |

---

## 项目结构

```
pl3/
├── README.md           # 本文档
├── __init__.py         # 模块入口
├── run.py              # 启动脚本（交互式对话循环 + 系统提示词）
├── tools.py            # 8 个 LangChain @tool 工具
├── diagnose.py         # 诊断桥接（格式转换 + Fuseki→rdflib 降级）
└── report.py           # 报告构建（DiagnosisReport + 推理路径说明）

依赖：
├── agent_core/         # 通用 Agent 框架（与 PL1/PL2 共享）
├── P3/                 # Jena/SPARQL 推理引擎（共享）
│   ├── src/reasoner.py       # SPARQLWrapper 推理引擎
│   ├── src/local_reasoner.py # rdflib 本地推理（降级）
│   ├── src/kb_builder.py     # CSV → Turtle 三元组
│   └── data/pet.ttl          # 知识库文件
└── tests/test_pl3.py   # 单元测试
```

---

## 环境准备

### 1. 安装依赖

```bash
cd ontologyops/examples
pip install -r agent_core/requirements.txt
pip install rdflib
```

### 2. P3 知识库

```bash
cd P3 && python src/kb_builder.py   # 构建 Turtle 知识库
```

### 3. LLM API

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
python pl3/run.py
```

### 运行测试

```bash
cd ontologyops/examples
python -m pytest tests/test_pl3.py -v
```

测试覆盖（7 组）：

| 测试组 | 覆盖内容 |
|--------|---------|
| 工具集创建 | `create_pl3_tools` 返回 8 个工具，名称正确 |
| 工具功能 | `add_observation` / `set_pet_info` / `get_case_summary` 正确写入和读取 state |
| 推理前置检查 | 信息不足时 `run_sparql_reasoning` 返回提示而非报错 |
| 报告构建 | `build_pl3_report` 生成正确的 `DiagnosisReport`，包含 OWA 说明 |
| Agent 集成 | `OntologyAgent` 创建成功、`reset()` 清空状态、工具与 state 同步 |
| RDF 推理 | `pl3_diagnose` 端到端测试（环境就绪时运行，否则跳过） |
| 格式转换 | `_convert_case_dict` 物种映射正确 |

---

## OWA vs CWA 的实践影响

```
病例：猫，发热 + 呕吐，未记录是否腹泻

PL2（CWA）：\+ has(case, '腹泻') 成功（因为没有这个事实）
  → 未记录 = 不存在
  → 猫瘟无法确诊（必要症状"腹泻"缺失）
  → 只能给出"疑似"判断

PL3（OWA）：未断言腹泻 ≠ 没有腹泻
  → 可能是尚未检查，不能因"未断言"就排除
  → 猫瘟仍可能为疑似（覆盖率 2/3 = 0.67）
  → 不会因信息缺失而完全排除疾病
```

这意味着 PL3 对信息完整性的要求相对宽松——少一条症状，疾病仍然出现在结果中（只是置信度低）。但这也意味着可能产生更多假阳性。

---

## PL 系列路线图

| 编号 | 对应范式 | 推理引擎 | 状态 |
|------|---------|---------|------|
| PL1 | OWL/HermiT 本体推理 | HermiT + SWRL | ✅ 已完成 |
| PL2 | Prolog 逻辑推理 | SWI-Prolog | ✅ 已完成 |
| **PL3** | **Jena/SPARQL 三元组推理** | **Apache Jena + rdflib** | **✅ 已完成** |
| PL4 | 模糊逻辑推理 | scikit-fuzzy | ✅ 已完成 |
| PL5 | 多范式融合引擎 | 上述全部 | 规划中 |

---

## 参考资料

1. [P3 · Jena/SPARQL 三元组推理](../P3/README.md) — PL3 的推理引擎基础
2. [PL1 · LLM Agent / OWL 推理](../pl1/README.md) — 对比项目
3. [PL2 · LLM Agent / Prolog 推理](../pl2/README.md) — 对比项目
4. rdflib 文档：https://rdflib.readthedocs.io/
5. Apache Jena 文档：https://jena.apache.org/
6. [PL3 博客文章](https://senlinpubu.top/blog/pl3-sparql-agent/) — 完整技术讲解
7. 《当 LLM 不够用了——本体推理的企业决策实践》

---

*作者：森林瀑布 | 项目类型：多范式推理实战营 PL3 | 最后更新：2026-07-13*

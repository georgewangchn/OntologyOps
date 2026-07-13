# PL4 · LLM Agent + 模糊逻辑推理（教学演示版）

> **多范式推理实战营 — 项目 8/8（PL 系列）**
> 推理范式：**LangGraph Agent + Mamdani 模糊推理（scikit-fuzzy）**
> 前置项目：[P4 · 模糊逻辑推理](../P4/README.md)

> 📖 本项目将 P4 的 Mamdani 模糊推理引擎用 LLM Agent 包装，让用户用自然语言描述宠物症状（含严重度），Agent 自动完成查模糊知识库、收集严重度详情、触发模糊推理、解释结果的全流程。

---

## 项目概述

P4 构建了一个完整的 Mamdani 模糊推理引擎——三维模糊输入（覆盖率 + 强度 + 排除度）→ 12 条 IF-THEN 规则 → 重心法去模糊化 → 连续置信度。但 P4 的使用门槛比 P1-P3 更高：用户不仅要传症状列表，还要传 `symptom_details`（体温值、呕吐频率、腹泻类型等），否则推理退化为基线严重度。

**PL4 解决的问题**：让 LLM Agent 自动追问症状详情，将自然语言描述转换为模糊推理所需的连续严重度。

核心思路：

> **用 LLM Agent 充当「模糊化前端」，用户说"猫体温 39.5°C、呕吐了四五次"，Agent 自动提取严重度详情、触发 Mamdani 模糊推理，再把连续置信度翻译成人类可读的诊断报告。**

### 与 PL1-PL3 的对比

| 维度 | PL1-PL3（确定性推理） | PL4（模糊推理） |
|------|----------------------|-----------------|
| 输入 | 症状有/无（二元） | 症状严重度（连续 0-1） |
| 输出 | 确诊/排除（二元） | 置信度 0-1（连续） |
| 排除逻辑 | 命中排除症状 → 完全排除 | 排除症状 → 降低置信度 |
| 追问策略 | 确认有无 | 追问严重度详情 |
| 工具特有 | — | `get_symptom_severity` |
| 工具数量 | 7-8 | 8 |

**关键差异**：PL4 的 Agent 会主动追问症状的严重度详情（"体温多少？""呕吐频率？"），这些详情直接影响模糊推理结果。PL4 还多了 `get_symptom_severity` 工具，让用户看到症状如何从自然语言映射为连续严重度。

---

## 技术架构

### 通用 Agent 框架 + 领域工具注入

```
用户自然语言（含严重度描述）
    ↓
OntologyAgent (agent_core)        ← 与 PL1-PL3 完全相同
  ├── System Prompt (角色定义)
  ├── 8 个 @tool (领域工具)        ← PL4 特有
  └── ConversationState (对话状态)
      ↓ LangGraph ReAct 循环：Think → Act → Observe → Repeat
    ↓
P4 Mamdani 模糊推理引擎 (共享)
  scikit-fuzzy + 12 条 IF-THEN 规则 + 重心法去模糊化
```

### 四个注入点

| 注入点 | PL3 | PL4 |
|--------|-----|-----|
| `tools_factory` | `create_pl3_tools` | `create_pl4_tools` |
| `diagnose_fn` | `pl3_diagnose` | `pl4_diagnose` |
| `report_builder` | `build_pl3_report` | `build_pl4_report` |
| `system_prompt` | SPARQL 诊断助手 | 模糊推理诊断助手 |

---

## 八个工具

PL4 提供 8 个 LangChain `@tool` 工具：

| # | 工具名 | 功能 | 类别 |
|---|--------|------|------|
| 1 | `lookup_symptom_fuzzy` | 在模糊知识库中查找症状，返回关联疾病 + 基线严重度 | 查询 |
| 2 | `lookup_disease_fuzzy` | 查找疾病，返回必要症状、排除症状、物种约束 | 查询 |
| 3 | `add_observation` | 记录症状（含严重度详情，影响推理结果） | 收集 |
| 4 | `set_pet_info` | 设置宠物基本信息 | 收集 |
| 5 | `run_fuzzy_reasoning` | 运行 Mamdani 模糊推理，返回诊断报告 | 推理 |
| 6 | `explain_fuzzy_reasoning` | 解释推理链（覆盖率/强度/排除度 + 规则触发） | 解释 |
| 7 | `get_symptom_severity` | 查询某症状的模糊化严重度（PL4 独有） | 解释 |
| 8 | `get_case_summary` | 返回当前病例摘要（含严重度详情） | 解释 |

---

## 项目结构

```
pl4/
├── README.md           # 本文档
├── __init__.py         # 模块入口
├── run.py              # 启动脚本（交互式对话循环 + 系统提示词）
├── tools.py            # 8 个 LangChain @tool 工具
├── diagnose.py         # 诊断桥接（格式转换 + symptom_details 提取）
└── report.py           # 报告构建（DiagnosisReport + 模糊推理路径说明）

依赖：
├── agent_core/         # 通用 Agent 框架（与 PL1-PL3 共享）
├── P4/                 # 模糊推理引擎（共享）
│   ├── src/reasoner.py       # scikit-fuzzy Mamdani 推理引擎
│   ├── src/kb_builder.py     # CSV + 专家知识 → fuzzy_kb.json
│   ├── src/utils.py          # 严重度计算 + 覆盖率/强度/排除度
│   └── data/fuzzy_kb.json    # 模糊知识库
└── tests/test_pl4.py   # 单元测试
```

---

## 环境准备

### 1. 安装依赖

```bash
cd ontologyops/examples
pip install -r agent_core/requirements.txt
pip install scikit-fuzzy numpy
```

### 2. P4 知识库

```bash
cd P4 && python src/kb_builder.py   # 构建模糊知识库
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
python pl4/run.py
```

### 运行测试

```bash
cd ontologyops/examples
python -m pytest tests/test_pl4.py -v
```

测试覆盖（7 组）：

| 测试组 | 覆盖内容 |
|--------|---------|
| 工具集创建 | `create_pl4_tools` 返回 8 个工具，名称正确 |
| 工具功能 | `add_observation`（含 details）/ `set_pet_info` / `get_case_summary` 正确写入和读取 state |
| 推理前置检查 | 信息不足时 `run_fuzzy_reasoning` 返回提示而非报错 |
| 报告构建 | `build_pl4_report` 生成正确的 `DiagnosisReport`，包含模糊推理说明 |
| Agent 集成 | `OntologyAgent` 创建成功、`reset()` 清空状态、工具与 state 同步 |
| 模糊推理 | `pl4_diagnose` 端到端测试（环境就绪时运行，否则跳过） |
| 格式转换 | `_convert_case_dict` 物种映射 + symptom_details 正确传递 |

---

## 模糊推理 vs 确定性推理的实践影响

```
病例：猫，发热(39.5°C) + 呕吐(多次) + 腹泻(水样暗红)

PL1-PL3（确定性推理）：
  症状 = ["发热", "呕吐", "腹泻"]（二元，严重度信息丢失）
  → 猫瘟：确诊（必要症状全匹配，排除症状未命中）
  → 猫肠炎：排除（排除症状"发热"命中）
  结果：二元，没有灰度

PL4（模糊推理）：
  覆盖率 = 3/3 = 1.0（高）
  强度 = (0.80 + 0.70 + 0.90) / 3 = 0.80（高）
  排除度 = max(0.80, 0) = 0.80（有）  ← 发热是猫肠炎的排除症状
  → 猫瘟：覆盖率=高 ∧ 强度=高 ∧ 排除度=有 → 置信度=中（约0.55）
  → 猫肠炎：不完全排除，置信度降低
  结果：连续置信度，有灰度
```

PL4 保留了严重度信息——39.5°C 的高烧和 38.5°C 的低烧不再是同一个"发热"。

---

## PL 系列路线图

| 编号 | 对应范式 | 推理引擎 | 状态 |
|------|---------|---------|------|
| PL1 | OWL/HermiT 本体推理 | HermiT + SWRL | ✅ 已完成 |
| PL2 | Prolog 逻辑推理 | SWI-Prolog | ✅ 已完成 |
| PL3 | Jena/SPARQL 三元组推理 | Apache Jena + rdflib | ✅ 已完成 |
| **PL4** | **模糊逻辑推理** | **scikit-fuzzy Mamdani** | **✅ 已完成** |
| PL5 | 多范式融合引擎 | 上述全部 | 规划中 |

---

## 参考资料

1. [P4 · 模糊逻辑推理](../P4/README.md) — PL4 的推理引擎基础
2. [PL1 · LLM Agent / OWL 推理](../pl1/README.md) — 对比项目
3. [PL2 · LLM Agent / Prolog 推理](../pl2/README.md) — 对比项目
4. [PL3 · LLM Agent / SPARQL 推理](../pl3/README.md) — 对比项目
5. scikit-fuzzy 文档：https://scikit-fuzzy.readthedocs.io/
6. [PL4 博客文章](https://senlinpubu.top/blog/pl4-fuzzy-agent/) — 完整技术讲解
7. 《当 LLM 不够用了——本体推理的企业决策实践》

---

*作者：森林瀑布 | 项目类型：多范式推理实战营 PL4 | 最后更新：2026-07-13*

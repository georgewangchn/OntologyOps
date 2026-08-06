# PL6 · LLM Agent + 多范式分层仲裁引擎

> **多范式推理实战营 · PL 系列 6/7**
> P1-P5 五种推理引擎 + 分层仲裁 + LLM Agent

## 四注入点实现

| 注入点 | PL6 实现 |
|--------|---------|
| tools_factory | `create_pl6_tools` — 8 个 @tool |
| diagnose_fn | `pl6_diagnose` — 调用 P6 仲裁引擎 |
| report_builder | `build_pl6_report` — DiagnosisReport + 仲裁说明 |
| system_prompt | 多范式仲裁角色定义 |

## 工具列表

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | lookup_symptom_multi | 多引擎知识库中查找症状 |
| 2 | lookup_disease_multi | 多引擎知识表示对比 |
| 3 | add_observation | 记录症状 |
| 4 | set_pet_info | 设置宠物信息 |
| 5 | run_multi_engine_reasoning | 执行多引擎仲裁推理 |
| 6 | **compare_engine_results** | **PL6 独有** — 对比各引擎结果差异 |
| 7 | **explain_arbitration** | **PL6 独有** — 解释仲裁冲突消解逻辑 |
| 8 | get_case_summary | 病例摘要 |

## 完整体系

```
P1 (OWL/HermiT)         → PL1 (Agent + OWL)
P2 (Prolog/SLD)         → PL2 (Agent + Prolog)
P3 (Jena/SPARQL)        → PL3 (Agent + SPARQL)
P4 (Mamdani 模糊)       → PL4 (Agent + Fuzzy)
P5 (朴素贝叶斯)         → PL5 (Agent + Bayesian)
P6 (分层仲裁 P1-P5)     → PL6 (Agent + Arbiter)  ← 本项目
```

## 快速开始

```bash
export OPENAI_API_KEY=your-key
cd examples
python -m pl6.run
```

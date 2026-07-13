# PL5 · LLM Agent + 贝叶斯推理

> **多范式推理实战营 · PL 系列 5/7**
> 将 P5 的朴素贝叶斯推理引擎用 LangGraph Agent 包装，用户用自然语言描述宠物症状，Agent 自动查知识库、收集信息、触发贝叶斯推理、解释后验概率，还能查询先验概率和似然比。

## 四注入点实现

| 注入点 | PL5 实现 |
|--------|---------|
| tools_factory | `create_pl5_tools` — 8 个 @tool |
| diagnose_fn | `pl5_diagnose` — 调用 P5 贝叶斯推理 |
| report_builder | `build_pl5_report` — DiagnosisReport + 贝叶斯说明 |
| system_prompt | 贝叶斯推理角色定义 |

## 工具列表

| # | 工具名 | 说明 |
|---|--------|------|
| 1 | lookup_symptom_bayesian | 查找症状关联疾病 + 条件概率 |
| 2 | lookup_disease_bayesian | 查找疾病先验 + CPT |
| 3 | add_observation | 记录症状 |
| 4 | set_pet_info | 设置宠物信息 |
| 5 | run_bayesian_reasoning | 执行贝叶斯推理 |
| 6 | explain_bayesian_reasoning | 解释推理链（先验→后验） |
| 7 | query_prior_and_likelihood | **PL5 独有** — 查询先验概率和似然比 |
| 8 | get_case_summary | 病例摘要 |

## PL5 vs PL1-PL4 核心差异

| | PL1 | PL2 | PL3 | PL4 | PL5 |
|---|---|---|---|---|---|
| 推理引擎 | OWL/HermiT | Prolog/SWI | Jena/SPARQL | scikit-fuzzy | **朴素贝叶斯** |
| 输出语义 | 确诊/排除 | 确诊/疑似/排除 | 确诊/疑似/排除 | 匹配度 | **后验概率** |
| 先验知识 | 不使用 | 不使用 | 不使用 | 不使用 | **核心输入** |
| 独有工具 | explain_subsumption | query_transmit_chain | query_transitive_closure | get_symptom_severity | **query_prior_and_likelihood** |

## 快速开始

```bash
export OPENAI_API_KEY=your-key
export LLM_MODEL=glm-4.7-flash

cd examples
python -m pl5.run
```

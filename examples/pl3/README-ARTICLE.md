# PL3 · LLM Agent / SPARQL 推理

> 多范式推理实战营 · PL 系列 3/5
> 副标题：当查询即推理 —— SPARQL 的前向链预计算如何被 LLM 解锁

**作者**：森林瀑布 ｜ **博客**：[senlinpubu.top](https://senlinpubu.top/)

---

## 一、引言：P3 很强，但用户还是不会用

P3 展示了第三种推理范式——**把推理内置到查询管线里**。Jena Fuseki 的前向链在数据写入时预计算所有推断结果，SPARQL 查询时自动包含。传递闭包也被预计算为物化视图，查询时直接读取。

但 P3 的使用门槛不比 P1/P2 低：

- 用户要传 `{"pet_type": "cat", "symptoms": ["发热", "呕吐"]}` 这样的 JSON
- 症状名称要精确匹配 RDF 资源的 URI（`http://petbps.com/ontology/pet_disease#发热`）
- 物种要用英文（`cat` / `dog`）
- 如果 Fuseki 没启动，用户要理解 `rdflib` 降级模式

P3 的 SPARQL 查询推理一体化确实强大，但如果用户连 SPARQL 是什么都不知道呢？

**PL3 的核心思路**：

> 用 LLM Agent 充当「翻译层」，用户说自然语言，Agent 自动查 RDF 知识库、收集信息、触发前向链推理，再把结果翻译成人类可读的诊断报告。

LLM 负责「听懂人话」，SPARQL 推理负责「说对话」。

---

## 二、PL3 是怎么把 P3 包装成 Agent 的

### 2.1 四个注入点

PL3 与 PL1/PL2 共享同一个 `agent_core` 框架，区别只在四个注入点：

```python
agent = OntologyAgent(
    tools_factory=create_pl3_tools,    # 8 个 SPARQL 工具
    diagnose_fn=pl3_diagnose,          # 桥接 P3 推理引擎
    report_builder=build_pl3_report,   # 生成诊断报告
    system_prompt=SYSTEM_PROMPT,       # 角色定义
)
```

**不需要改 agent_core 的任何代码**——这是「核心 + 可替换领域层」设计的价值。

### 2.2 八个工具

| # | 工具名 | 功能 |
|---|--------|------|
| 1 | `lookup_symptom_sparql` | 在 RDF 知识库中查找症状 |
| 2 | `lookup_disease_sparql` | 查找疾病详情 |
| 3 | `add_observation` | 记录症状 |
| 4 | `set_pet_info` | 设置宠物信息 |
| 5 | `run_sparql_reasoning` | 运行前向链 + SPARQL 推理 |
| 6 | `explain_reasoning_chain` | 解释推理链（含 OWA 说明） |
| 7 | `query_transitive_closure` | 查询传递闭包（预计算独有） |
| 8 | `get_case_summary` | 病例摘要 |

### 2.3 一次完整的对话

```
用户：我家猫发烧了，还吐了两次

Agent（Think）：用户提到"发烧"和"吐"，需要确认是否是知识库中的症状
Agent（Act）：调用 lookup_symptom_sparql("发热") → 关联猫瘟、猫肠炎
Agent（Act）：调用 lookup_symptom_sparql("呕吐") → 关联猫瘟、猫肠炎
Agent（Act）：调用 set_pet_info(species="猫")
Agent（Act）：调用 add_observation("发热")
Agent（Act）：调用 add_observation("呕吐")

Agent：确认一下，猫咪除了发热和呕吐，还有其他症状吗？比如腹泻？

用户：对，还拉肚子了

Agent（Act）：调用 add_observation("腹泻")
Agent（Act）：调用 run_sparql_reasoning()

Agent：根据 Jena 前向链推理，诊断结果如下：
  1. 猫瘟 — 置信度 100% — ✅确诊
     匹配症状：发热、呕吐、腹泻
  2. 猫肠炎 — 置信度 50% — ⚠️疑似
     匹配症状：呕吐、腹泻

用户：为什么猫肠炎只是疑似？

Agent（Act）：调用 explain_reasoning_chain("猫肠炎")
Agent：猫肠炎的必要症状是腹泻和呕吐（都已观测 ✅），
  但排除症状"发热"也被观测到了 ⚠️。
  在 Jena 前向链规则中，命中排除症状会触发 excluded 三元组，
  因此猫肠炎被标记为排除，不会出现在确诊列表中。
  但在 OWA 下，仍保留为低置信度疑似。
```

---

## 三、SPARQL 查询推理一体化的 Agent 视角

### 3.1 推理时机：预计算 vs 实时计算

PL2（Prolog）的推理是**查询时实时计算**——Agent 调用 `run_prolog_reasoning()` 时，SWI-Prolog 才开始 SLD 归结。

PL3（Jena）的推理是**数据写入时预计算**——Agent 调用 `add_observation()` 时症状三元组就被断言，Jena 前向链立即触发，计算出 `suspected`/`excluded`/`diagnosed` 三元组。当 Agent 调用 `run_sparql_reasoning()` 时，SPARQL 查询直接读取预计算结果。

```
PL2：add_observation → 存储事实 → run_reasoning → SLD 归结 → 结果
PL3：add_observation → 存储三元组 → 前向链自动触发 → run_reasoning → SPARQL 读取预计算结果
```

从 Agent 视角看，PL3 的 `run_sparql_reasoning` 比 PL2 的 `run_prolog_reasoning` 更快——因为推理已经在数据写入时完成了。

### 3.2 传递闭包：预计算 vs 递归

PL2 的 `query_transmit_chain` 使用 Prolog 递归查询传播链——每次查询都要从头递归。

PL3 的 `query_transitive_closure` 直接读取预计算的传递闭包——Jena 的 `TransitiveProperty` 在数据加载时就把所有传递关系算好了。

```python
# PL3 工具：查询传递闭包
@tool
def query_transitive_closure() -> str:
    """查询疾病传播的传递闭包。"""
    graph = _get_graph()
    # 直接遍历 contain 三元组（含传递闭包）
    for a, _, b in graph.triples((None, contain_prop, None)):
        # 不需要递归，预计算已经完成了
        ...
```

这是 P3/PL3 的独特优势：**以空间换时间**——预计算占内存，但查询是 O(1)。

---

## 四、OWA 对 Agent 行为的影响

### 4.1 OWA vs CWA 的 Agent 策略差异

| | PL2（CWA） | PL3（OWA） |
|---|---|---|
| 未观测症状 | = 不存在 | = 尚未检查 |
| 推理影响 | 必要症状缺失 → 无法确诊 | 必要症状缺失 → 仍为疑似 |
| Agent 策略 | 必须完整收集所有症状 | 可以在部分信息下给出低置信度结果 |
| 假阳性风险 | 低（信息不全就不确诊） | 高（信息不全仍可能疑似） |
| 假阴性风险 | 高（信息不全就排除） | 低（信息不全不排除） |

### 4.2 Agent 的追问策略

在 CWA（PL2）下，Agent 必须积极追问——因为少一条症状可能就从"确诊"降为"疑似"。

在 OWA（PL3）下，Agent 可以更"懒"——少一条症状，疾病仍然出现在结果中（只是置信度低）。但这可能导致假阳性增多。

PL3 的系统提示词明确提醒 Agent：

```
## Jena/SPARQL vs Prolog 的区别
- 本系统基于开放世界假设（OWA）：未记录的症状 ≠ 不存在
- 这意味着未观测的症状不会自动排除疾病，只是尚未检查
- 推理结果由 Jena 前向链预计算，SPARQL 查询时自动包含
```

---

## 五、explain_reasoning_chain 的 OWA 说明

PL3 的解释工具与 PL2 有一个微妙但重要的差异——**对未观测症状的说明**：

**PL2（CWA）**：
```
❌ 腹泻（未观测）
CWA 说明：在封闭世界假设下，未观测 = 不存在。
因此这些未观测症状将导致该疾病无法确诊。
```

**PL3（OWA）**：
```
❓ 腹泻（未观测）
OWA 说明：在开放世界假设下，未观测 ≠ 不存在。
未观测的症状可能是尚未检查，因此该疾病仍可能为疑似。
```

同一个"未观测腹泻"事实，在两种世界假设下有完全不同的推理含义。Agent 需要理解这个差异，才能正确解释推理结果。

---

## 六、Fuseki → rdflib 降级策略

P3 设计了 Fuseki 不可用时降级为 rdflib 本地推理的机制。PL3 继承了这个策略：

```python
def pl3_diagnose(case_dict):
    p3_case = _convert_case_dict(case_dict)
    try:
        # 优先使用 Fuseki
        from reasoner import load_knowledge_base, diagnose
        load_knowledge_base()
        raw_results, excluded = diagnose(p3_case)
    except Exception as e:
        # 降级到 rdflib 本地推理
        logger.warning(f"Fuseki 不可用，降级为本地推理：{e}")
        from local_reasoner import diagnose_local
        raw_results, excluded = diagnose_local(p3_case)
    return _format_results(raw_results, excluded, p3_case)
```

对 Agent 来说，这个降级是透明的——无论底层是 Fuseki 还是 rdflib，Agent 调用 `run_sparql_reasoning()` 都能拿到结果。差异只在于推理速度和传递闭包的完整性。

---

## 七、PL1-PL3 横向对比

| 维度 | PL1 | PL2 | PL3 |
|------|------|------|------|
| 推理引擎 | HermiT (Tableau) | SWI-Prolog (SLD) | Jena (前向链) |
| 世界假设 | OWA | CWA | OWA |
| 推理时机 | 查询前一次性 | 查询时实时 | 数据写入时预计算 |
| 传递闭包 | 声明式 | 递归查询 | 预计算物化视图 |
| 工具数 | 7 | 8 (+传播链) | 8 (+传递闭包) |
| 追问策略 | 中等 | 积极 | 中等 |
| 假阳性风险 | 中 | 低 | 中 |
| 假阴性风险 | 中 | 高 | 低 |
| 降级策略 | HermiT 不可用→报错 | pyswip 不可用→手动查询 | Fuseki 不可用→rdflib |

---

## 八、从代码到实践

### 8.1 运行 PL3

```bash
cd ontologyops/examples

# 构建 P3 知识库（如果还没构建）
cd P3 && python src/kb_builder.py && cd ..

# 启动 Agent
python pl3/run.py
```

### 8.2 运行测试

```bash
python -m pytest tests/test_pl3.py -v
```

7 组测试覆盖工具集创建、工具功能、推理前置检查、报告构建、Agent 集成、RDF 推理、格式转换。

---

## 九、小结

PL3 展示了如何将 Jena 前向链 + SPARQL 推理一体化能力包装为 LLM Agent。关键收获：

1. **预计算推理的 Agent 视角**：PL3 的 `run_sparql_reasoning` 比 PL2 的 `run_prolog_reasoning` 更快，因为推理在数据写入时就完成了
2. **传递闭包预计算**：PL3 的 `query_transitive_closure` 不需要递归，直接读取预计算结果
3. **OWA 对 Agent 策略的影响**：PL3 的 Agent 可以更"懒"（少条症状也能给出疑似），但假阳性风险更高
4. **降级策略**：Fuseki → rdflib 的降级对 Agent 是透明的

PL1-PL3 覆盖了三种确定性推理范式（OWL、Prolog、SPARQL），接下来 PL4 将引入不确定性——模糊推理。

---

> **作者**：森林瀑布 ｜ **博客**：[senlinpubu.top](https://senlinpubu.top/) ｜ **GitHub**：[OntologyOps](https://github.com/georgewangchn/OntologyOps)
>
> *本文是「多范式推理实战营」PL 系列第 3 篇。PL1-PL4 覆盖四种推理范式 + LLM Agent 增强，PL5 将实现多范式融合引擎。*

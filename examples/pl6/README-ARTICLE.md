# PL6 · LLM Agent / 贝叶斯元推理

> 多范式推理实战营 · PL 系列 6/7
> 副标题：终章 —— 当三种推理引擎被一个 Agent 统一调度

**作者**：森林瀑布 ｜ **博客**：[senlinpubu.top](https://senlinpubu.top/)

---

## 一、PL6 是什么

PL6 = P6（贝叶斯元推理引擎）+ LLM Agent（LangGraph ReAct 循环）。

这是多范式推理实战营的终章。PL1-PL5 各自展示了单一推理范式的 Agent 化实践，PL6 将三种正交的推理引擎统一调度：

- P2(Prolog) 确定性推理 → 似然比 LR_struct
- P4(Mamdani) 模糊推理 → 似然比 LR_fuzzy
- P5(贝叶斯) 概率推理 → 似然比 LR_bayesian
- 贝叶斯乘法融合 → 归一化后验分布

```
用户：「我的猫又吐又拉还发烧，39.8度」
    ↓  LLM Agent
Agent 自动：
  1. 识别物种 → 猫
  2. 记录症状 → 发热(39.8°C) + 呕吐 + 腹泻
  3. 并行触发三引擎推理：
     P2: 确诊猫瘟（必要症状全匹配）→ LR=5.0
     P4: 置信度0.86（高匹配+高严重度）→ LR=3.2
     P5: 后验91.3%（先验8%被放大11倍）→ LR=18.2
  4. 贝叶斯乘法融合 → P_final = 91.3%
  5. 对比各引擎贡献 + 解释融合逻辑
  6. 返回诊断报告 + 引擎对比
```

---

## 二、从分层仲裁到贝叶斯元推理

PL6 经历了一次重要的架构重构。最初采用的是"分层仲裁"模式，但从第一性原理审视后发现三个结构性缺陷：

1. **P1/P2/P3 知识源冗余**：同一份领域知识的三种编码形式，投票=一人投三票
2. **P4 与 P1-P3 输入空间重叠**：coverage 计算逻辑完全相同，P4 的增量仅为症状严重度
3. **权重 0.6/0.4 无理论依据**：贝叶斯后验和模糊匹配度语义不同，不能加权平均

重构后的贝叶斯元推理模式：
- P1-P3 取其一（P2 Prolog），消除冗余
- 各引擎输出统一转为似然比（LR），语义对齐
- 贝叶斯乘法融合有概率论保证（贝叶斯定理链式法则）

### 为什么用似然比？

三种引擎的输出语义完全不同：
- P2 输出离散判定（确诊/疑似/排除）
- P4 输出模糊匹配度（0-1 连续值）
- P5 输出后验概率（0-1 概率）

不能直接比较或加权。但它们都可以转换为"证据对疾病的支持程度"——即似然比。转换后，乘法融合就有了统一的"货币"。

---

## 三、八个工具

| # | 工具名 | 功能 | PL6 特有 |
|---|--------|------|----------|
| 1 | `lookup_symptom_multi` | 多引擎知识库中查找症状 | ✅ 同时返回三种编码 |
| 2 | `lookup_disease_multi` | 多引擎知识表示对比 | ✅ Prolog + Fuzzy + Bayes |
| 3 | `add_observation` | 记录症状 | 共享 |
| 4 | `set_pet_info` | 设置宠物信息 | 共享 |
| 5 | `run_multi_engine_reasoning` | 执行多引擎融合推理 | ✅ P2+P4+P5 并行 + LR 融合 |
| 6 | `compare_engine_results` | **对比各引擎结果** | ✅ PL6 独有 |
| 7 | `explain_arbitration` | **解释融合逻辑** | ✅ PL6 独有 |
| 8 | `get_case_summary` | 病例摘要 | 共享 |

### compare_engine_results：PL6 独有

让 Agent 能回答："不同引擎对同一个疾病给出了什么似然比？"

```
猫瘟 (最终后验: 91.30% [高概率])
    P2: conf=1.00 [确诊] LR=5.00
    P4: conf=0.86 [高]   LR=3.20
    P5: conf=0.91 [高概率] LR=18.20
    融合：P_prior(0.0500) × LR_P2(5.0) × LR_P4(3.2) × LR_P5(18.2)

猫肠炎 (最终后验: 5.20% [低概率])
    P2: conf=0.00 [排除] LR=0.10
    P4: conf=0.62 [中]   LR=1.80
    P5: conf=0.02 [低概率] LR=0.80
    融合：P_prior(0.0300) × LR_P2(0.1) × LR_P4(1.8) × LR_P5(0.8)
```

### explain_arbitration：PL6 独有

让 Agent 能解释："为什么猫肠炎的 P2 似然比是 0.1 而 P4 是 1.8？"

Agent 调用后返回贝叶斯元推理的完整规则集，包括 LR 映射公式和融合逻辑：

```
贝叶斯元推理规则：

1. 各引擎输出转为似然比（LR）：
   P2 确诊 → LR=5.0（强证据支持）
   P2 疑似 → LR=1.5（弱证据支持）
   P2 排除 → LR=0.1（强证据反对）
   P4: LR = exp(3.0 × (confidence - 0.5))
   P5: LR = posterior / prior（贝叶斯因子）

2. 贝叶斯乘法融合：
   P_final(D) ∝ P_prior(D) × LR_struct × LR_fuzzy × LR_bayesian
   归一化 → 最终后验概率分布

3. 冲突检测：
   如果 max(LR) / min(LR) > 5.0 且方向不一致，标记冲突

猫肠炎分析：
  P2 排除（LR=0.1）：猫肠炎的排除症状"发热"出现 → CWA 下直接排除
  P4 中匹配（LR=1.8）：呕吐+腹泻部分匹配，但发热的严重度高拉高了排除度
  P5 低后验（LR=0.8）：P(发热|猫肠炎)=0.10 很低，大幅拉低似然
  → P2 的强反对（0.1）在乘法中起决定性作用
```

---

## 四、系统提示词设计

PL6 的系统提示词需要让 Agent 理解三个概念：

1. **三引擎并行**：不是选一个用，而是同时运行三个引擎
2. **似然比融合**：各引擎输出转为 LR 后乘法融合，不是加权平均
3. **冲突检测**：各引擎意见不一致时需要提醒用户

```
## 多引擎融合说明
- 本系统同时运行 P2(Prolog)、P4(模糊)、P5(贝叶斯) 三种推理引擎
- 各引擎输出统一转为似然比（LR），以贝叶斯乘法融合
- P_final(D) ∝ P_prior(D) × LR_struct × LR_fuzzy × LR_bayesian
- 这是概率论的链式法则，不是经验加权
- 如果各引擎 LR 方向不一致，会标记冲突，需要提醒用户
```

---

## 五、诊断桥接层

PL6 的 `diagnose.py` 是所有 PL 中最复杂的——它需要同时调用三个引擎：

```python
def pl6_diagnose(case_dict):
    """多引擎融合诊断"""
    p6_case = _convert_case_dict(case_dict)
    
    # P6 引擎内部并行调用 P2/P4/P5
    try:
        from P6.src.reasoner import MetaReasoner
        reasoner = MetaReasoner()
        results = reasoner.diagnose(p6_case)
    except Exception as e:
        # 降级到仅 P5 贝叶斯推理
        logger.warning(f"P6 融合引擎失败，降级为 P5：{e}")
        return _fallback_to_p5(p6_case)
    
    return _format_results(results, p6_case)
```

### 降级策略

PL6 的降级比其他 PL 更复杂——如果 P6 融合引擎失败，降级为仅使用 P5（贝叶斯）：

```python
def _fallback_to_p5(case_dict):
    """P6 失败时降级为 P5 贝叶斯推理"""
    from P5.src.reasoner import BayesianReasoner
    reasoner = BayesianReasoner()
    results = reasoner.diagnose(case_dict)
    return _format_results_single_engine(results, "P5 (fallback)")
```

---

## 六、报告构建

PL6 的 `reasoning_engine` 标注为 `"Bayesian Meta-Reasoner (似然比融合)"`，报告包含独特的多引擎对比信息：

```markdown
### 推理结果

1. ● **猫瘟** — 后验概率 91.30% [高概率]
   融合：P_prior(0.0500) × LR_P2(5.0) × LR_P4(3.2) × LR_P5(18.2)
   
   引擎对比：
   P2 (Prolog):    确诊     conf=1.00  LR=5.00
   P4 (Fuzzy):     高匹配    conf=0.86  LR=3.20
   P5 (Bayesian):  高概率    conf=0.91  LR=18.20

2. ○ **猫肠炎** — 后验概率 5.20% [低概率]
   融合：P_prior(0.0300) × LR_P2(0.1) × LR_P4(1.8) × LR_P5(0.8)
   
   引擎对比：
   P2 (Prolog):    排除     conf=0.00  LR=0.10
   P4 (Fuzzy):     中匹配    conf=0.62  LR=1.80
   P5 (Bayesian):  低概率    conf=0.02  LR=0.80

### 推理路径说明

1. **三引擎并行推理**
   P2(Prolog) 确定性推理 + P4(Mamdani) 模糊推理 + P5(贝叶斯) 概率推理

2. **似然比转换**
   各引擎输出统一转为 LR，语义对齐

3. **贝叶斯乘法融合**
   P_final(D) ∝ P_prior(D) × LR_struct × LR_fuzzy × LR_bayesian
   归一化 → 最终后验概率分布

4. **冲突检测**
   猫肠炎：P2 排除(LR=0.1) vs P4 中匹配(LR=1.8) → 方向不一致
   比值 = 1.8/0.1 = 18.0 > 5.0 → ⚠️ 标记冲突
```

---

## 七、对话流程示例

```
🐾 用户：我家猫39.8度发烧，吐了四五次，拉水样带血的便便

🤖 Agent 自动决策：
  1. set_pet_info(species="猫")
  2. add_observation("发热", details={"value": 39.8})
  3. add_observation("呕吐", details={"frequency": "频繁"})
  4. add_observation("腹泻", details={"type": "水样", "color": "暗红"})
  5. run_multi_engine_reasoning()

## 推理报告

**对象信息**：类型: 猫
**观测记录**：发热(39.8°C)、呕吐(频繁)、腹泻(水样+暗红)

### 推理结果

1. ● **猫瘟** — 后验概率 91.30% [高概率]
   融合：P_prior(5.0%) × LR_P2(5.0) × LR_P4(3.2) × LR_P5(18.2)
   P2: 确诊（必要症状全匹配） LR=5.00
   P4: 高匹配（覆盖率1.0, 强度0.87, 排除度0.0） LR=3.20
   P5: 高概率（先验8%→后验91.3%） LR=18.20

---

🐾 用户：三个引擎对猫瘟的贡献分别是多少？

🤖 Agent（Act）：调用 compare_engine_results("猫瘟")

  猫瘟引擎对比：
    P2 (Prolog):    确诊     LR=5.00   ← 确定性规则全匹配
    P4 (Fuzzy):     高匹配    LR=3.20   ← 症状严重度高（39.8°C高烧）
    P5 (Bayesian):  高概率    LR=18.20  ← 先验8%被放大11倍

  融合效果：5.0 × 3.2 × 18.2 = 291.2（先验被放大291倍）
  归一化后：91.30%

🤖 助手：三个引擎一致支持猫瘟。P5 的贡献最大（LR=18.2），
        因为猫瘟的先验概率（8%）相对较高，且三个必要症状
        的条件概率都在0.80以上。P2 贡献LR=5.0（确定性确诊），
        P4 贡献LR=3.2（高严重度匹配）。乘法融合后，先验5%
        被放大到91.3%。
```

---

## 八、与其他 PL 的对比

| 维度 | PL1-PL5 | PL6 |
|------|---------|-----|
| 引擎数 | 1 | **3（P2+P4+P5 融合）** |
| 融合方式 | 无（单引擎） | **似然比乘法融合** |
| 理论基础 | 各引擎自有 | **贝叶斯定理链式法则** |
| 独有工具 | 各有1个 | **2个（compare + explain）** |
| 冲突检测 | 无 | **LR 方向不一致检测** |
| 降级策略 | 降级到各自fallback | **降级到P5单引擎** |
| 报告内容 | 单引擎结果 | **三引擎对比 + 融合公式** |

---

## 九、完整体系回顾

```
P1 (OWL/HermiT)     → PL1 (Agent + OWL)       确定性 | OWA
P2 (Prolog/SLD)     → PL2 (Agent + Prolog)     确定性 | CWA
P3 (Jena/SPARQL)    → PL3 (Agent + SPARQL)     确定性 | 前向链
P4 (Mamdani 模糊)   → PL4 (Agent + Fuzzy)      不确定性 | 匹配度
P5 (朴素贝叶斯)     → PL5 (Agent + Bayesian)   概率性 | 后验概率
P6 (贝叶斯元推理)   → PL6 (Agent + Meta)       融合性 | 似然比融合
```

6 种推理范式 × (纯推理 + LLM Agent) = **12 个完整项目**，共享同一个 `agent_core` 框架。

### 递进路线

| 阶段 | 范式 | 核心问题 |
|------|------|---------|
| P1-P3 | 确定性推理 | 症状有/无 → 疾病是/否 |
| P4 | 模糊推理 | 症状有多严重 → 匹配度多高 |
| P5 | 概率推理 | 给定症状 → 疾病概率多少 |
| P6 | 多范式融合 | 多引擎意见 → 谁的证据该被采信 |

每一步都引入了前一步无法表达的信息维度。PL1-PL6 让这些推理引擎从"API 调用"变成了"自然语言交互"——用户不需要了解推理引擎的技术细节，只需要描述症状，Agent 自动完成知识查询、信息收集、推理触发、结果解释的全流程。

---

## 十、总结

多范式推理实战营从 P1 的 OWL 本体推理出发，经过 Prolog 逻辑推理、Jena 语义网推理、Mamdani 模糊推理、贝叶斯概率推理，最终在 P6 实现了三种正交范式的贝叶斯元推理融合。

关键洞察：**多引擎融合的前提是各引擎提供正交的增量信息，而非冗余的重复判断。** 似然比是统一不同语义输出的标准工具——无论引擎输出的是二元判定、模糊匹配度还是后验概率，都可以转为 LR，然后以贝叶斯乘法融合。

LLM Agent（PL1-PL6）让这些推理引擎从"API 调用"变成了"自然语言交互"，用户不需要了解推理引擎的技术细节，只需要描述症状，Agent 自动完成知识查询、信息收集、推理触发、结果解释的全流程。

PL6 的 Agent 比前五个 PL 多了一层职责——不仅解释单个引擎的结果，还要解释**三个引擎如何融合**、**各自的贡献是多少**、**有没有冲突**。这让 Agent 从"翻译器"升级为"仲裁解释器"。

---

> **作者**：森林瀑布 ｜ **博客**：[senlinpubu.top](https://senlinpubu.top/) ｜ **GitHub**：[OntologyOps](https://github.com/georgewangchn/OntologyOps)
>
> *本文是「多范式推理实战营」PL 系列第 6 篇，也是终章。PL1-PL6 覆盖五种推理范式 + LLM Agent 增强 + 多范式证据融合。*

# PL5 · LLM Agent / 贝叶斯推理

> 多范式推理实战营 · PL 系列 5/7  
> 副标题：从模糊匹配到概率推理 —— Agent 如何理解「后验概率91.3%」

**作者**：森林瀑布 ｜ **博客**：[senlinpubu.top](https://senlinpubu.top/) ｜ **最后更新**：2026-07-01

---

## 一、引言：P5 有概率论保证，但用户不懂概率

P5 引入了第五种推理范式——**贝叶斯概率推理**。与 P4 的模糊匹配不同，P5 的输出是后验概率：不是"匹配度高"，而是"给定症状，猫瘟的概率是91.3%"。有先验概率、有条件概率表、有贝叶斯定理的数学保证。

但 P5 的使用门槛有其独特性：

- 用户不需要传 `symptom_details`（贝叶斯用二元症状，不需要严重度）—— 这点比 P4 简单
- 但用户需要理解"后验概率"的含义 —— 这点比 P4 难
- 先验概率和条件概率表是 P5 的核心知识源，但用户看不到、也不理解

> **患者**：「医生，你说猫瘟概率91.3%，猫肠炎8.3%——为什么差这么多？」  
> **医生**：「因为猫瘟的先验概率（8%）是猫肠炎（6%）的1.3倍，而且猫肠炎的排除症状'发热'出现了，P(发热|猫肠炎)只有0.10，大幅拉低了似然。」  
> **患者**：「……能说人话吗？」

**PL5 的核心思路**：

> 用 LLM Agent 充当「概率翻译层」——用户说自然语言，Agent 自动查贝叶斯知识库、收集症状、触发概率推理，再把后验概率和似然比翻译成人类可读的解释。

PL4 的 Agent 负责"模糊化"——把程度描述转为严重度。PL5 的 Agent 负责"概率化"——把二元症状转为后验概率，并解释为什么这个概率高、那个低。

---

## 二、与 PL1-PL4 的核心差异

```
维度              PL1-PL3                 PL4                     PL5
推理输出          确诊/排除（二元）       置信度（匹配度）         后验概率
先验知识          不使用                  不使用                   核心输入
负证据            不考虑未出现的症状      不考虑未出现的症状       P(¬S|D) 降低后验
罕见病处理        与常见病同等            与常见病同等             先验天然压低
独有工具          —                       get_symptom_severity     query_prior_and_likelihood
Agent 追问重点    症状有无                症状严重度               症状有无（不追问严重度）
```

### PL4 vs PL5：模糊匹配 vs 概率推理

PL4 的 Agent 会追问症状严重度（"体温多少度？""呕吐频率？"），因为模糊推理需要连续输入。

PL5 的 Agent 不需要追问严重度——贝叶斯推理用的是二元症状（有/无）。但 PL5 的 Agent 有一个 PL4 没有的能力：**查询先验概率和似然比**，让用户理解"为什么这个病概率高"。

---

## 三、工具集

PL5 暴露 8 个 @tool 给 Agent：

```
工具                              功能                              对应 PL4
lookup_symptom_bayesian           查找症状关联疾病 + P(S|D)         lookup_symptom_fuzzy
lookup_disease_bayesian           查找疾病先验 + CPT                lookup_disease_fuzzy
add_observation                   记录症状（二元，不需严重度）      add_observation（需严重度）
set_pet_info                      设置宠物信息                      相同
run_bayesian_reasoning            执行贝叶斯推理                    run_fuzzy_reasoning
explain_bayesian_reasoning        解释推理链（先验→似然→后验）      explain_fuzzy_reasoning
query_prior_and_likelihood        查询先验概率和似然比（PL5独有）   无对应
get_case_summary                  病例摘要                          相同
```

### query_prior_and_likelihood（PL5 独有）

这个工具让 Agent 能回答用户的问题："为什么猫瘟的概率比猫肠炎高？"

Agent 调用后会返回：

```
猫瘟 (D001):
  先验概率 P(D) = 8.00%
  各症状似然比：
    发热: LR = 6.0x （强支持证据）
    呕吐: LR = 8.5x （强支持证据）
    腹泻: LR = 6.7x （强支持证据）
    咳嗽: LR = 0.3x （强反对证据）
    流鼻涕: LR = 0.2x （强反对证据）
```

似然比 LR = P(S|D) / P(S|¬D) 的解读：

```
LR 范围      含义
LR > 10      强支持证据
LR > 3       中等支持证据
LR < 0.3     强反对证据
LR < 1       弱反对证据
```

这个工具是 PL5 的核心差异化能力。PL4 的 `get_symptom_severity` 让用户看到"39.8°C 如何变成 0.80"，PL5 的 `query_prior_and_likelihood` 让用户看到"为什么猫瘟的概率是91.3%"——两者都在让推理从黑盒变白盒，但维度不同。

---

## 四、系统提示词设计

PL5 的系统提示词强调三个 PL4 没有的概念：

1. **后验概率语义**："你的输出是后验概率，不是匹配度或模糊值"
2. **先验概率作用**："先验概率让常见病天然占优"
3. **负证据**："未出现的症状也参与推理（通过 P(¬S|D) 降低后验）"

同时明确告知 Agent：贝叶斯推理**不需要症状严重度**（与 PL4 不同），只需要症状有/无。

```
## 贝叶斯推理 vs 模糊推理的区别
- 本系统基于贝叶斯定理，输出后验概率（0-1），不是模糊匹配度
- 不需要症状严重度，只需要症状有/无
- 先验概率让常见病天然占优（猫感冒 P=0.12 > 猫艾滋 P=0.01）
- 未出现的症状也参与推理：通过 P(¬S|D) 降低后验概率
```

---

## 五、诊断桥接层

`diagnose.py` 的 `_convert_case_dict` 比 PL4 简单——不需要提取 `symptom_details`：

```python
# PL4: 需要提取 symptom_details（症状严重度详情）
p4_case["symptom_details"] = case_dict.get("symptom_details", {})

# PL5: 只需要二元症状
p5_case["symptom_type"] = _SPECIES_MAP.get(raw_type, raw_type)
p5_case["symptoms"] = case_dict.get("observations", [])
```

降级策略与 PL1-PL4 一致：当 P5 推理引擎失败时，`_fallback_diagnose` 手动实现朴素贝叶斯计算（先验 × 似然 → 归一化）。

### 降级诊断的具体实现

```python
def _fallback_diagnose(case_dict):
    """P5 引擎失败时的降级：手动计算朴素贝叶斯"""
    symptoms = case_dict.get("symptoms", [])
    pet_type = case_dict.get("pet_type", "")
    
    results = []
    for disease_id, disease_info in DISEASE_PRIORS.items():
        if disease_info["species"] != pet_type:
            continue
        prior = disease_info["prior"]
        likelihood = prior
        for s in disease_info["cpt"]:
            if s in symptoms:
                likelihood *= disease_info["cpt"][s]["present"]
            else:
                likelihood *= (1 - disease_info["cpt"][s]["present"])
        results.append((disease_info["name"], likelihood, disease_id))
    
    # 归一化
    total = sum(r[1] for r in results)
    results = [(r[0], r[1]/total, r[2]) for r in results]
    return sorted(results, key=lambda x: -x[1])
```

---

## 六、报告构建

PL5 的 `reasoning_engine` 标注为 `"Naive Bayes (贝叶斯网络)"`，disclaimer 强调：

> 后验概率基于先验概率和条件概率表计算，具有严格的概率论语义。结果表示"给定症状时疾病的概率"，而非症状匹配程度。

### 推理路径说明

报告中的推理路径分为四步：

```
1. 先验概率
   每种疾病有先验 P(D)，来自流行病学统计。
   猫瘟 P(D)=8%，猫感冒 P(D)=12%。

2. 似然计算
   P(D|S) ∝ P(D) × ∏ P(Sᵢ|D) × ∏ P(¬Sⱼ|D)
   已出现症状乘以 P(S|D)，未出现症状乘以 P(¬S|D)。

3. 归一化
   所有疾病的后验值除以总和，得到概率分布。

4. 负证据
   未出现的症状也参与推理——这是与 P1-P4 的核心区别。
```

---

## 七、对话流程示例

```
🐾 用户：我家猫发热、呕吐、腹泻

🤖 Agent 自动决策：
  1. set_pet_info(species="猫")
  2. lookup_symptom_bayesian("发热") → 关联猫瘟、猫肠炎、猫艾滋
  3. add_observation("发热")
  4. add_observation("呕吐")
  5. add_observation("腹泻")
  6. get_case_summary() → ✅ 信息已足够
  7. run_bayesian_reasoning()

## 推理报告

**对象信息**：类型: 猫
**观测记录**：发热、呕吐、腹泻

### 推理结果

1. ● **猫瘟** — 后验概率 91.32% [高概率]
   先验：8.00% → 后验：91.32%（似然比 11.41x）
   证据：发热(P(S|D)=0.90)、呕吐(P(S|D)=0.85)、腹泻(P(S|D)=0.80)
   反证据：咳嗽未出现(P(¬S|D)=0.95)、流鼻涕未出现(P(¬S|D)=0.97)

2. ○ **猫肠炎** — 后验概率 8.31% [低概率]
   先验：6.00% → 后验：8.31%

---

🐾 用户：为什么猫肠炎只有8%？

🤖 Agent（Act）：调用 query_prior_and_likelihood("猫肠炎")

  猫肠炎 (D003):
    先验概率 P(D) = 6.00%
    各症状似然比：
      发热: LR = 0.3x （强反对证据）← 排除症状出现
      呕吐: LR = 8.5x （强支持证据）
      腹泻: LR = 6.7x （强支持证据）

🤖 助手：猫肠炎的先验概率只有6%，而且它的排除症状"发热"
        出现了。P(发热|猫肠炎)只有0.10，这意味着猫肠炎
        患者出现发热的概率很低。发热这个症状对猫肠炎的
        似然比只有0.3x——强反对证据。虽然呕吐和腹泻支持
        猫肠炎，但发热的反对力度太大，综合后验只有8.31%。
```

---

## 八、PL1-PL5 横向对比

```
维度          PL1                 PL2                     PL3                         PL4                 PL5
推理引擎      HermiT              SWI-Prolog              Jena                        scikit-fuzzy        朴素贝叶斯
输出语义      确诊/排除           确诊/疑似/排除          确诊/疑似/排除              匹配度              后验概率
先验知识      不使用              不使用                  不使用                      不使用              核心输入
负证据        无                  无                      无                          无                  P(¬S|D)
独有工具      explain_subsumption query_transmit_chain    query_transitive_closure    get_symptom_severity query_prior_and_likelihood
追问策略      症状有无            症状有无                症状有无                    症状严重度          症状有无
工具数        7                   8                       8                           8                   8
```

---

## 九、总结

PL5 完成了从"模糊匹配"到"概率推理"的跨越。五种 PL 的递进路线：

```
阶段      范式                  核心能力
PL1-PL3   确定性推理 + Agent     不同知识表示，同一确定性本质
PL4       模糊推理 + Agent       处理"边缘模糊"，不处理概率
PL5       概率推理 + Agent       处理"概率不确定性"，有严格数学基础
```

PL5 的 Agent 有两个独特价值：

1. **概率翻译**：把"后验概率91.3%"翻译成用户能理解的语言——"先验8%被放大了11倍，因为发热、呕吐、腹泻三个症状都是强支持证据"
2. **先验透明**：通过 `query_prior_and_likelihood` 工具，用户可以查看每种疾病的先验概率和每个症状的似然比，理解"为什么这个病概率高"

下一步 PL6 将实现**多范式融合引擎**——将 P2(Prolog)、P4(模糊)、P5(贝叶斯) 三种正交推理结果通过似然比融合为最终诊断。

---

**项目链接**：[github.com/georgewangchn/OntologyOps/tree/main/ontologyops/examples/pl5](https://github.com/georgewangchn/OntologyOps/tree/main/examples/pl5)

**PL4 对比**：[PL4 · 模糊推理 Agent](../pl4/README-ARTICLE.md)

**PL6 延伸**：[PL6 · 元推理 Agent](../pl6/README-ARTICLE.md)

**书籍全书**：[《当 LLM 不够用了——本体推理的企业决策实践》在线阅读](https://senlinpubu.top/book/)

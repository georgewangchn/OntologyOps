# P1 · 宠物疾病本体推理系统

> 多范式推理实战营 · 项目 1/6  
> 副标题：当 LLM 不够用时，如何让「症状 → 疾病」的推理可验证

**作者**：森林瀑布 ｜ **GitHub 仓库**：[georgewangchn/OntologyOps](https://github.com/georgewangchn/OntologyOps) 

---

## 一、引言：为什么需要本体推理？

当你带着宠物去医院，医生询问症状后迅速给出诊断——这背后是一套**符号推理**过程：

> **患者**：「医生，我的猫又吐又拉，还发烧。」  
> **医生**：「呕吐 + 腹泻 + 发热，首先考虑猫瘟或猫肠胃炎。做过血常规吗？」

这套推理过程，如果交给 LLM（大语言模型），会出现什么问题？

| 维度 | LLM 方案 | 本体推理方案 |
|------|----------|--------------|
| 推理可解释性 | ❌ 黑盒，无法追溯推理链 | ✅ 每一步推理都有逻辑依据 |
| 结果一致性 | ❌ 同一输入可能输出不同结果 | ✅ 相同输入必然得到相同结果 |
| 知识更新 | ❌ 需要重新训练或微调 | ✅ 直接修改本体，立即生效 |
| 合规性 | ❌ 无法满足医疗审计要求 | ✅ 推理链完整记录，可审计 |

这正是《当 LLM 不够用了——本体推理的企业决策实践》一书的核心论点：**在企业关键决策场景中，我们需要的不是「看起来对」的概率生成，而是「必定对」的可验证推理。**

本项目（P1）用一个**真实落地的宠物医疗 CDSS（临床决策支持系统）**作为案例，展示本体推理的完整工作流程。

---

## 二、技术架构：三层推理 + 排除过滤

P1 采用三层推理架构，每层解决不同的问题：

```
┌─────────────────────────────────────────────────┐
│           输入：病例（症状列表）                │
│         例：["发热", "呕吐", "腹泻"]             │
└──────────────────────┬──────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│  Layer 1：OWL 分类（equivalent_to 双向推理）    │
│  - HermiT 根据「充要条件」从症状反推疾病类      │
│  - 精确匹配：症状全满足 → 确定推断疾病          │
└──────────────────────┬──────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│  Layer 2：SWRL 规则（部分匹配 → 疑似候选）      │
│  - 规则1：必要症状匹配 → suspected             │
│  - 模糊补充：部分症状匹配也能捕获候选           │
└──────────────────────┬──────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│  Layer 3：排除过滤（SWRL + Python 双重排除）    │
│  - 规则2：排除症状 → excluded                   │
│  - Python 检查：nos 注解命中 → 移除             │
└──────────────────────┬──────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│    输出：疑似疾病列表（按置信度排序）           │
│    例：猫瘟(0.99) > 犬细小病毒(0.77)            │
└─────────────────────────────────────────────────┘
```

### 2.1 三层知识编码

疾病诊断知识从 CSV 加载后，编码为三层 OWL 公理。以 D001 猫瘟（必要症状：发热、呕吐、腹泻；排除症状：咳嗽、流鼻涕）为例：

**第一层 — 推理层（`equivalent_to`，充要条件）**

```python
# D001 ≡ 疾病 ∧ has.value(发热) ∧ has.value(呕吐) ∧ has.value(腹泻)
d.equivalent_to.append(
    onto.疾病 & onto.has.value(发热) & onto.has.value(呕吐) & onto.has.value(腹泻)
)
```

这是**双向推理**的关键——HermiT 可以从"病例 has 这些症状"反推"病例 rdf:type D001"。

**第二层 — 元数据层（`SubClassOf` + `comment`）**

```python
# necessary.value 限制（供置信度计算解析）
d.is_a.append(onto.necessary.value(发热))
d.is_a.append(onto.necessary.value(呕吐))
d.is_a.append(onto.necessary.value(腹泻))
# 排除症状存入 comment 注解（供 Python 排除检查解析）
d.comment.append("nos:咳嗽;流鼻涕")
```

**第三层 — SWRL 层（疾病知识个体）**

```python
# 创建 D001_kb 个体，断言实例级 necessary / nos 属性
d_kb = onto.疾病("D001_kb")
d_kb.necessary.append(发热)
d_kb.necessary.append(呕吐)
d_kb.necessary.append(腹泻)
d_kb.nos.append(咳嗽)
d_kb.nos.append(流鼻涕)
```

为什么要第三层？因为 SWRL 规则 `necessary(?d, ?s)` 匹配的是**实例级属性断言**（ABox triple `?d necessary ?s`），而疾病类本身是 TBox 概念，不是个体，无法被 SWRL 匹配。`D001_kb` 等个体提供了实例级断言，使 SWRL 规则可触发。

### 2.2 SWRL 规则推理

OWL 的表达能力有限（它是描述逻辑 `SHOIN(D)`），无法表达某些推理，比如：

> 「如果出现症状 X，且 X 在疾病 D 的**排除症状**列表中，则排除疾病 D」

这时需要 SWRL（Semantic Web Rule Language）：

```swrl
// 规则1：必要症状匹配 → 疑似疾病
has(?p, ?s) ∧ necessary(?d, ?s) ∧ 疾病(?d) ∧ 症状(?s)
→ suspected(?p, ?d)

// 规则2：排除性症状 → 排除疾病
has(?p, ?s) ∧ nos(?d, ?s) ∧ 疾病(?d) ∧ 症状(?s)
→ excluded(?p, ?d)
```

在 owlready2 中，SWRL 规则通过 `Imp` 类实现：

```python
from owlready2 import *

with onto:
    rule1 = Imp()
    rule1.label.append("necessary_symptom_rule")
    rule1.set_as_rule("""
        has(?p, ?s), necessary(?d, ?s),
        疾病(?d), 症状(?s)
        -> suspected(?p, ?d)
    """)
```

> 📝 这些规则依赖第三层的疾病知识个体（`D001_kb` 等）提供实例级断言。没有这些个体，`necessary(?d, ?s)` 无法匹配，规则不会触发。

### 2.3 推理机（HermiT）

OWL 本体的推理复杂度是 `NExpTime`，需要专门的 Tableau 算法推理机。本项目选用 **HermiT**：

| 推理机 | 特点 | 本项目选择 |
|--------|------|-------------|
| **HermiT** | 纯 Java，OWL 2 完整支持，速度中等 | ✅ 默认选择 |
| Pellet | 支持更多推理类型，速度较快 | 备选 |
| JFact | 专注于分类推理，速度快 | 仅分类时用 |

```python
# 调用 HermiT 推理机
from owlready2 import sync_reasoner_hermit

with onto:
    sync_reasoner_hermit([onto], infer_property_values=True, debug=0)

# 推理后，case_instance 会被自动分类到匹配的疾病类
```

---

## 三、实现细节

### 3.1 本体构建（onto_builder.py）

核心类与属性设计：

```python
from owlready2 import *

onto = get_ontology("http://petbps.com/ontology/pet_disease")

with onto:
    # 核心类
    class 疾病(Thing): pass
    class 症状(Thing): pass
    class 物种(Thing): pass

    # 对象属性
    class has(ObjectProperty):
        domain = [疾病]
        range  = [症状]

    class necessary(ObjectProperty):
        domain = [疾病]
        range  = [症状]

    class nos(ObjectProperty):
        domain = [疾病]
        range  = [症状]

    # SWRL 规则推断属性
    class suspected(ObjectProperty):
        domain = [Thing]
        range  = [疾病]

    class excluded(ObjectProperty):
        domain = [Thing]
        range  = [疾病]
```

### 3.2 三层知识编码（从 CSV 加载）

疾病数据存储在 CSV 文件中：

```csv
疾病ID,疾病名称,物种,必要症状,排除症状,充分症状
D001,猫瘟,cat,发热;呕吐;腹泻,咳嗽;流鼻涕,白细胞减少
D002,猫感冒,cat,打喷嚏;流鼻涕,发热;呕吐,
D003,猫肠炎,cat,腹泻;呕吐,发热;咳嗽,
D004,犬细小病毒,dev,呕吐;腹泻;精神萎靡,咳嗽;,白细胞减少
...
```

加载与三层编码代码：

```python
import pandas as pd

def add_symptom_relations(onto, csv_path):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    with onto:
        for _, row in df.iterrows():
            d = onto[row["疾病ID"]]

            # ── 必要症状 ──────────────────────
            nec_symptoms = []
            for sname in row["必要症状"].split(";"):
                s_ind = onto[sname.strip()]
                nec_symptoms.append(s_ind)
                # 第二层：SubClassOf 元数据
                d.is_a.append(onto.necessary.value(s_ind))

            # 第一层：equivalent_to 充要条件
            expr = onto.疾病
            for s_ind in nec_symptoms:
                expr = expr & onto.has.value(s_ind)
            d.equivalent_to.append(expr)

            # ── 排除症状 ──────────────────────
            nos_symptoms = []
            for sname in row["排除症状"].split(";"):
                s_ind = onto[sname.strip()]
                nos_symptoms.append(s_ind)
                d.is_a.append(onto.nos.max(0, s_ind))
            # 排除症状存入 comment 注解
            d.comment.append("nos:" + ";".join(s.name for s in nos_symptoms))

            # ── 第三层：疾病知识个体 ──────────
            d_kb = onto.疾病(row["疾病ID"] + "_kb")
            for s_ind in nec_symptoms:
                d_kb.necessary.append(s_ind)
            for s_ind in nos_symptoms:
                d_kb.nos.append(s_ind)
```

### 3.3 诊断推理主流程（reasoner.py）

```python
def diagnose(onto, case_dict):
    """
    case_dict 格式：
    {
        "pet_type": "cat",
        "symptoms": ["发热", "呕吐", "腹泻"],
        "breed": "英短",
        "age": 2
    }
    """
    # 0. 嵌入 SWRL 规则
    onto = apply_swrl_rules(onto)

    with onto:
        # 1. 创建病例个体，断言症状
        case_instance = Thing("case_001")
        for sname in case_dict["symptoms"]:
            case_instance.has.append(onto[sname])

    # 2. HermiT 推理（OWL 分类 + SWRL 规则）
    sync_reasoner_hermit([onto], infer_property_values=True, debug=0)

    # 3. 第一层：OWL 分类结果
    results = []
    for cls in onto.疾病.descendants():
        if case_instance in cls.instances():
            results.append((cls, _calc_confidence(cls, case_dict, onto)))

    # 4. 第二层：SWRL 补充的疑似候选
    for d_kb in case_instance.suspected:
        disease_cls = _map_kb_to_class(d_kb, onto)  # D001_kb → D001
        if disease_cls and disease_cls not in existing:
            results.append((disease_cls, _calc_confidence(...)))

    # 5. 第三层：排除过滤
    excluded = {_map_kb_to_class(d, onto) for d in case_instance.excluded}
    filtered = [(c, f) for c, f in results
                if c not in excluded
                and not (case_symptoms & set(_get_exclusion_symptoms(c)))]

    # 6. 清理 + 排序
    destroy_entity(case_instance)
    return sorted(filtered, key=lambda x: x[1], reverse=True)
```

---

## 四、运行示例

输入一个病例：

```python
case = {
    "pet_type": "cat",
    "symptoms": ["发热", "呕吐", "腹泻"],
    "breed": "英短",
    "age": 2
}

results = diagnose(onto, case)
print_diagnosis(results)
```

输出：

```
──────────────────────────────────────────────────
  📋 诊断结果（按置信度排序）
──────────────────────────────────────────────────
  1. 猫瘟                   置信度：0.99  █████████
  2. 犬细小病毒                置信度：0.77  ███████
──────────────────────────────────────────────────
```

### 推理链完整追溯

```
① OWL 分类（equivalent_to 双向推理）
   ├─ D001(猫瘟)   ← has(发热)✓ has(呕吐)✓ has(腹泻)✓  → 3/3 充要条件满足
   ├─ D003(猫肠炎) ← has(腹泻)✓ has(呕吐)✓              → 2/2 充要条件满足
   └─ D006(犬冠状) ← has(呕吐)✓ has(腹泻)✓              → 2/2 充要条件满足

② SWRL 补充（规则1：必要症状匹配 → 疑似）
   ├─ D004(犬细小) ← necessary(呕吐)✓ necessary(腹泻)✓  → 2/3 匹配
   └─ D009(猫艾滋) ← necessary(发热)✓                    → 1/2 匹配

③ 排除过滤（规则2 + Python 检查）
   ├─ D003(猫肠炎) ← nos(发热)✓ 命中 → 排除
   ├─ D006(犬冠状) ← nos(发热)✓ 命中 → 排除
   ├─ D009(猫艾滋) ← nos(腹泻)✓ 命中 → 排除
   ├─ D002(猫感冒) ← nos(发热)✓ + nos(呕吐)✓ → 排除（SWRL）
   ├─ D005(犬感冒) ← nos(呕吐)✓ + nos(腹泻)✓ → 排除（SWRL）
   ├─ D007(猫尿感) ← nos(腹泻)✓ → 排除（SWRL）
   ├─ D008(犬尿感) ← nos(腹泻)✓ → 排除（SWRL）
   └─ D010(犬副流) ← nos(腹泻)✓ → 排除（SWRL）

④ 最终结论
   → 猫瘟（0.99）> 犬细小病毒（0.77）
```

---

## 五、与 LLM 方案对比

我们用同一个病例，分别测试 LLM 方案和本体推理方案：

| 维度 | LLM 方案（GPT-4） | 本体推理方案 |
|------|-------------------|--------------|
| 输入 | 「我的猫又吐又拉，还发烧」 | `symptoms: ["发热", "呕吐", "腹泻"]` |
| 输出 | 「可能是猫瘟或肠胃炎，建议就医」 | 猫瘟（0.99）> 犬细小病毒（0.77） |
| 推理链 | ❌ 无法提供 | ✅ 三层推理完整追溯 |
| 可验证性 | ❌ 黑盒 | ✅ 每一步都有 OWL/SWRL 公理依据 |
| 一致性 | ❌ 同一输入可能不同输出 | ✅ 相同输入必定相同输出 |
| 耗时 | 2-5 秒（API 调用） | 0.3 秒（本地推理） |

> **结论**：在医疗诊断这类关键决策场景中，本体推理的**可验证性、一致性、低延迟**是 LLM 无法替代的。

---

## 六、教学效果：从代码到原理

本项目作为《当 LLM 不够用了》的配套实战案例，对应以下章节：

| 本书章节 | 本项目对应内容 |
|----------|----------------|
| 第一章 本体论是什么 | `src/onto_builder.py`：OWL 类、属性、层次结构设计 |
| 第二章 企业为什么需要本体推理 | `data/` 中的症状-疾病数据，展示「数据富裕、知识贫困」问题 |
| 第四章 技术推理的技术基础设施 | `src/reasoner.py`：Tableau 推理机（HermiT）调用 |
| 第七章 国内实践 | 本项目即国内宠物医疗领域的真实实践案例 |

**学习路径**：

1. **第一周**：理解 OWL 本体建模（类、属性、三层知识编码）
2. **第二周**：掌握 SWRL 规则编写（Imp 类、set_as_rule、疾病知识个体）
3. **第三周**：运行完整诊断流程，分析三层推理链
4. **第四周**：扩展本体（增加疾病、症状、规则）

---

## 七、总结

本体推理不是要**取代** LLM，而是在 LLM **不够用**的场景中提供确定性的推理能力：

| 场景 | 推荐方案 |
|------|----------|
| 开放域对话、创意生成 | ✅ LLM |
| 医疗诊断、金融风控、法律推理 | ✅ 本体推理 + LLM 辅助 |
| 需要审计轨迹的决策 | ✅ 本体推理（必须） |

> 「让 LLM 做它擅长的，让本体推理做它必须的。」  
> —— 《当 LLM 不够用了——本体推理的企业决策实践》

---

**项目链接**：[github.com/georgewangchn/OntologyOps/tree/main/ontologyops/examples/P1](https://github.com/georgewangchn/OntologyOps/tree/main/examples/P1)

**在线阅读**：[georgewangchn.github.io/OntologyOps/examples/P1/](https://georgewangchn.github.io/OntologyOps/examples/P1/)

**书籍全书**：[《当 LLM 不够用了——本体推理的企业决策实践》在线阅读](https://georgewangchn.github.io/OntologyOps/book/)

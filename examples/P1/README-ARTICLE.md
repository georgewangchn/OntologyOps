# P1 · 宠物疾病本体推理系统

> 多范式推理实战营 · 项目 1/6  
> 副标题：当 LLM 不够用时，如何让「症状 → 疾病」的推理可验证

**作者**：森林瀑布 ｜ **GitHub 仓库**：[georgewangchn/OntologyOps](https://github.com/georgewangchn/OntologyOps) ｜ **最后更新**：2026-06-21

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

## 二、技术架构：OWL + SWRL + HermiT

P1 采用三层推理架构：

```
┌─────────────────────────────────────────────┐
│         输入：病例（症状列表）            │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  Layer 1：OWL 本体推理（必要条件匹配）    │
│  - 用 OWL 属性限制表达「必要症状」       │
│  - HermiT 推理机执行 Tableau 算法        │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  Layer 2：SWRL 规则推理（跨属性推理）     │
│  - 用 SWRL 规则表达「排除症状」          │
│  - owlready2.Imp 执行规则匹配            │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  输出：疑似疾病列表（按置信度排序）       │
└─────────────────────────────────────────────┘
```

### 2.1 OWL 本体建模

OWL（Web Ontology Language）是 W3C 推荐的本体表示语言。我们用它形式化宠物疾病领域知识：

```python
# 类层次结构
疾病 ⊃ 猫瘟
疾病 ⊃ 犬细小病毒
疾病 ⊃ 猫感冒

症状 ⊃ 发热
症状 ⊃ 呕吐
症状 ⊃ 腹泻
症状 ⊃ 咳嗽
```

> ⚠️ **注意**：`A ⊃ B` 在 OWL 中表示「A 是 B 的子类」（A SubClassOf B）。  
> 发热、呕吐、腹泻是**并列关系**，各自独立继承「症状」，并非继承链。

关键在于如何用 OWL 表达「罹患某病必须具备的症状」：

```python
# 用 owlready2 实现
with onto:
    class 猫瘟(疾病):
        equivalent_to = [
            has_symptom.some(发热) &
            has_symptom.some(呕吐) &
            has_symptom.some(腹泻)
        ]
```

这段代码的语义是：

> **「猫瘟」等价于「疾病 且 有症状 发热 且 有症状 呕吐 且 有症状 腹泻」**
> 
> 这是一个 `EquivalentTo` 声明，意味着：
> 1. 如果一个个体满足这三个症状，推理机会推断它属于「猫瘟」类；
> 2. 反之，如果一个个体被分类为「猫瘟」，则它必然有这三个症状。

### 2.2 SWRL 规则推理

OWL 的表达能力有限（它是描述逻辑 `SHOIN(D)`），无法表达某些推理，比如：

> 「如果出现症状 X，且 X 在疾病 D 的**排除症状**列表中，则排除疾病 D」

这时需要 SWRL（Semantic Web Rule Language）：

```python
# 规则1：必要症状全匹配 → 疑似疾病
has(?p, ?s) ∧ necessary(?d, ?s) → suspected(?p, ?d)

# 规则2：排除性症状 → 排除疾病
has(?p, ?s) ∧ nos(?d, ?s) → excluded(?p, ?d)
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

### 2.3 推理机（HermiT）

OWL 本体的推理复杂度是 `NExpTime`，需要专门的 Tableau 算法推理机。本项目选用 **HermiT**：

| 推理机 | 特点 | 本项目选择 |
|--------|------|-------------|
| **HermiT** | 纯 Java，OWL 2 完整支持，速度中等 | ✅ 默认选择 |
| Pellet | 支持更多推理类型，速度较快 | 备选 |
| JFact | 专注于分类推理，速度快 | 仅分类时用 |

```python
# 调用 HermiT 推理机
from owlready2 import *

onto = get_ontology("pet_ontology.owl").load()

with onto:
    sync_reasoner(HermiT, infer_property_values=True)

# 推理后，case_instance 会被自动分类到合适的疾病类
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
        domain = [Thing]
        range = [症状]

    class necessary(ObjectProperty):
        domain = [疾病]
        range = [症状]

    class nos(ObjectProperty):
        domain = [疾病]
        range = [症状]

    class suspected(ObjectProperty):
        domain = [Thing]
        range = [疾病]

    class excluded(ObjectProperty):
        domain = [Thing]
        range = [疾病]
```

### 3.2 症状-疾病关联（从 CSV 加载）

疾病数据存储在 CSV 文件中：

```csv
疾病ID,疾病名称,必要症状,排除症状
cat_001,猫瘟,发热;呕吐;腹泻,咳嗽
cat_002,猫感冒,打喷嚏;咳嗽,腹泻
cat_003,猫肠胃炎,呕吐;腹泻,发热
```

加载代码：

```python
import pandas as pd

def add_symptom_relations(onto, csv_path):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    with onto:
        for _, row in df.iterrows():
            disease_id = row["疾病ID"]
            d = onto[disease_id]

            # 必要症状
            nec_str = row.get("必要症状", "")
            if pd.notna(nec_str) and nec_str.strip():
                for sname in nec_str.split(";"):
                    s = onto[sname.strip()]
                    # 用 OWL 属性限制（而非直接 append）
                    d.is_a.append(necessary.value(s))

            # 排除症状
            nos_str = row.get("排除症状", "")
            if pd.notna(nos_str) and nos_str.strip():
                for sname in nos_str.split(";"):
                    s = onto[sname.strip()]
                    d.is_a.append(nos.value(s))
```

### 3.3 诊断推理主流程（diagnosis.py）

```python
def diagnose(onto, case_dict):
    """
    对一个病例执行诊断推理
    case_dict 格式：
    {
        "pet_type": "cat",
        "symptoms": ["发热", "呕吐", "腹泻"],
        "breed": "英短",
        "age": 2
    }
    """
    with onto:
        # 1. 创建临时个体
        case_id = f"case_{hash(str(case_dict)) % 100000}"
        case_instance = onto.Thing(case_id)

        # 2. 断言症状
        for sname in case_dict.get("symptoms", []):
            s_ind = onto[sname]
            case_instance.has.append(s_ind)

        # 3. 嵌入 SWRL 规则
        onto = apply_swrl_rules(onto)

        # 4. 推理
        sync_reasoner(HermiT, infer_property_values=True)

        # 5. 收集结果
        results = []
        for cls in onto.疾病.descendants():
            if case_instance in cls.instances():
                confidence = _calc_confidence(cls, case_dict, onto)
                results.append((cls, confidence))

        # 6. 清理
        destroy_entity(case_instance)

    results.sort(key=lambda x: x[1], reverse=True)
    return results
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
[诊断结果]
疑似疾病：猫瘟（置信度：0.92）
推理链：
  - 必要症状：发热 ✅、呕吐 ✅、腹泻 ✅
  - 排除症状：咳嗽 ❌（排除猫感冒）
  - 物种匹配：猫 ✅

建议：立即进行血常规检查
```

---

## 五、与 LLM 方案对比

我们用同一个病例，分别测试 LLM 方案和本体推理方案：

| 维度 | LLM 方案（GPT-4） | 本体推理方案 |
|------|-------------------|--------------|
| 输入 | 「我的猫又吐又拉，还发烧」 | `symptoms: ["发热", "呕吐", "腹泻"]` |
| 输出 | 「可能是猫瘟或肠胃炎，建议就医」 | 猫瘟（置信度 0.92） |
| 推理链 | ❌ 无法提供 | ✅ 必要症状全匹配 → 疑似 |
| 可验证性 | ❌ 黑盒 | ✅ 每一步都可追溯 |
| 耗时 | 2-5 秒（API 调用） | 0.3 秒（本地推理） |

> **结论**：在医疗诊断这类关键决策场景中，本体推理的**可验证性、一致性、低延迟**是 LLM 无法替代的。

---

## 六、教学效果：从代码到原理

本项目作为《当 LLM 不够用了》的配套实战案例，对应以下章节：

| 本书章节 | 本项目对应内容 |
|----------|----------------|
| 第一章 本体论是什么 | `src/onto_builder.py`：OWL 类、属性、层次结构设计 |
| 第二章 企业为什么需要本体推理 | `data/` 中的症状-疾病数据，展示「数据富裕、知识贫困」问题 |
| 第四章 本体推理的技术基础设施 | `src/reasoner.py`：Tableau 推理机（HermiT）调用 |
| 第七章 国内实践 | 本项目即国内宠物医疗领域的真实实践案例 |

**学习路径**：

1. **第一周**：理解 OWL 本体建模（类、属性、限制）
2. **第二周**：掌握 SWRL 规则编写（Imp 类、set_as_rule）
3. **第三周**：运行完整诊断流程，分析推理结果
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

**项目链接**：[github.com/georgewangchn/OntologyOps/tree/main/ontologyops/examples/P1](https://github.com/georgewangchn/OntologyOps/tree/main/ontologyops/examples/P1)

**在线阅读**：[georgewangchn.github.io/OntologyOps/examples/P1/](https://georgewangchn.github.io/OntologyOps/examples/P1/)

**书籍全书**：[《当 LLM 不够用了——本体推理的企业决策实践》在线阅读](https://georgewangchn.github.io/OntologyOps/book/)

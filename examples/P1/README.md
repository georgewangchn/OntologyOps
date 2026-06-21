# P1 · 宠物疾病本体推理系统（教学演示版）

> **多范式推理实战营 — 项目 1/6**
> 推理范式：**OWL 本体 + SWRL 规则 + 推理机（HermiT）**

> 📖 本项目为教学演示版，数据为简化示例（10 种疾病、15 种症状），聚焦讲解 OWL 本体构建与 SWRL 规则推理的核心原理。

---

## 项目概述

本项目**基于真实宠物医疗 CDSS 场景设计**，为教学目的做了简化：

- **本体结构**：展示 OWL 核心类与属性的构建方法
- **数据规模**：10 种疾病、15 种症状（足够教学演示）
- **推理规则**：用 owlready2.Imp 实现 SWRL 规则
- **输入类型**：症状输入（教学版聚焦核心流程）

核心思路：

> **把宠物疾病诊断知识形式化为 OWL 本体，用 SWRL 规则表达诊断逻辑，用推理机自动完成「症状 → 疾病」的推理链。**

这是本体推理在企业级场景的最直接范式——不依赖 LLM 的概率生成，每一步推理都可验证、可解释、可审计。

### 与《当 LLM 不够用了》的对应关系

| 本书章节 | 本项目对应内容 |
|---------|--------------|
| 第一章 本体论是什么 | `src/onto_builder.py`：OWL 类、属性、层次结构设计 |
| 第二章 企业为什么需要本体推理 | `data/` 中的症状-疾病数据，展示「数据富裕、知识贫困」问题 |
| 第四章 本体推理的技术基础设施 | `src/reasoner.py`：Tableau 推理机（HermiT）调用 |
| 第七章 国内实践 | 本项目即国内宠物医疗领域的真实实践案例 |

---

## 技术原理

### 1. OWL 本体建模

用 OWL（Web Ontology Language）对宠物疾病领域知识进行形式化建模：

```
疾病 ⊃ 猫瘟
疾病 ⊃ 犬细小病毒

症状 ⊃ 发热
症状 ⊃ 呕吐
症状 ⊃ 腹泻

必要症状（necessary）：罹患某病必须具备的症状
充分症状（sufficient）：出现即高度疑似某病的症状
```

**关键设计决策**：
- `necessary` 用 OWL 的 `EquivalentTo` 表达「必要条件」
- `has_symptom` 用 `ObjectProperty` 建立疾病-症状关联
- 多物种共用一本体，通过 `物种` 属性区分猫/狗/通用

### 2. SWRL 规则推理

SWRL（Semantic Web Rule Language）在 OWL 基础上补充规则推理能力：

```swrl
# 规则1：必要症状组合 → 疑似疾病
疾病(?d) ∧ has_symptom(?d, ?s) ∧ necessary(?d, ?s) → suspected_disease(?d)

# 规则2：排除性症状 → 排除疾病
disease(?d) ∧ nos(?d, ?s) ∧ has_symptom(p, ?s) → NOT diagnose(?d)
```

### 3. 推理机（HermiT / Pellet）

OWL 本体的推理复杂度是 `NExpTime`，需要专门的 Tableau 算法推理机：

| 推理机 | 特点 | 本项目选择 |
|--------|------|--------------|
| **HermiT** | 纯 Java，OWL 2 完整支持，速度中等 | ✅ 默认选择 |
| Pellet | 支持更多推理类型，速度较快 | 备选 |
| JFact | 专注于分类推理，速度快 | 仅分类时用 |

---

## 项目结构

```
P1/
├── README.md              # 本文档
├── notebook.ipynb         # Jupyter Notebook 完整讲解（含逐步推理演示）
├── src/
│   ├── onto_builder.py    # 本体构建：类、属性、层次结构
│   ├── swrl_rules.py     # SWRL 规则定义与加载
│   ├── reasoner.py       # 推理机调用（HermiT）
│   ├── diagnosis.py       # 诊断推理主流程
│   └── utils.py          # 工具函数（数据加载、结果格式化）
├── data/
│   ├── pet_ontology.owl  # 预构建的本体制服（可直接加载）
│   ├── symptoms.csv      # 示例症状数据（10 个样本）
│   └── diseases.csv      # 示例疾病数据（10 个样本）
├── docker-compose.yml    # 一键启动 Jena Fuseki + HermiT
└── slides/               # 配套图文素材（小红书用）
    └── (待补充)
```

---

## 环境准备

### 依赖安装

```bash
# Python 依赖（owlready2 使用支持中文的改造版）
pip install https://github.com/georgewangchn/Owlready2-Chinese.git rdflib pandas

# 验证安装
python -c "import owlready2; print('owlready2 已安装')"
```

> 📝 Owlready2 已改造支持中文（标签、注释、IRI 含中文），源码：https://github.com/georgewangchn/Owlready2-Chinese

```bash
# 可选：Jena Fuseki（如需 SPARQL 查询）
docker run -d -p 3030:3030 stain/jena-fuseki

# 可选：HermiT 推理机（Java）
# 下载：http://www.hermit-reasoner.com/
```

### 快速检查

```python
from owlready2 import *
print("owlready2 version:", owlready2.__version__)
# 预期输出：0.37
```

---

## 运行步骤

### Step 1：构建本体

```bash
cd src/
python onto_builder.py
```

此脚本会：
1. 定义核心类：`疾病`、`症状`、`物种`、`品种`
2. 定义属性：`has_symptom`、`necessary`、`nos`、`history`
3. 从 `../data/diseases.csv` 加载疾病层次结构
4. 从 `../data/symptoms.csv` 加载症状-疾病关联
5. 保存本体到 `../data/pet_ontology.owl`

### Step 2：加载 SWRL 规则

```bash
python swrl_rules.py
```

将诊断规则以 SWRL 形式加载到本体中。

### Step 3：执行推理

```bash
python reasoner.py
```

调用 HermiT 推理机，输出：
- 每个病例的疑似疾病列表（按置信度排序）
- 推理链：「症状 A + 症状 B → 疾病 X（置信度 0.85）」

### Step 4：完整诊断流程

```bash
python diagnosis.py --input ../data/sample_case.json
```

输入示例：
```json
{
  "pet_type": "cat",
  "symptoms": ["发热", "呕吐", "腹泻"],
  "breed": "英短",
  "age": 2
}
```

输出示例：
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

## 核心代码讲解

### onto_builder.py（本体构建）

```python
from owlready2 import *

# 1. 创建本体
onto = get_ontology("http://petbps.com/ontology/pet_disease")

with onto:
    # 2. 定义核心类
    class 疾病(Thing): pass
    class 症状(Thing): pass
    class 物种(Thing): pass

    # 3. 定义对象属性
    class has_symptom(ObjectProperty):
        domain = [疾病]
        range = [症状]

    class necessary(ObjectProperty):
        domain = [疾病]
        range = [症状]
        # 必要症状：罹患该病必须具备的症状

    # 4. 创建具体疾病类
    class 猫瘟(疾病):
        equivalent_to = [has_symptom.some(发热) & has_symptom.some(呕吐)]
        # 等价于：猫瘟 = 疾病 ∧ has_symptom 发热 ∧ has_symptom 呕吐

# 5. 保存本体
onto.save("pet_ontology.owl")
```

### reasoner.py（推理机调用）

```python
from owlready2 import *

# 加载本体
onto = get_ontology("pet_ontology.owl").load()

# 同步推理（使用 HermiT）
with onto:
    sync_reasoner(infer_property_values=True)

# 查看推理结果
for disease in 疾病.descendants():
    instances = list(disease.instances())
    if instances:
        print(f"{disease.label[0]}: {len(instances)} 个疑似病例")
```

---

## 技术栈对照表

| 组件 | 技术选型 | 替代方案 |
|------|----------|----------|
| 本体构建 | owlready2（Python） | Protégé（GUI） |
| 规则引擎 | SWRL + owlready2 | Jena Rules |
| 推理机 | HermiT（通过 owlready2 调用） | Pellet、JFact |
| 本体存储 | OWL 文件（RDF/XML） | Jena Fuseki（SPARQL） |
| 图数据库（可选） | Neo4j | Neptune、Neo4j Aura |


---
## 参考资料

1. W3C OWL 2 Primer：https://www.w3.org/TR/owl2-primer/
2. owlready2 官方文档：https://owlready2.readthedocs.io/
3. SWRL 规范：https://www.w3.org/Submission/SWRL/
4. HermiT 推理机：http://www.hermit-reasoner.com/
5. 《当 LLM 不够用了——本体推理的企业决策实践》第四章

---

*作者：森林瀑布 | 项目类型：多范式推理实战营 P1 | 最后更新：2026-06-20*

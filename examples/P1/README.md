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

### 1. 三层知识编码

疾病诊断知识从 CSV 加载后，编码为三层 OWL 公理（`onto_builder.py` 的 `add_symptom_relations()`）：

以 D001 猫瘟（必要症状：发热、呕吐、腹泻；排除症状：咳嗽、流鼻涕）为例：

| 层 | 编码方式 | 语义 | 作用 |
|---|---------|------|------|
| **推理层** | `equivalent_to` | `D001 ≡ 疾病 ∧ has.value(发热) ∧ has.value(呕吐) ∧ has.value(腹泻)` | HermiT 双向推理：病例有症状 → 推断属于疾病 |
| **元数据层** | `SubClassOf` + `comment` | `necessary.value(症状)` 限制 + `"nos:咳嗽;流鼻涕"` 注解 | 供置信度计算和排除检查解析 |
| **SWRL 层** | 疾病知识个体 | `D001_kb` 个体 + 实例级 `necessary`/`nos` 断言 | 供 SWRL 规则实例级匹配 |

**为什么要三层？**

- `equivalent_to`（充要条件）让 HermiT 能从"病例有这些症状"反推"病例属于这种疾病"——这是确定性推理的核心
- `SubClassOf`（必要条件）只支持单向推理，无法反推，但适合作为元数据供 Python 解析
- SWRL 规则 `necessary(?d, ?s)` 匹配的是实例级断言（ABox），疾病类本身是 TBox 概念无法匹配，需要创建 `D001_kb` 等知识个体

### 2. SWRL 规则推理

SWRL（Semantic Web Rule Language）在 OWL 基础上补充规则推理能力：

```swrl
# 规则1：必要症状匹配 → 疑似疾病
has(?p, ?s) ∧ necessary(?d, ?s) ∧ 疾病(?d) ∧ 症状(?s)
→ suspected(?p, ?d)

# 规则2：排除性症状 → 排除疾病
has(?p, ?s) ∧ nos(?d, ?s) ∧ 疾病(?d) ∧ 症状(?s)
→ excluded(?p, ?d)
```

规则通过 `owlready2.Imp` 嵌入本体，HermiT 推理时自动执行。

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
├── README-ARTICLE.md      # 配套文章（小红书/知乎用）
├── notebook.ipynb         # Jupyter Notebook 完整讲解（含逐步推理演示）
├── setup_env.sh           # 环境初始化脚本（创建 venv + 安装补丁版 owlready2）
├── requirements.txt       # Python 依赖清单
├── index.html             # 文章在线阅读页（由 md2html.py 生成）
├── md2html.py             # README-ARTICLE.md → index.html 转换器
├── test_p1.py             # 测试脚本（print 断言，非 pytest）
├── src/
│   ├── onto_builder.py    # 本体构建：类、属性、层次结构、三层知识编码
│   ├── swrl_rules.py      # SWRL 规则定义与加载（owlready2.Imp）
│   ├── reasoner.py        # 推理机调用（HermiT）+ 三层推理 + 排除逻辑
│   ├── diagnosis.py       # 诊断推理主流程（JSON/交互/API 三种入口）
│   └── utils.py           # 工具函数（数据加载、结果格式化）
├── data/
│   ├── pet_ontology.owl   # 预构建的本体文件（可直接加载）
│   ├── diseases.csv       # 疾病数据（10 种疾病）
│   ├── symptoms.csv       # 症状数据（15 种症状）
│   └── sample_case.json   # 示例病例
├── docker-compose.yml     # 一键启动 Jena Fuseki + HermiT
└── slides/                # 配套图文素材（小红书用）
    └── (待补充)
```

---

## 环境准备

### 一键安装

```bash
bash setup_env.sh
```

此脚本会自动完成：
1. 创建 `.venv` 虚拟环境
2. 下载 `owlready2==0.37` 源码
3. 用 [Owlready2-Chinese](https://github.com/georgewangchn/Owlready2-Chinese) 仓库的 `rule.py` / `reasoning.py` 覆盖源码（使 SWRL 规则和 HermiT 推理支持中文标识符）
4. 从补丁源码安装 owlready2
5. 安装 `rdflib`、`pandas`

> 📝 为什么要打补丁？PyPI 的 owlready2==0.37 的 SWRL 解析器不支持中文标识符（`\?[a-zA-Z0-9_]+`），Owlready2-Chinese 仓库修改了正则为 `\?[a-zA-Z0-9_\u4e00-\u9fa5]+`，同时修复了 HermiT 输出的中文解码（utf8 → gbk）。

### 手动安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install owlready2==0.37 rdflib pandas

# 手动打补丁（从 Owlready2-Chinese 仓库下载 rule.py 和 reasoning.py）
git clone https://github.com/georgewangchn/Owlready2-Chinese.git /tmp/owlready2-chinese
OWL_DIR=$(python3 -c "import owlready2, os; print(os.path.dirname(owlready2.__file__))")
cp /tmp/owlready2-chinese/rule.py "$OWL_DIR/rule.py"
cp /tmp/owlready2-chinese/reasoning.py "$OWL_DIR/reasoning.py"
```

### 可选基础设施

```bash
# Jena Fuseki（如需 SPARQL 查询）
docker run -d -p 3030:3030 stain/jena-fuseki

# HermiT 推理机需要 JVM（owlready2 已内置 HermiT JAR）
java -version  # 确认 Java 可用
```

---

## 运行步骤

### Step 1：构建本体

```bash
source .venv/bin/activate
cd src/
python onto_builder.py
```

此脚本会：
1. 定义核心类：`疾病`、`症状`、`物种`、`品种`
2. 定义属性：`has`、`necessary`、`nos`、`suspected`、`excluded`
3. 从 `../data/diseases.csv` 加载疾病层次结构
4. 从 `../data/symptoms.csv` 加载症状个体
5. 编码三层知识：`equivalent_to`（推理）+ `necessary.value`（元数据）+ `D001_kb` 个体（SWRL）
6. 保存本体到 `../data/pet_ontology.owl`

### Step 2：执行推理

```bash
python reasoner.py
```

调用 HermiT 推理机，三层推理流程：
1. **OWL 分类**：`equivalent_to` 双向推理，从症状反推疾病类
2. **SWRL 补充**：规则1收集部分症状匹配的疑似候选
3. **排除过滤**：规则2 + Python 检查，移除排除症状命中的疾病

### Step 3：完整诊断流程

```bash
python diagnosis.py --input ../data/sample_case.json
```

输入示例（`data/sample_case.json`）：
```json
{
  "pet_type": "cat",
  "breed": "英国短毛猫",
  "age": 2,
  "symptoms": ["发热", "呕吐", "腹泻"],
  "note": "2岁英短，未免疫，急性发病"
}
```

输出示例：
```
  📋 诊断结果（按置信度排序）
──────────────────────────────────────────────────
  1. 猫瘟                   置信度：0.99  █████████
  2. 犬细小病毒                置信度：0.77  ███████
──────────────────────────────────────────────────
```

### Step 4：运行测试

```bash
python test_p1.py
```

测试脚本覆盖三个环节：本体构建 → 推理机 → 诊断模块（从 JSON 加载）。

---

## 推理链详解

以 sample_case（猫，发热 + 呕吐 + 腹泻）为例，完整推理链：

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

## 核心代码讲解

### onto_builder.py（三层知识编码）

```python
from owlready2 import *

onto = get_ontology("http://petbps.com/ontology/pet_disease")

with onto:
    class 疾病(Thing): pass
    class 症状(Thing): pass

    class has(ObjectProperty):
        domain = [疾病]
        range  = [症状]

    class necessary(ObjectProperty):
        domain = [疾病]
        range  = [症状]

    class nos(ObjectProperty):
        domain = [疾病]
        range  = [症状]

# 从 CSV 加载后，为每个疾病编码三层公理
with onto:
    d = onto["D001"]  # 猫瘟

    # 第一层：equivalent_to（充要条件，HermiT 双向推理）
    d.equivalent_to.append(
        onto.疾病 & onto.has.value(发热) & onto.has.value(呕吐) & onto.has.value(腹泻)
    )

    # 第二层：necessary.value SubClassOf（供置信度计算解析）
    d.is_a.append(onto.necessary.value(发热))
    d.is_a.append(onto.necessary.value(呕吐))
    d.is_a.append(onto.necessary.value(腹泻))
    # 排除症状存入 comment 注解
    d.comment.append("nos:咳嗽;流鼻涕")

    # 第三层：疾病知识个体（供 SWRL 规则实例级匹配）
    d_kb = onto.疾病("D001_kb")
    d_kb.necessary.append(发热)
    d_kb.necessary.append(呕吐)
    d_kb.necessary.append(腹泻)
    d_kb.nos.append(咳嗽)
    d_kb.nos.append(流鼻涕)
```

### reasoner.py（三层推理 + 排除）

```python
from owlready2 import *

def diagnose(onto, case_dict):
    onto = apply_swrl_rules(onto)  # 嵌入 SWRL 规则

    with onto:
        # 创建病例个体，断言症状
        case_instance = Thing("case_001")
        case_instance.has.append(发热)
        case_instance.has.append(呕吐)
        case_instance.has.append(腹泻)

    # 三层推理
    run_reasoner(onto)  # HermiT 执行 OWL 分类 + SWRL 规则

    # 第一层：OWL 分类结果
    results = []
    for cls in onto.疾病.descendants():
        if case_instance in cls.instances():
            results.append((cls, _calc_confidence(cls, case_dict, onto)))

    # 第二层：SWRL 补充的疑似候选
    for d_kb in case_instance.suspected:
        disease_cls = _map_kb_to_class(d_kb, onto)  # D001_kb → D001
        if disease_cls and disease_cls not in existing:
            results.append((disease_cls, _calc_confidence(...)))

    # 第三层：排除过滤
    excluded = {_map_kb_to_class(d, onto) for d in case_instance.excluded}
    filtered = [(c, f) for c, f in results
                if c not in excluded
                and not (case_symptoms & set(_get_exclusion_symptoms(c)))]

    return sorted(filtered, key=lambda x: x[1], reverse=True)
```

---

## 技术栈对照表

| 组件 | 技术选型 | 替代方案 |
|------|----------|----------|
| 本体构建 | owlready2（Python） | Protégé（GUI） |
| 规则引擎 | SWRL + owlready2.Imp | Jena Rules |
| 推理机 | HermiT（通过 owlready2 调用） | Pellet、JFact |
| 本体存储 | OWL 文件（RDF/XML） | Jena Fuseki（SPARQL） |
| 图数据库（可选） | Neo4j | Neptune、Neo4j Aura |

---

## 参考资料

1. W3C OWL 2 Primer：https://www.w3.org/TR/owl2-primer/
2. owlready2 官方文档：https://owlready2.readthedocs.io/
3. SWRL 规范：https://www.w3.org/Submission/SWRL/
4. HermiT 推理机：http://www.hermit-reasoner.com/
5. Owlready2-Chinese（中文补丁）：https://github.com/georgewangchn/Owlready2-Chinese
6. 《当 LLM 不够用了——本体推理的企业决策实践》第四章

---

*作者：森林瀑布 | 项目类型：多范式推理实战营 P1 | 最后更新：2026-06-22*

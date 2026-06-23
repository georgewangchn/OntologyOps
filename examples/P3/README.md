# P3 · 宠物疾病三元组推理系统（教学演示版）

> **多范式推理实战营 — 项目 3/6**
> 推理范式：**Jena Fuseki 前向链规则 + SPARQL 查询一体化**
> 对比 P1：**OWL 本体推理（HermiT + SWRL）**
> 对比 P2：**Prolog 规则推理（SWI-Prolog + SLD 归结）**

> 📖 同一领域问题（宠物疾病诊断），第三种推理范式。P3 展示三元组存储 + 前向链规则推理 + SPARQL 查询管线一体化，与 P1 的 Tableau 算法、P2 的反向链 SLD 归结形成对比。

---

## P1 / P2 / P3 三种推理范式对比

| 维度 | P1（OWL + HermiT） | P2（Prolog） | P3（Jena Fuseki） |
|------|-------------------|-------------|-------------------|
| 逻辑基础 | 描述逻辑（DL） | Horn 子句逻辑 | 前向链规则 + RDF |
| 推理方向 | 分类推理（Tableau） | **反向链**（目标驱动） | **前向链**（数据驱动） |
| 推理时机 | 查询前一次性推理 | 查询时实时推理 | **数据加载时预计算** |
| 世界假设 | OWA（开放世界） | CWA（封闭世界） | CWA（negation-as-failure） |
| 知识表示 | OWL 类/属性/限制 | Prolog 事实/规则 | RDF 三元组 + Jena Rules |
| 查询语言 | owlready2 API | Prolog query | **SPARQL**（W3C 标准） |
| 推理完备性 | ✅ 完备 | ❌ 无保证 | ❌ 不完备（规则近似） |
| 数据持久化 | 文件加载 | 内存 | **三元组数据库** |
| 部署形态 | JVM 库 | 本地进程 | **HTTP 服务**（端口 3030） |

### 前向链 vs 反向链的核心差异

```
P2 Prolog（反向链）：
  用户问："case 是不是猫瘟？"
  → Prolog 从目标 diagnose(case, d001) 出发
  → 反向查找规则：需要 forall(necessary) + \+ nos
  → 按需计算，只算被问到的

P3 Jena（前向链）：
  数据加载时：自动执行所有规则
  → d001 necessary 发热 → 任何 has 发热的 case → suspected(d001)
  → d001 nos 咳嗽 → 任何 has 咳嗽的 case → excluded(d001)
  → 预计算所有推断结果，存入图
  用户查询时：SPARQL 直接读已计算好的结果
```

**类比**：P2 像按需计算（查一次算一次），P3 像物化视图（提前算好，查询直接读）。

### SPARQL 查询推理一体化

P3 的独特价值：**SPARQL 查询自动包含推理结果**。

```sparql
-- 这条查询会返回 Jena 前向链预计算的所有 diagnosed 三元组
-- 用户不需要先"运行推理机"再查询——推理内置在查询管线里
SELECT ?disease ?label WHERE {
    :case_temp :diagnosed ?disease .   -- :diagnosed 是规则推断的
    ?disease rdfs:label ?label .
}
```

P1 需要先 `sync_reasoner()` 再 `cls.instances()`，P2 需要直接调用 `prolog.query()`——推理和查询是分开的。P3 把两者融为一体。

---

## 项目结构

```
P3/
├── README.md              # 本文档
├── README-ARTICLE.md      # 配套文章
├── setup_env.sh           # 环境初始化（Docker + venv + 知识库构建 + Fuseki 启动）
├── requirements.txt       # Python 依赖
├── test_p3.py             # 测试脚本
├── docker-compose.yml     # Jena Fuseki 一键部署
├── fuseki/
│   ├── config.ttl         # Fuseki 配置（推理机 = GenericRuleReasoner）
│   └── data/
│       ├── rules.ttl      # Jena 自定义规则（4 条：传递/疑似/排除/确诊）
│       └── pet.ttl        # 自动生成的 Turtle 知识库
├── src/
│   ├── kb_builder.py      # CSV → Turtle 三元组
│   ├── reasoner.py        # SPARQL 查询 + 推理一体化
│   ├── diagnosis.py       # 诊断主流程
│   └── utils.py           # 工具函数
├── data/
│   ├── diseases.csv       # 疾病数据（与 P1/P2 相同）
│   ├── symptoms.csv       # 症状数据（与 P1/P2 相同）
│   └── sample_case.json   # 示例病例（与 P1/P2 相同）
└── slides/
    └── (待补充)
```

---

## 环境准备

### 一键安装

```bash
bash setup_env.sh
```

此脚本会：
1. 创建 `.venv` 虚拟环境
2. 安装 `SPARQLWrapper`、`pandas`
3. 从 CSV 生成 Turtle 知识库（`fuseki/data/pet.ttl`）
4. 启动 Jena Fuseki Docker 容器
5. 验证 SPARQL 端点可用

### 手动安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 构建知识库
cd src && python kb_builder.py && cd ..

# 启动 Fuseki
docker-compose up -d
```

### Fuseki UI

启动后访问 http://localhost:3030 ：
- 用户名 `admin`，密码 `admin`
- 数据集 `pet`，SPARQL 端点 `http://localhost:3030/pet/sparql`

---

## 运行步骤

### Step 1：构建知识库

```bash
source .venv/bin/activate
cd src/
python kb_builder.py
```

从 `../data/diseases.csv` 生成 Turtle 三元组 `../fuseki/data/pet.ttl`。

### Step 2：启动 Fuseki

```bash
docker-compose up -d
```

Fuseki 启动时自动加载 `config.ttl`，配置 `GenericRuleReasoner` + `rules.ttl`，对 `pet.ttl` 执行前向链推理。

### Step 3：执行推理

```bash
python reasoner.py
```

通过 SPARQL 查询获取推理结果。

### Step 4：运行测试

```bash
python test_p3.py
```

---

## Jena 规则详解

`fuseki/data/rules.ttl` 定义了 4 条前向链规则：

### 规则 1：传递闭包

```prolog
[rule_transitive:
    (?a :contain ?b), (?b :contain ?c)
    -> (?a :contain ?c)
]
```

前向链自动计算 `contain` 的传递闭包。对比 P2 Prolog 的递归 `can_transmit/2`（按需计算），P3 在数据加载时就预计算完毕。

### 规则 2：疑似推断

```prolog
[rule_suspected:
    (?case :has ?symptom), (?disease :necessary ?symptom), (?disease rdf:type :疾病)
    -> (?case :suspected ?disease)
]
```

### 规则 3：排除推断

```prolog
[rule_excluded:
    (?case :has ?symptom), (?disease :nos ?symptom), (?disease rdf:type :疾病)
    -> (?case :excluded ?disease)
]
```

### 规则 4：确诊推断（noValue = negation as failure）

```prolog
[rule_diagnosed:
    (?case :suspected ?disease), noValue(?case :excluded ?disease)
    -> (?case :diagnosed ?disease)
]
```

`noValue` 是 Jena 的 CWA 否定——如果图中没有 `excluded` 三元组，就认为不存在。对比 P1 的 OWA（未断言 ≠ 不存在）。

---

## 推理链详解

以 sample_case（猫，发热 + 呕吐 + 腹泻）为例：

```
① 数据断言（SPARQL UPDATE INSERT DATA）
   :case_temp :has :发热, :has :呕吐, :has :腹泻

② Jena 前向链预计算（自动触发所有规则）
   规则2 → :case_temp :suspected :d001, :d003, :d004, :d006, :d009
   规则3 → :case_temp :excluded :d002, :d003, :d005, :d006, :d007, :d008, :d009, :d010
   规则4 → :case_temp :diagnosed :d001, :d004（suspected 且无 excluded）

③ SPARQL 查询（查询自动包含推理结果）
   SELECT ?disease WHERE { :case_temp :diagnosed ?disease }
   → d001(猫瘟), d004(犬细小)

④ 最终结论
   → 猫瘟（确诊）> 犬细小病毒（确诊）
```

---

## 与《当 LLM 不够用了》的对应关系

| 本书章节 | P1 对应 | P2 对应 | P3 对应 |
|---------|---------|---------|---------|
| 第一章 本体论是什么 | OWL 类/属性/层次 | Prolog 事实/谓词 | RDF 三元组 |
| 第四章 技术基础设施 | HermiT（Tableau） | SWI-Prolog（SLD） | Jena Fuseki（前向链 + SPARQL） |
| 第八章 多范式推理 | OWL 本体推理 | Prolog 规则推理 | 三元组存储 + 规则推理 |

---

## 技术栈对照表

| 组件 | P1 选型 | P2 选型 | P3 选型 |
|------|---------|---------|---------|
| 推理引擎 | HermiT（Java） | SWI-Prolog（C） | Jena GenericRuleReasoner（Java） |
| 推理方向 | 分类（双向） | 反向链 | 前向链 |
| 查询语言 | owlready2 API | Prolog query | SPARQL |
| 知识格式 | OWL（RDF/XML） | Prolog（.pl） | Turtle（.ttl） |
| 数据存储 | 文件加载 | 内存 | 三元组数据库 |
| 部署 | docker-compose（Fuseki+HermiT） | Dockerfile（swipl+Python） | docker-compose（Fuseki 独立） |

---

*作者：森林瀑布 | 项目类型：多范式推理实战营 P3 | 最后更新：2026-06-22*

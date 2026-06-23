# P2 · 宠物疾病规则推理系统（教学演示版）

> **多范式推理实战营 — 项目 2/6**
> 推理范式：**Prolog 规则推理（SWI-Prolog + pyswip）**
> 对比 P1：**OWL 本体推理（HermiT + SWRL）**

> 📖 同一领域问题（宠物疾病诊断），不同推理范式。P2 展示 Horn 子句逻辑 + SLD 归结 + 封闭世界假设（CWA），与 P1 的描述逻辑 + Tableau 算法 + 开放世界假设（OWA）形成对比。

---

## P1 vs P2：两种推理范式对比

| 维度 | P1（OWL + HermiT） | P2（Prolog + SWI-Prolog） |
|------|-------------------|--------------------------|
| 逻辑基础 | 描述逻辑（DL, SHOIN(D)） | Horn 子句逻辑 |
| 世界假设 | **开放世界**（OWA） | **封闭世界**（CWA） |
| 知识表示 | OWL 类/属性/限制（三层编码） | Prolog 事实/规则（谓词逻辑） |
| 推理方式 | 分类推理（Tableau 算法） | 目标驱动（SLD 归结） |
| 否定语义 | 不能从"未断言"推断"不存在" | `\+`（negation as failure）：未断言 = 不存在 |
| 递归推理 | 不支持 | ✅ 原生支持 |
| 可判定性 | 有保证 | 无保证（可能不终止） |
| 推理机 | HermiT（Java，JVM） | SWI-Prolog（C） |
| Python 桥接 | owlready2 | pyswip |
| 部署 | docker-compose（Fuseki + HermiT） | Dockerfile（swipl:latest + Python） |

### CWA vs OWA 的实际影响

```
病例：猫，发热 + 呕吐 + 腹泻，未记录是否咳嗽

P1（OWA）：HermiT 不能因"未断言咳嗽"就判定"没有咳嗽"
  → 需要显式的排除症状断言才能排除疾病
  → 更保守，适合医疗场景

P2（CWA）：\+ has(case, '咳嗽') 成功（因为没有这个事实）
  → 未记录 = 不存在，可直接用于排除推理
  → 更激进，适合零件库/配置等封闭场景
```

---

## 项目结构

```
P2/
├── README.md              # 本文档
├── README-ARTICLE.md      # 配套文章（小红书/知乎用）
├── setup_env.sh           # 环境初始化脚本（检查 SWI-Prolog + 创建 venv）
├── requirements.txt       # Python 依赖
├── test_p2.py             # 测试脚本
├── Dockerfile             # Docker 镜像（swipl:latest + Python 3）
├── docker-compose.yml     # 一键部署
├── src/
│   ├── rules.pl           # Prolog 规则（6 条：确诊/疑似/排除/物种/递归/解释）
│   ├── kb_builder.py      # CSV → Prolog 事实（pet_kb.pl）
│   ├── reasoner.py        # pyswip 推理引擎
│   ├── api.py             # FastAPI 接口（/diagnose, /explain）
│   ├── diagnosis.py       # 诊断主流程（JSON/交互）
│   └── utils.py           # 工具函数
├── data/
│   ├── diseases.csv       # 疾病数据（与 P1 相同）
│   ├── symptoms.csv       # 症状数据（与 P1 相同）
│   ├── sample_case.json   # 示例病例（与 P1 相同）
│   └── pet_kb.pl          # 自动生成的 Prolog 知识库
└── slides/                # 配套图文素材
    └── (待补充)
```

---

## 环境准备

### 前置条件

- **SWI-Prolog**（推理引擎）
- **Python 3.10+**（pyswip 桥接 + FastAPI）

### 一键安装

```bash
bash setup_env.sh
```

### 手动安装

```bash
# macOS
brew install swi-prolog

# Ubuntu/Debian
sudo apt-get install swi-prolog

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Docker 部署

```bash
docker-compose up -d
# API: http://localhost:8000
```

---

## 运行步骤

### Step 1：构建知识库

```bash
source .venv/bin/activate
cd src/
python kb_builder.py
```

从 `../data/diseases.csv` 生成 Prolog 事实文件 `../data/pet_kb.pl`。

### Step 2：执行推理

```bash
python reasoner.py
```

### Step 3：完整诊断流程

```bash
python diagnosis.py --input ../data/sample_case.json
```

### Step 4：运行测试

```bash
python test_p2.py
```

### Step 5：启动 API 服务

```bash
cd src/
python api.py
# 或
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

API 调用示例：
```bash
curl -X POST http://localhost:8000/diagnose \
  -H "Content-Type: application/json" \
  -d '{"pet_type": "cat", "symptoms": ["发热", "呕吐", "腹泻"]}'
```

---

## Prolog 规则详解

`src/rules.pl` 定义了 6 条规则：

### 规则 1：确诊（全匹配 + 排除未命中）

```prolog
diagnose(Patient, Disease) :-
    disease(Disease, _, _),
    forall(necessary(Disease, S), has(Patient, S)),
    \+ (nos(Disease, S), has(Patient, S)).
```

- `forall/2`：检查所有必要症状都已断言
- `\+`：negation as failure，未断言排除症状 = 不存在

### 规则 2：疑似（部分匹配 + 置信度）

```prolog
suspect(Patient, Disease, Confidence) :-
    findall(S, (necessary(Disease, S), has(Patient, S)), Matched),
    findall(S, necessary(Disease, S), All),
    length(Matched, M), length(All, N),
    Confidence is M / N.
```

- `findall/3`：收集匹配的必要症状
- 置信度 = 匹配数 / 总数（Prolog 算术，OWL/SWRL 无法表达）

### 规则 5：递归传播链（Prolog 独有）

```prolog
can_transmit(D1, D2) :- transmit_to(D1, D2).
can_transmit(D1, D3) :- transmit_to(D1, D2), can_transmit(D2, D3).
```

Prolog 原生支持递归，可推理疾病传播链路。OWL 的 `TransitiveProperty` 只能做传递闭包，无法做条件递归。

---

## 推理链详解

以 sample_case（猫，发热 + 呕吐 + 腹泻）为例：

```
① 断言症状
   has(case, '发热'), has(case, '呕吐'), has(case, '腹泻')

② 确诊查询（diagnose/2：forall 必要症状 + \+ 排除症状）
   ├─ d001(猫瘟): forall(necessary) ✓, \+ nos ✓ → ✅确诊
   ├─ d003(猫肠炎): forall ✓, \+ nos(发热) ✗ → ❌
   └─ d006(犬冠状): forall ✓, \+ nos(发热) ✗ → ❌

③ 疑似查询（suspect/3：findall 匹配率 + \+ 排除）
   ├─ d001(猫瘟): 3/3=1.0, \+ nos ✓ → ✅ 1.00
   ├─ d004(犬细小): 2/3=0.67, \+ nos ✓ → ✅ 0.67
   └─ d009(猫艾滋): 1/2=0.5, \+ nos(腹泻) ✗ → ❌

④ 最终结论
   → 猫瘟（1.00 ✅确诊）> 犬细小病毒（0.67 ⚠️疑似）
```

---

## 与《当 LLM 不够用了》的对应关系

| 本书章节 | P1 对应 | P2 对应 |
|---------|---------|---------|
| 第一章 本体论是什么 | `onto_builder.py`：OWL 类/属性/层次 | `kb_builder.py`：Prolog 事实/谓词 |
| 第四章 技术基础设施 | HermiT（Tableau 算法） | SWI-Prolog（SLD 归结） |
| 第八章 多范式推理 | OWL 本体推理 | Prolog 规则推理（对比范式） |

---

## 技术栈对照表

| 组件 | P1 选型 | P2 选型 |
|------|---------|---------|
| 推理引擎 | HermiT（Java） | SWI-Prolog（C） |
| Python 桥接 | owlready2 | pyswip |
| 知识格式 | OWL（RDF/XML） | Prolog（.pl） |
| Web 框架 | —（diagnosis.py 内嵌） | FastAPI + Uvicorn |
| 容器基础 | python:3.7 + JVM | swipl:latest + Python 3 |

---

*作者：森林瀑布 | 项目类型：多范式推理实战营 P2 | 最后更新：2026-06-22*

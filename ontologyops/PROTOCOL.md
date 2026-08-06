# OntologyOps — "Ontology Repo" 支柱协议 v1.0

> 本文件是**抽象协议契约**（语义级、可移植）。它规定"一个实现要成为 OntologyOps
> 合规的 Ontology Repo，必须满足什么"，**不绑定任何具体文件格式或技术栈**。
>
> 协议分两层，以匹配 OntologyOps **领域中立**的定位（其自身材料横跨设备/医疗/治理）：
> - **§1 核心机制层（领域中立）**：任何领域的 Ontology Repo 都须满足的工程纪律。
> - **§2 领域 Profile（领域专属）**：某一具体领域在核心之上追加的语义要求。本协议随附一个 **Governance Profile**，由参考实现 GovernanceOps 满足。
>
> GovernanceOps 是本协议的**参考实现**：采用 `ontology/schema/ontology.schema.json`
> 定义的 YAML DSL 作为**参考编码 (reference encoding, non-exclusive)**，用 owlready2+HermiT
> 推理、SQLite 版本仓库，并满足 Governance Profile。另一支团队完全可以用别的编码、别的推理机、
> 别的存储、**别的领域 profile** 实现本协议，只要通过 §1 + 其目标 profile 的符合性条款。

## 0. 术语

- **本体 (Ontology)**：一组概念、属性、定义类及其公理，语义等价于 OWL 2 DL。
- **定义类 (Defined Class)**：由等价类公理 (equivalent-to) 定义、供推理机分类的类。
- **result_key**：定义类对外暴露的稳定分类标识（下游按此消费分类结果）。
- **领域 Profile**：在核心机制之上，为某一领域追加的一组语义符合性要求（如 Governance Profile）。

## 1. 核心机制要求（领域中立，MUST）

任何领域的合规 Ontology Repo 实现 **MUST**：

- **R1 · 声明式本体**：本体以某种可被机器校验的编码持有（存在一份 schema 可判定其合法性）。本体是**唯一事实源**，推理与降级逻辑都从它派生，不得存在与之并行的手写副本。
- **R2 · OWL 2 DL 语义**：本体可编译到 OWL 2 DL，交给确定性推理机分类。LLM 只用于**构建/修改**本体（知识工程链），**不得进入推理链**。
- **R3 · 语义分类（result_key）**：推理 **MUST** 产出一组以 `result_key` 标识的语义类别，供下游稳定消费。**具体有哪些类别属于领域 Profile**（§2）——核心层只要求"以 result_key 暴露可被推理机判定的语义分类"这一机制本身。
- **R4 · 版本化治理**：本体可被版本化，**MUST** 支持 diff（语义级）、tag、rollback，且版本可回溯（parent 链或等价机制）。版本读取失败 **MUST** 显式报错，不得静默返回空。
- **R5 · 互操作产物**：**MUST** 能导出一种标准 W3C 序列化（如 Turtle/RDF-XML），供外部本体工具消费。
- **R6 · 自证符合性**：实现 **MUST** 能对自身产出机器可读的符合性报告（见 `conformance.yaml`）。

> 这六条与领域无关：设备本体、医疗本体、治理本体都能谈"是否满足 R1–R6"。

## 2. 领域 Profile

领域 Profile 在核心机制之上追加语义要求。一个实现选择其目标 profile 并满足之。

### 2.1 Governance Profile（GovernanceOps 满足）

企业决策治理领域的 profile，要求：

- **G1 · 核心概念**：定义 `Decision` 概念。
- **G2 · governed 语义**：存在等价于"同时具备 owner、deadline、至少一次 update"的定义类，`result_key = governed`。
- **G3 · 优先级关键类**：存在由**优先级值约束**驱动的关键类（如 `critical` = 最高档 P0、`high_priority` = P1）。

> 其它领域可定义自己的 profile（如医疗诊断 profile 的 `diagnosable` 语义、设备合规 profile 的 `compliant` 语义），无需改动核心机制层。本版本只随附 Governance Profile；**不预置 profile 注册表或插件框架**（当前 Ontology Repo 支柱仅 GovernanceOps 一个实现，多 profile 抽象留待第二个实现出现时再引入）。

## 3. 协议不规定 (NON-normative)

- 具体序列化格式（YAML DSL / Turtle / JSON-LD / …）——`ontology.schema.json` 只是参考编码之一。
- 具体推理机（HermiT / Pellet / ELK / …）。
- 具体版本存储（SQLite / 文件 / git / …）。
- 具体领域语义（由领域 Profile 定，不属于核心机制）。
- 闭世界过程式规则（优先级阈值等）的表达方式——本版本将其留在实现侧，作为后续协议增量。

## 4. 符合性

符合性 = 通过 `ontology/schema/conformance.yaml` 中**核心条款 (profile: core)** + **目标 profile 条款**的全部检查。每条条款标注了所属层（`core` 或某 profile 名）。参考实现（GovernanceOps）对自身本体运行 `govops onto conformance` 应全绿（core + governance）；`--json` 输出即"本实现符合 OntologyOps Ontology Repo 协议（Governance Profile）"的可核验证据。

> **非符合性目标**：教学范式演示（如 OntologyOps 博客的 P1–P6 / PL1–PL6）**不以符合本协议为目标**——协议是为生产级、会持续演化的本体仓库准备的工程纪律，教学件的目的是讲清各推理范式。

## 5. 与 OntologyOps 博客系列的关系

- 本文件与 `ontology.schema.json`、`conformance.yaml` 三者构成可回填 OntologyOps 博客仓库的**协议 canonical 源**。
- 博客系列第 8 篇六支柱之"Ontology Repo"、第 9 篇"六支柱→GovernanceOps 组件映射表"的对应内容，以本协议 + 本参考实现为事实依据。

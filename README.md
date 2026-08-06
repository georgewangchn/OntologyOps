<div align="center">

# 🧠 OntologyOps

### 让本体像代码一样被管理，让知识像软件一样持续交付，让推理像编译器一样稳定运行

<em>GitOps + DevOps + Knowledge Engineering + Ontology 融合后的新范式</em>

<br>

[![Code License](https://img.shields.io/badge/Code-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Series License](https://img.shields.io/badge/Series-CC_BY--NC--SA_4.0-f59e0b?style=for-the-badge)](LICENSE-BOOK)
[![Protocol License](https://img.shields.io/badge/Protocol-CC_BY_4.0-3b82f6?style=for-the-badge)](ontologyops/LICENSE)
[![Reference Impl](https://img.shields.io/badge/参考实现-GovernanceOps-6366f1?style=for-the-badge)](https://github.com/georgewangchn/GovernanceOps)

📖 **[在线阅读全系列 →](https://senlinpubu.top)**

</div>

---

> 🧭 **工程师从哪进？** 建议**先**跑参考实现 **[GovernanceOps](https://github.com/georgewangchn/GovernanceOps)**（`govops demo` 看代码例子跑起来），有了大概感觉，**再**回来读这里的方法论与协议——先看能跑的，再看为什么。

## 💡 一句话定义

**OntologyOps = 面向企业知识资产的持续构建、持续验证、持续推理、持续治理体系。**

它不是「Ontology + Agent」，而是把本体从**依赖专家手工维护的静态资产**，变成**能持续演化、持续验证、持续发布的工程化资产**。

<br>

## 🎯 解决什么问题

本体（Ontology）在推理能力上没有被知识图谱取代——但它被行业放弃了。根因不是「OWL 太复杂」或「推理太慢」，而是一句话：

<div align="center">

### `知识变化速度  >  知识维护速度`

</div>

传统架构完全依赖专家手工维护本体，当法规、标准、制度持续变化，本体必然腐化。OntologyOps 正面解决这个困扰知识工程界二十多年的问题。

<br>

## ⚖️ 核心原则

> **LLM 永远不进入推理链，只进入知识工程链。**

| 角色 | 对应实体 | 职责 | 特点 |
|------|---------|------|------|
| 🤖 **Knowledge Engineer** | LLM / Agent | 构建知识 | 灵活、泛化、理解自然语言 |
| 📐 **Knowledge Model** | Ontology (OWL/SWRL) | 表达知识 | 精确、可验证、形式化 |
| 🧮 **Inference Engine** | Reasoner (HermiT/Pellet) | 推理知识 | 确定、可追溯、可审计 |

<br>

## 🏛️ 总体架构

```
        Knowledge Sources  ·  法规 / 标准 / 制度 / 设计规范
                       │
                       ▼
   🔧 Knowledge Compiler     Document → Ontology Patch      ← 核心创新
                       │
                       ▼
   📦 Ontology Repo          concepts / rules / constraints  ← Git for Knowledge
                       │                                       Diff · Tag · Rollback …
                       ▼
   📝 Knowledge PR           提交 / 审查 / 合并 / 拒绝        ← 知识变更审计
                       │
                       ▼
   ✅ Ontology CI            语法 / 语义 / 一致性 / 规则       ← 自动化验证
                       │
                       ▼
   🧠 Reasoning Runtime      Deterministic·Traceable·Auditable ← 推理执行（隔离）
```

<br>

## 🧩 六大核心组件

| 组件 | 定位 | 类比 |
|------|------|------|
| 📦 **Ontology Repo** | 本体的 Git 仓库 | GitHub Repository |
| 🔧 **Knowledge Compiler** | 文档 → 本体 Patch | 编译器（Source → IR） |
| 📝 **Knowledge PR** | 知识变更请求 | Pull Request |
| 🤖 **Agent 体系** | 知识工程 Agent 群 | CI Pipeline 中的 Worker |
| ✅ **Ontology CI** | 自动化质量门禁 | Jenkins / GitHub Actions |
| 🧠 **Reasoning Runtime** | 隔离的推理执行层 | Production Runtime |

<br>

## 🛰️ 落地实现：GovernanceOps

OntologyOps 是**方法论**（六支柱）；六支柱之一的 **Ontology Repo** 已沉淀出一份正式、可验证的协议。它由一个可运行实现长出来、并被它持续验证——**[GovernanceOps](https://github.com/georgewangchn/GovernanceOps)**，一个把企业「决策」当第一管理对象的治理运行时（Ontology Repo 支柱已达协议级，其余五根为雏形）。

其中「Ontology Repo」支柱已沉淀为一份**正式、可验证的协议**：

| 文件 | 作用 |
|---|---|
| [`ontologyops/PROTOCOL.md`](ontologyops/PROTOCOL.md) | 抽象协议契约（R1–R6，语义级、不绑定格式） |
| [`ontologyops/ontology.schema.json`](ontologyops/ontology.schema.json) | 参考编码：LLM 友好、diff 友好的本体 DSL 的 JSON Schema |
| [`ontologyops/conformance.yaml`](ontologyops/conformance.yaml) | 符合性条款——判定一个实现是否合规 |

> GovernanceOps 里 `govops onto conformance --json` 对自身本体跑上述条款，全绿即「合规参考实现」的机器可读证据。schema 校验的正是参考 DSL、conformance 跑的正是参考实现，故协议与实现锁步、不漂移。

<br>

## 🚀 快速开始

本仓库是**方法论 + 专栏系列 + 推理实战营**的集合。想直接看可运行代码：

```bash
git clone git@github.com:georgewangchn/OntologyOps.git
cd OntologyOps

# 多范式推理实战营：P1–P6（符号 → 数值）与 pl1–pl6（LLM Agent 版）
cd labs/P1                    # P1 = OWL / HermiT 本体推理
pip install -r requirements.txt
# 按该目录 README 运行：构建本体 → HermiT 推理 → 诊断
```

想看 OntologyOps 落成一个**可跑的系统（原型级）**长什么样：直接跑 **[GovernanceOps](https://github.com/georgewangchn/GovernanceOps)**（`govops demo` 一键体验）。

<br>

## 📦 项目组成

本仓库包含三个独立"产品"，各有清晰边界：

| 产品 | 目录 | 说明 | 许可 |
|------|------|------|------|
| **OntologyOps** | `ontologyops/` | 方法论 + 协议规范 | CC BY 4.0 |
| **推理实战营** | `labs/` | P1–P6 + pl1–pl6 可运行代码 | MIT |
| **博客站点** | `astro/` | [senlinpubu.top](https://senlinpubu.top) 在线博客 | MIT |

<br>

## 📂 项目结构

```
OntologyOps/
├── ontologyops/      # OntologyOps 协议规范（CC BY 4.0）
├── labs/                        # 推理实战营 P1–P6 + pl1–pl6（LLM Agent 版）
│   ├── agent_core/              #   共享 Agent 框架
│   └── shared_data/             #   共享数据集
├── astro/                       # 博客站点（部署至 senlinpubu.top）
└── _archived_copub/             # 归档
```

<br>

## 📚 与「当LLM不够用了」系列的关系

「当LLM不够用了」是作者维护的**博客专栏系列**，系统讲解本体推理在企业决策中的实践。本仓库的 P1–PL6 多范式推理示例是该系列的配套代码，博客文章在 [senlinpubu.top](https://senlinpubu.top) 在线阅读。

| 专栏系列 | 本仓库 |
|----------|--------|
| 理论设计 · 架构文档 | 工程实现 · 可运行代码 |
| **Why & What** | **How** |

> 全系列论证「为什么 LLM 不够用」；OntologyOps 回答「行业放弃本体后，如何让本体重新可用」。

### 📖 出版书

「当LLM不够用了」系列已精编调整为正式出版书 **《从 Palantir 到本体智能：企业决策系统落地实战》**（暂定名）。出版书的 P1–PL6 案例代码在本仓库 `labs/` 目录下，读者可在此查看和运行。OntologyOps 的完整可运行实现另见 **[GovernanceOps](https://github.com/georgewangchn/GovernanceOps)** 开源项目。

<br>

## 👤 作者

**森林瀑布** — 本体推理 × 企业决策 × AI 实战

<br>

## 📜 License

本仓库采用**分层许可**，不同资产类型适用不同协议：

| 资产类型 | 许可协议 | 覆盖范围 | 说明 |
|---------|---------|---------|------|
| **代码** | [MIT](LICENSE) | labs/, astro/ | 自由使用、修改、商用 |
| **专栏内容** | [CC BY-NC-SA 4.0](LICENSE-BOOK) | blog mdx | 署名 + 非商业 + 相同方式共享 |
| **协议规范** | [CC BY 4.0](ontologyops/LICENSE) | ontologyops/ | 署名 + 允许商业实现 |
| **出版书** | All Rights Reserved | 《从 Palantir 到本体智能》 | 独立版权作品，详见 [LICENSE-BOOK](LICENSE-BOOK) |

**贡献者**：提交 PR 即表示同意 [CLA](CLA.md) · 项目名称使用指引见 [TRADEMARK.md](TRADEMARK.md)

<div align="center">
<br>
<sub>让本体重新可用 · Code: MIT · 专栏: CC BY-NC-SA 4.0 · 协议: CC BY 4.0</sub>
</div>

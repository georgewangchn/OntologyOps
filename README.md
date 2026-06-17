# OntologyOps

> **让本体像代码一样被管理，让知识像软件一样持续交付，让推理像编译器一样稳定运行。**

[![Code License](https://img.shields.io/badge/Code-MIT-blue.svg)](LICENSE)
[![Book License](https://img.shields.io/badge/Book-CC_BY--NC--SA_4.0-orange.svg)](LICENSE-BOOK)
[![Book](https://img.shields.io/badge/配套书籍-《当LLM不够用了》-green.svg)](./docs/OntologyOps方案.md)

📖 **[在线阅读全书 →](https://georgewangchn.github.io/OntologyOps/book/)**

---

## 一句话定义

**OntologyOps = 面向企业知识资产的持续构建、持续验证、持续推理、持续治理体系**

它不是"Ontology + Agent"，而是 GitOps + DevOps + Knowledge Engineering + Ontology 融合后的新范式。

---

## 解决什么问题

本体（Ontology）在推理能力上没有被知识图谱取代——但它被行业放弃了。根因不是"OWL 太复杂"或"推理太慢"，而是：

```
知识变化速度 > 知识维护速度
```

传统架构完全依赖专家手工维护本体，当法规、标准、制度持续变化，本体必然腐化。OntologyOps 正面解决这个困扰知识工程界二十多年的问题：

> **如何把本体从依赖专家手工维护的静态资产，变成能持续演化、持续验证、持续发布的工程化资产。**

---

## 核心原则

| 角色 | 对应实体 | 职责 | 特点 |
|------|---------|------|------|
| **Knowledge Engineer** | LLM / Agent | 构建知识 | 灵活、泛化、理解自然语言 |
| **Knowledge Model** | Ontology (OWL/SWRL) | 表达知识 | 精确、可验证、形式化 |
| **Inference Engine** | Reasoner (HermiT/Pellet) | 推理知识 | 确定、可追溯、可审计 |

**关键原则：LLM 永远不进入推理链，只进入知识工程链。**

---

## 总体架构

```
┌─────────────────────────────────────┐
│        Knowledge Sources             │
│  法规 / 标准 / 制度 / 设计规范         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      🔧 Knowledge Compiler          │  ← 核心创新
│      Document → Ontology IR         │     Document → Ontology Patch
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      📦 Ontology Repo               │  ← Git for Knowledge
│  concepts / rules / constraints      │     Diff / Branch / Merge / Tag
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      📝 Knowledge PR                │  ← 知识变更审计
│  提交 / 审查 / 合并 / 拒绝            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      ✅ Ontology CI                 │  ← 自动化验证
│  语法 / 语义 / 一致性 / 规则检查       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      🧠 Reasoning Runtime           │  ← 推理执行（隔离）
│  Deterministic / Traceable / Auditable │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      🏛️  Governance Center          │  ← 知识治理
│  Version / Audit / Approval / Rollback │
└─────────────────────────────────────┘
```

---

## 六大核心组件

| 组件 | 定位 | 类比 |
|------|------|------|
| **Ontology Repo** | 本体的 Git 仓库 | GitHub Repository |
| **Knowledge Compiler** | 文档 → 本体 Patch | 编译器（Source → IR） |
| **Knowledge PR** | 知识变更请求 | Pull Request |
| **Agent 体系** | A2A 知识工程 Agent 群 | CI Pipeline 中的 Worker |
| **Ontology CI** | 自动化质量门禁 | Jenkins / GitHub Actions |
| **Reasoning Runtime** | 隔离的推理执行层 | Production Runtime |

---

## 四个产品化方向

```
Ontology Compiler ──→ Ontology Repository ──→ Ontology CI/CD ──→ Ontology Runtime
    编译知识              存储和管理知识            验证和发布知识          推理和执行知识
```

---

## 🎬 应用场景演示

### GovernanceOps —— 第一个应用场景 Demo

我们敏锐地发现了一个被忽视但极具价值的落地场景：**企业治理运维（GovernanceOps）**。企业战略会、经营分析会、重大决策事项终究是一系列需协同、需追踪、需问责的治理流程，但现状往往是"人人负责，无人负责"。

GovernanceOps 用本体推理技术，将企业决策从主观"人治"推向可验证、可追踪、可审计的机制治。

<video src="examples/GovernanceOps-demo演示视频.mp4" controls width="100%" poster="examples/GovernanceOps-demo-poster.png"></video>

> 🔗 视频无法播放？[点击此处直接查看](./examples/GovernanceOps-demo演示视频.mp4)

---

## 与《当LLM不够用了》的关系

此项目是知乎专栏/书籍 **《当LLM不够用了——本体推理的企业决策实践》** 第十章「OntologyOps：让本体像代码一样被管理」的工程实践载体。

| 书籍（第十章） | 本项目 |
|--------------|--------|
| 理论设计 | 工程实现 |
| 架构文档 | 可运行代码 |
| Why & What | How |

> 全书论证"为什么 LLM 不够用"；OntologyOps 回答"行业放弃本体后，如何让本体重新可用"。

---

## 项目结构

```
ontologyops/
├── README.md                # 本文件
├── docs/
│   └── OntologyOps方案.md    # 完整方案文档（第十章的详细版本）
├── ontology/                # 示例本体仓库
│   ├── concepts/
│   ├── relations/
│   ├── rules/
│   ├── constraints/
│   └── taxonomy/
├── compiler/                # Knowledge Compiler 实现
├── ci/                      # Ontology CI 检查规则
├── runtime/                 # Reasoning Runtime
└── agents/                  # A2A Agent 体系
```

---

## 快速开始

```bash
# 克隆仓库
git clone git@github.com:georgewangchn/OntologyOps.git
cd OntologyOps

# 安装依赖
pip install -r requirements.txt

# 运行示例推理
python examples/basic_inference.py
```

*详细文档：见 [docs/OntologyOps方案.md](./docs/OntologyOps方案.md)*

---

## 作者

**森林瀑布** — 本体推理 × 企业决策 × AI 实战

- 知乎：[森林瀑布](https://www.zhihu.com/)
- 配套书籍：《当LLM不够用了——本体推理的企业决策实践》

---

## License

本仓库采用**双重许可**：

| 范围 | 许可协议 | 说明 |
|------|---------|------|
| **代码** | [MIT](LICENSE) | 所有脚本、工具、配置文件可自由使用、修改、商用 |
| **书籍内容** | [CC BY-NC-SA 4.0](LICENSE-BOOK) | 署名 + 非商业 + 相同方式共享；禁止将书籍文本用于商业目的 |

> 详见 [LICENSE-BOOK](LICENSE-BOOK) 了解书籍内容的完整许可条款。

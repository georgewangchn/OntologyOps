# OntologyOps 协议 · Ontology Repo 支柱 (v1)

本目录是 OntologyOps 六大组件之一 **Ontology Repo**（本体代码仓库）的**规范 canonical 源**——即"一个实现要成为 OntologyOps 合规的 Ontology Repo，必须满足什么"。

## 文件

| 文件 | 作用 |
|---|---|
| [`PROTOCOL.md`](./PROTOCOL.md) | **抽象协议契约**（语义级、格式无关）：核心机制层 R1–R6 + 领域 Profile。 |
| [`ontology.schema.json`](./ontology.schema.json) | **参考编码 (reference encoding, non-exclusive)**：一种通过协议的本体序列化（LLM 友好、diff 友好的 YAML DSL）的 JSON Schema。 |
| [`conformance.yaml`](./conformance.yaml) | **符合性条款**：每条标注 `profile: core`（领域中立）或 `profile: governance`（Governance Profile）。 |

## 分层：核心机制 + 领域 Profile

OntologyOps 定位为**领域中立**的方法论（其自身材料横跨设备/医疗/治理），故协议分两层：

- **核心机制层（`core`，领域中立）**：声明式本体、OWL 2 DL 编译、以 result_key 暴露语义分类、版本化(diff/tag/rollback)、标准导出、自证符合性——任何领域的 Ontology Repo 都须满足。
- **领域 Profile（领域专属）**：在核心之上追加的语义要求。本版本随附 **Governance Profile**（Decision / governed / 优先级关键类），由 GovernanceOps 满足。其它领域（医疗、设备…）可定义自己的 profile 而不动核心层。

> **为什么这样分**：若把治理专属条款当成"协议本体"，就会判定 OntologyOps 自己的另一实证（宠物诊断本体）"不符合 OntologyOps 协议"——与其领域中立定位自相矛盾。分层消除该矛盾，也让协议能被多领域实现 target（这正是"协议"区别于"某框架配置"之处）。当前只随附 Governance Profile，**不预置多-profile 注册表/插件框架**（Ontology Repo 支柱现仅 1 个实现，避免 N=1 上的过度抽象）。

> ⚠️ **非符合性目标**：教学范式演示（本仓库 `labs/` 的 P1–P6 / PL1–PL6）**不以符合本协议为目标**——它们讲清各推理范式，而协议是为生产级、会持续演化的本体仓库准备的工程纪律。

## 参考实现：GovernanceOps

协议不绑定格式或技术栈——但它由一个**可运行的参考实现**长出来、并被它持续验证：

- 仓库：**[github.com/georgewangchn/GovernanceOps](https://github.com/georgewangchn/GovernanceOps)**
- 落地：`ontology/govops.onto.yaml`（本体 DSL 唯一事实源）→ 编译成 owlready2 TBox → HermiT OWL 2 DL 分类 → 生成标准 W3C Turtle。
- 版本化：`govops onto validate / build / commit / log / diff / tag / rollback`（SQLite 内容寻址版本仓库）。
- 自证合规：`govops onto conformance --json` 对自身本体跑本目录的 `conformance.yaml`，全绿即"符合 OntologyOps Ontology Repo 协议"的机器可读证据。

> **canonical 源就是这里**：GovernanceOps 的 `ontology/schema/{ontology.schema.json,conformance.yaml}` 与 `ontology/PROTOCOL.md` 与本目录逐字一致；schema 校验的正是参考 DSL、conformance 跑的正是参考实现，故协议与实现锁步、不漂移。

## 当前范围与诚实边界

- ✅ 已在参考实现中跑通：声明式本体 (R1)、OWL 2 DL 编译+HermiT 分类 (R2)、语义分类 result_key (R3)、版本化 **Diff / Tag / Rollback** (R4 的一部分)、标准 Turtle 导出 (R5)、自证符合性 (R6)。
- 🚧 **Branch / Merge**（本体分支与三方合并）：白皮书 §6.1 列出的能力，本版协议**尚未纳入符合性**，作为下一增量。当前交付线性版本历史 + Diff/Tag/Rollback。
- 🚧 闭世界过程式规则（优先级阈值等）目前留在实现侧，作为后续协议增量（预留 DSL `rules:` 段）。

## 许可

本目录下的协议规范文件（PROTOCOL.md、ontology.schema.json、conformance.yaml、README.md）
采用 **[CC BY 4.0](./LICENSE)** 许可协议——允许商业实现，仅要求署名。

这与仓库其余部分不同：代码（`labs/`）用 MIT。详见仓库根目录的
[分层许可说明](../../README.md#-license)。

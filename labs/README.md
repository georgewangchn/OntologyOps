# 推理实战营（Reasoning Labs）

本目录包含「当LLM不够用了」系列的配套代码——P1–P6（多范式推理）与 pl1–pl6（LLM Agent 版），以宠物诊断 CDSS 为贯穿案例。

## 目录结构

```
labs/
├── P1/              # OWL / HermiT 本体推理
├── P2/              # Prolog 逻辑推理
├── P3/              # Jena / SPARQL 查询推理
├── P4/              # 模糊逻辑推理
├── P5/              # 贝叶斯推理
├── P6/              # 仲裁器（多推理机融合）
├── pl1/             # LLM Agent 版 P1
├── pl2/             # LLM Agent 版 P2
├── pl3/             # LLM Agent 版 P3
├── pl4/             # LLM Agent 版 P4
├── pl5/             # LLM Agent 版 P5
├── pl6/             # LLM Agent 版 P6
├── agent_core/      # 共享 Agent 框架（对话、工具注册、Agent 循环）
├── shared_data/     # 共享数据集（症状、疾病、样本病例）
└── tests/           # 测试
```

## 快速开始

```bash
cd labs/P1
pip install -r requirements.txt
# 按该目录 README 运行：构建本体 → HermiT 推理 → 诊断
```

## 设计理念

| 层级 | 范式 | 推理机 | 对应章节 |
|------|------|--------|---------|
| P1 | 本体推理 | HermiT (OWL 2 DL) | 第四章 |
| P2 | 逻辑推理 | SWI-Prolog | 第四章 |
| P3 | 查询推理 | Jena / SPARQL | 第四章 |
| P4 | 模糊推理 | 自实现 | 第九章 |
| P5 | 概率推理 | 自实现 | 第九章 |
| P6 | 仲裁推理 | 多推理机融合 | 第九章 |
| pl1–pl6 | LLM Agent 版 | LLM + 对应推理机 | 第九章 |

> **核心原则**：LLM 永远不进入推理链，只进入知识工程链。pl 系列展示 LLM 作为 Agent 协调推理机，而非替代推理机。

## 许可

本目录代码采用 [MIT](../LICENSE) 许可协议。

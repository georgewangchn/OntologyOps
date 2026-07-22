# PL2 · LLM Agent / Prolog 推理

> 多范式推理实战营 · PL 系列 2/5
> 副标题：当封闭世界遇到开放对话 —— Prolog 的递归推理如何被 LLM 解锁

**作者**：森林瀑布 ｜ **博客**：[senlinpubu.top](https://senlinpubu.top/)

---

## 一、引言：P2 很快，但用户还是不会用

在 P2 中，我们构建了一个 Prolog 规则推理引擎——Horn 子句 + SLD 归结 + 封闭世界假设（CWA），能从症状列表推导疾病，还能递归查询传播链。

但和 P1 一样，用户面对的是：

```python
# P2 的使用方式
case = {
    "pet_type": "cat",
    "symptoms": ["发热", "呕吐", "腹泻"],
}
results, excluded = diagnose(prolog, case)
```

症状名称要精确匹配 Prolog 原子，物种要用英文，还得手动构造 `Prolog` 实例和加载知识库。

**PL2 的目标**：把 P2 的推理能力包一层 LLM Agent，让用户直接说"我的猫又吐又拉还发烧"，Agent 自动完成剩下的所有事——包括 OWL 做不到的传播链查询。

```
用户：「我的猫感冒了，会不会变成猫瘟？」
    ↓  LLM Agent
Agent 自动：
  1. 识别物种 → 猫
  2. 记录症状 → 打喷嚏、流鼻涕
  3. 触发 Prolog 推理 → 确诊猫感冒
  4. 查询传播链 → can_transmit(d002, d001) → 可能继发猫瘟
  5. 返回诊断 + 传播风险提示
```

最后一步——传播链查询——是 PL2 独有的。Prolog 的递归推理能力让 Agent 能回答"会不会变成另一个病"这种前瞻性问题，这是 PL1 的 OWL 引擎做不到的。

---

## 二、架构：同一个 Agent 框架，换一套工具

PL2 与 PL1 共享同一个 `agent_core` 框架。核心设计是**关注点分离**：Agent 循环（LangGraph）与领域知识（Prolog 知识库）完全解耦。

```
┌─────────────────────────────────────────────────────────┐
│                    用户自然语言                          │
│       「我的猫打喷嚏流鼻涕，会不会变猫瘟？」              │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              OntologyAgent (agent_core)                  │
│              ← 与 PL1 完全相同，零改动                    │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ System Prompt │  │  8 个 @tool   │  │  ConversationState │ │
│  │ (角色定义)    │  │  (领域工具)    │  │  (对话状态)       │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
│                                                          │
│  LangGraph ReAct 循环：Think → Act → Observe → Repeat   │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              P2 Prolog 推理引擎 (共享)                   │
│  SWI-Prolog + Horn 子句 + SLD 归结 + CWA                │
│  知识库：pet_kb.pl + rules.pl (6 条规则)                │
└─────────────────────────────────────────────────────────┘
```

### 四个注入点

| 注入点 | PL1 中的实现 | PL2 中的实现 |
|--------|-------------|-------------|
| `tools_factory` | `create_pl1_tools` (7 个工具) | `create_pl2_tools` (8 个工具) |
| `diagnose_fn` | `pl1_diagnose` | `pl2_diagnose` |
| `report_builder` | `build_pl1_report` | `build_pl2_report` |
| `system_prompt` | OWL 诊断助手 | Prolog 诊断助手 |

```python
agent = OntologyAgent(
    tools_factory=create_pl2_tools,    # ← PL2 工具（8 个）
    diagnose_fn=pl2_diagnose,          # ← PL2 诊断桥接
    report_builder=build_pl2_report,   # ← PL2 报告构建
    system_prompt=SYSTEM_PROMPT,       # ← Prolog 兽医助手
    api_key="sk-xxx",
    model="gpt-4o",
)
```

**Agent 框架零改动复用**——这就是关注点分离的价值。

---

## 三、八个工具

PL2 比 PL1 多一个工具（`query_transmit_chain`），利用 Prolog 的递归推理能力：

| # | 工具名 | 功能 | PL1 有无 |
|---|--------|------|---------|
| 1 | `lookup_symptom_prolog` | 在 Prolog 知识库中查找症状 | ✅ 对应 |
| 2 | `lookup_disease_prolog` | 查找疾病详情 | ✅ 对应 |
| 3 | `add_observation` | 添加观测记录 | ✅ 共享 |
| 4 | `set_pet_info` | 设置宠物信息 | ✅ 共享 |
| 5 | `run_prolog_reasoning` | 运行 SLD 推理 | ✅ 对应 |
| 6 | `explain_reasoning_chain` | 解释推理链 | ✅ 对应 |
| 7 | `query_transmit_chain` | **查询传播链** | ❌ **PL2 独有** |
| 8 | `get_case_summary` | 病例摘要 | ✅ 共享 |

工具 7 是 PL2 的核心差异化能力，下面详细讲解。

---

## 四、Prolog 递归推理：传播链查询

### 为什么 OWL 做不到

在 P2 的 `rules.pl` 中有一条递归规则：

```prolog
% 基本传播：D1 可以传播到 D2
can_transmit(D1, D2) :- transmit_to(D1, D2).

% 递归传播：D1 → D2 → D3
can_transmit(D1, D3) :- transmit_to(D1, D2), can_transmit(D2, D3).
```

知识库中有：
```prolog
transmit_to(d002, d001).  % 猫感冒 → 猫瘟
transmit_to(d005, d004).  % 犬感冒 → 犬细小
```

查询 `can_transmit(d002, Target)` 会返回 `d001`（猫瘟）。

OWL 的 `TransitiveProperty` 可以做传递闭包，但**无法做条件递归**——比如"只有在未治疗的情况下才传播"。Prolog 可以轻松加入条件：

```prolog
% 只有未治疗时才传播
can_transmit(D1, D2) :- 
    transmit_to(D1, D2), 
    \+ treated(case).
```

### Agent 如何调用

```python
@tool
def query_transmit_chain(disease_name: str) -> str:
    """查询疾病传播链。"""
    prolog = _get_prolog()
    # ... 查找疾病 ID ...
    chain = query_transmit(prolog, source_id)
    # ... 格式化输出 ...
```

用户问"猫感冒会不会变猫瘟"，Agent 自动调用 `query_transmit_chain("猫感冒")`，得到传播链：

```
### 传播链：猫感冒
  → 猫瘟（d001）

*传播链由 Prolog 递归推理生成（can_transmit/2）*
```

这是 PL1 完全做不到的——不是工具没写，而是 OWL 推理引擎本身没有递归能力。

---

## 五、CWA vs OWA：同一个病例，不同结论

PL1（OWA）和 PL2（CWA）对"未记录的症状"态度完全不同，这直接影响诊断结果。

```
病例：猫，发热 + 呕吐（未记录是否腹泻）

PL1（OWA）：HermiT 不能因"未断言腹泻"就判定"没有腹泻"
  → 猫瘟的必要症状（发热、呕吐、腹泻）可能都满足
  → 猫瘟 确诊 99%

PL2（CWA）：\+ has(case, '腹泻') 成功
  → 腹泻"不存在"（因为没记录）
  → 猫瘟的必要症状未全匹配
  → 猫瘟 疑似 67%（2/3）
```

| 维度 | PL1（OWA） | PL2（CWA） |
|------|-----------|-----------|
| 未记录的症状 | 可能存在 | 视为不存在 |
| 确诊标准 | 更宽松 | 更严格 |
| 信息不完整时 | 倾向确诊 | 倾向疑似 |
| 适用场景 | 医疗（保守） | 配置/零件库（精确） |

**实践影响**：PL2 的 Agent 需要更积极地追问——少一条症状，可能就从"确诊"降为"疑似"。系统提示词中专门提醒了这一点：

> Prolog vs OWL 的区别：
> - 本系统基于封闭世界假设（CWA）：未记录的症状 = 不存在
> - 因此请确保尽可能完整地收集症状信息

---

## 六、诊断桥接层

和 PL1 一样，PL2 需要一个桥接层将 agent_core 的通用格式转换为 P2 的格式。

### 输入转换

```python
# agent_core 通用格式 → P2 格式
_SPECIES_MAP = {
    "猫": "cat", "喵": "cat", "猫咪": "cat",
    "狗": "dog", "犬": "dog", "狗狗": "dog",
}
```

用户说"猫咪"，Agent 记录为 `species="猫"`，PL2 桥接层转换为 `"cat"` 传给 P2。

### 输出转换

```python
# P2 返回: (results, excluded)
#   results: List[Tuple[disease_name, confidence, is_confirmed, disease_id]]
#   excluded: List[disease_name]
# agent_core 期望: List[Dict]
```

### 降级诊断

当 P2 的 `diagnose()` 函数因任何原因失败时（pyswip 未安装、知识库损坏等），PL2 有降级策略：手动查询 Prolog 计算必要症状匹配度。

---

## 七、报告构建

PL2 的报告与 PL1 格式相同（共用 `DiagnosisReport`），但推理路径说明不同：

```markdown
### 推理路径说明

1. **Horn 子句规则**
   - diagnose/2：必要症状全匹配 + 排除症状未命中 → 确诊
   - suspect/3：部分匹配 + 置信度 = 匹配数 / 总数
   - excluded/2：命中排除症状 → 排除

2. **SLD 归结**
   Prolog 从目标出发，自顶向下归结。

3. **封闭世界假设（CWA）**
   未断言的症状 = 不存在。
   \+ has(case, '咳嗽') 在未记录咳嗽时即为 true。

4. **物种过滤**
   仅保留物种为「猫」的疾病。
```

---

## 八、对话流程示例

以"猫感冒→传播链"为例：

```
🐾 用户：我的猫一直打喷嚏流鼻涕，会不会变成猫瘟？

🤖 Agent 自动决策：
  1. set_pet_info(species="猫")
  2. lookup_symptom_prolog("打喷嚏") → 关联猫感冒、犬感冒
  3. add_observation("打喷嚏")
  4. add_observation("流鼻涕")
  5. get_case_summary() → ✅ 信息已足够
  6. run_prolog_reasoning() → 确诊猫感冒（2/2 = 100%）

## 推理报告

**对象信息**：类型: 猫
**观测记录**：打喷嚏、流鼻涕

### 推理结果

1. ● **猫感冒** — 置信度 100%
   证据：打喷嚏、流鼻涕

---

  7. query_transmit_chain("猫感冒") → 传播链

### 传播链：猫感冒
  → 猫瘟（d001）

🤖 助手：您的猫确诊为猫感冒。需要注意的是，猫感冒如果未及时治疗，
        可能继发猫瘟。建议尽快就医。
```

工具调用序列中，第 7 步 `query_transmit_chain` 是 PL2 独有的——PL1 没有，也不可能实现。

---

## 九、与《当 LLM 不够用了》的对应关系

| 本书章节 | PL1 对应 | PL2 对应 |
|---------|---------|---------|
| 第一章 本体论是什么 | OWL 类/属性/层次 | Prolog 事实/谓词/规则 |
| 第四章 技术基础设施 | HermiT（Tableau） | SWI-Prolog（SLD 归结） |
| 第八章 多范式推理 | OWA + 分类推理 | CWA + 目标驱动 + 递归 |
| 第九章 推理链构建 | explain_subsumption | explain_reasoning_chain + 传播链 |

---

## 十、PL 系列进展

| 编号 | 范式 | 引擎 | 状态 |
|------|------|------|------|
| PL1 | OWL/HermiT | HermiT + SWRL | ✅ 已完成 |
| **PL2** | **Prolog** | **SWI-Prolog** | **✅ 已完成** |
| PL3 | Jena/SPARQL | Apache Jena | ✅ 已完成 |
| PL4 | 模糊逻辑 | scikit-fuzzy | ✅ 已完成 |
| PL5 | 贝叶斯推理 | 纯 Python | ✅ 已完成 |
| PL6 | 多范式融合 | P2+P4+P5 | ✅ 已完成 |

每个 PL 复用同一个 `agent_core` 框架，只需实现自己的四个注入点。PL2 证明了这套框架的可复用性——从 OWL 切到 Prolog，Agent 核心零改动。

---

## 参考资料

1. P2 · Prolog 逻辑推理 — PL2 的推理引擎基础
2. PL1 · LLM Agent / OWL 推理 — 对比项目
3. SWI-Prolog 官方文档：https://www.swi-prolog.org/
4. pyswip：https://github.com/yuce/pyswip
5. LangGraph 文档：https://langchain-ai.github.io/langgraph/
6. 《当 LLM 不够用了——本体推理的企业决策实践》

---

*作者：森林瀑布 | 多范式推理实战营 PL2 | 2026-07-13*

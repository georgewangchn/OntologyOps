# -*- coding: utf-8 -*-
"""
模糊知识库构建模块 —— CSV + 专家知识 → fuzzy_kb.json
对比 P1 的 onto_builder.py：CSV → OWL 本体（equivalent_to + SubClassOf + SWRL 个体）
对比 P2 的 kb_builder.py：CSV → Prolog 事实（disease/necessary/nos 谓词）
对比 P3 的 kb_builder.py：CSV → Turtle 三元组（RDF + Jena 规则）

核心差异：
  P1：疾病是 OWL 类，用 equivalent_to 编码充要条件，HermiT 做分类推理
  P2：疾病是 Prolog 谓词，用事实 + Horn 规则编码，SLD 归结做推理
  P3：疾病是 RDF 资源，用三元组 + Jena 前向链规则编码
  P4：疾病是模糊规则，用隶属度函数 + Mamdani IF-THEN 规则编码

  P1-P3：知识库 = 离散事实（症状有/无 → 疾病是/否）
  P4：知识库 = 连续隶属度函数 + 模糊规则（症状严重度 → 疾病置信度）
"""

import json
import os
import pandas as pd

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
OUTPUT_JSON = os.path.join(LOCAL_DATA_DIR, "fuzzy_kb.json")

# ============================================================
# 专家知识：隶属度函数定义（trapezoidal membership functions）
# ============================================================
# 对比 P1-P3：不需要隶属度函数，因为症状是二元的
# P4：隶属度函数将连续值映射到模糊集合，是模糊推理的核心
#
# trapmf 参数 [a, b, c, d]：
#   a-b: 升边（0→1），b-c: 平顶（1），c-d: 降边（1→0）

MEMBERSHIP_FUNCTIONS = {
    "覆盖率": {
        "低": [0, 0, 0.15, 0.35],
        "中": [0.25, 0.45, 0.55, 0.75],
        "高": [0.65, 0.85, 1.0, 1.0],
    },
    "强度": {
        "低": [0, 0, 0.15, 0.35],
        "中": [0.25, 0.45, 0.55, 0.75],
        "高": [0.65, 0.85, 1.0, 1.0],
    },
    "排除度": {
        "无": [0, 0, 0.05, 0.15],
        "有": [0.1, 0.3, 1.0, 1.0],
    },
    "置信度": {
        "低": [0, 0, 0.15, 0.35],
        "中": [0.25, 0.45, 0.55, 0.75],
        "高": [0.65, 0.85, 1.0, 1.0],
    },
}

# ============================================================
# 专家知识：模糊 IF-THEN 规则（Mamdani 推理，三输入）
# ============================================================
# 三输入：覆盖率 × 强度 × 排除度 → 置信度
#
# 双输入设计解决了旧设计的问题：
#   旧：匹配度 = 覆盖率 × 强度（混合），无法区分"全在但轻"和"缺很多但有一个很重"
#   新：覆盖率 + 强度分离，3×3×2 = 18 种组合，12 条规则（利用部分条件简化）
#
# 规则矩阵（排除度=无）：
#   覆盖率\强度   低    中    高
#   低           低    低    低     ← 缺核心症状，不管多严重
#   中           低    中    中
#   高           中    中    高     ← 全覆盖+高强度 = 确诊
#
# 规则矩阵（排除度=有）：
#   覆盖率\强度   低    中    高
#   低           低    低    低
#   中           低    低    低     ← 排除症状压低
#   高           低    低    中     ← 证据强但排除也出现 → 降一级而非完全排除

FUZZY_RULES = [
    # ── 覆盖率=低：缺核心症状，一律低置信度（3 条省为 1 条）──
    {"if": {"覆盖率": "低"}, "then": {"置信度": "低"}},

    # ── 覆盖率=中 ──
    {"if": {"覆盖率": "中", "强度": "低"}, "then": {"置信度": "低"}},
    {"if": {"覆盖率": "中", "强度": "中", "排除度": "无"}, "then": {"置信度": "中"}},
    {"if": {"覆盖率": "中", "强度": "中", "排除度": "有"}, "then": {"置信度": "低"}},
    {"if": {"覆盖率": "中", "强度": "高", "排除度": "无"}, "then": {"置信度": "中"}},
    {"if": {"覆盖率": "中", "强度": "高", "排除度": "有"}, "then": {"置信度": "低"}},

    # ── 覆盖率=高 ──
    {"if": {"覆盖率": "高", "强度": "低", "排除度": "无"}, "then": {"置信度": "中"}},
    {"if": {"覆盖率": "高", "强度": "低", "排除度": "有"}, "then": {"置信度": "低"}},
    {"if": {"覆盖率": "高", "强度": "中", "排除度": "无"}, "then": {"置信度": "中"}},
    {"if": {"覆盖率": "高", "强度": "中", "排除度": "有"}, "then": {"置信度": "低"}},
    {"if": {"覆盖率": "高", "强度": "高", "排除度": "无"}, "then": {"置信度": "高"}},
    {"if": {"覆盖率": "高", "强度": "高", "排除度": "有"}, "then": {"置信度": "中"}},
]


def build_kb(diseases_csv=None, symptoms_csv=None, output_path=None):
    """
    从 CSV + 专家知识生成模糊知识库 JSON 文件

    输出 fuzzy_kb.json 包含三部分：
      1. 隶属度函数定义（专家知识，本文件中硬编码）
      2. 模糊规则定义（专家知识，本文件中硬编码）
      3. 疾病-症状关系（从 diseases.csv 加载）
      4. 症状基线严重度（从 symptoms.csv 加载）
    """
    if diseases_csv is None:
        diseases_csv = os.path.join(SHARED_DATA_DIR, "diseases.csv")
    if symptoms_csv is None:
        symptoms_csv = os.path.join(SHARED_DATA_DIR, "symptoms.csv")
    if output_path is None:
        output_path = OUTPUT_JSON

    # ── 加载疾病数据 ─────────────────────────────
    df = pd.read_csv(diseases_csv, encoding="utf-8-sig")

    diseases = []
    for _, row in df.iterrows():
        did = row["疾病ID"]
        name = row["疾病名称"]
        species = str(row.get("物种", "pet")).lower()

        necessary = []
        nec_str = row.get("必要症状", "")
        if pd.notna(nec_str) and nec_str.strip():
            necessary = [s.strip() for s in nec_str.split(";") if s.strip()]

        exclusion = []
        nos_str = row.get("排除症状", "")
        if pd.notna(nos_str) and nos_str.strip():
            exclusion = [s.strip() for s in nos_str.split(";") if s.strip()]

        diseases.append({
            "id": did,
            "name": name,
            "species": species,
            "necessary_symptoms": necessary,
            "exclusion_symptoms": exclusion,
        })

    # ── 加载症状基线严重度 ───────────────────────
    df_sym = pd.read_csv(symptoms_csv, encoding="utf-8-sig")
    symptom_baselines = dict(zip(
        df_sym["症状名称"],
        df_sym["严重度"].astype(float)
    ))

    # ── 组装知识库 ───────────────────────────────
    kb = {
        "paradigm": "模糊推理（Mamdani）",
        "description": "P4 宠物疾病模糊推理知识库",
        "membership_functions": MEMBERSHIP_FUNCTIONS,
        "fuzzy_rules": FUZZY_RULES,
        "diseases": diseases,
        "symptom_baselines": symptom_baselines,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print(f"✅ 模糊知识库已生成：{output_path}（{os.path.getsize(output_path)} bytes）")
    print(f"   隶属度函数：{len(MEMBERSHIP_FUNCTIONS)} 组")
    print(f"   模糊规则：{len(FUZZY_RULES)} 条")
    print(f"   模糊输入：覆盖率 + 强度 + 排除度 → 置信度（三输入）")
    print(f"   疾病定义：{len(diseases)} 种")
    print(f"   症状基线：{len(symptom_baselines)} 个")
    return output_path


if __name__ == "__main__":
    print("🏗️  开始构建模糊知识库...")
    build_kb()
    print("🎉 完成！可用 reasoner.py 加载并执行模糊推理。")

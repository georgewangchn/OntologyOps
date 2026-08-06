# -*- coding: utf-8 -*-
"""
贝叶斯知识库构建模块 —— CSV + 专家先验 → bayesian_kb.json
对比 P1 的 onto_builder.py：CSV → OWL 本体（equivalent_to + SubClassOf + SWRL 个体）
对比 P2 的 kb_builder.py：CSV → Prolog 事实（disease/necessary/nos 谓词）
对比 P3 的 kb_builder.py：CSV → Turtle 三元组（RDF + Jena 规则）
对比 P4 的 kb_builder.py：CSV → 模糊隶属度函数 + Mamdani 规则

核心差异：
  P1：疾病是 OWL 类，用 equivalent_to 编码充要条件，HermiT 做分类推理
  P2：疾病是 Prolog 谓词，用事实 + Horn 规则编码，SLD 归结做推理
  P3：疾病是 RDF 资源，用三元组 + Jena 前向链规则编码
  P4：疾病是模糊规则，用隶属度函数 + Mamdani IF-THEN 规则编码
  P5：疾病是贝叶斯网络节点，用条件概率表（CPT）编码，概率传播做推理

  P1-P3：症状有/无（二元）→ 疾病是/否（二元）
  P4：症状严重度（连续 0-1）→ 疾病置信度（连续 0-1）
  P5：症状有/无（二元）→ 疾病后验概率（连续 0-1），但推理基础是条件概率而非模糊规则

  P4 vs P5 关键区别：
    P4 的置信度来自模糊规则匹配（覆盖率×强度→置信度），是"匹配程度"
    P5 的置信度来自贝叶斯定理（P(D|S) = P(S|D)×P(D)/P(S)），是"后验概率"
    P4 回答："症状与疾病的模糊匹配程度有多高？"
    P5 回答："给定这些症状，疾病的概率是多少？"
"""

import json
import os
import pandas as pd

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
OUTPUT_JSON = os.path.join(LOCAL_DATA_DIR, "bayesian_kb.json")

# ============================================================
# 专家先验知识：疾病先验概率与症状条件概率
# ============================================================
# 对比 P1-P3：不需要概率，因为推理是确定性的
# 对比 P4：不需要隶属度函数，因为推理是概率性的而非模糊性的
#
# 贝叶斯网络结构：
#   疾病节点（根节点）→ 症状节点（叶子节点）
#   P(D) = 先验概率（该疾病在总体中的发病率）
#   P(S|D) = 疾病存在时症状出现的概率（敏感度/真阳性率）
#   P(S|¬D) = 疾病不存在时症状出现的概率（假阳性率）
#
# 诊断推理（贝叶斯定理）：
#   P(D|S₁,...,Sₙ) ∝ P(D) × ∏ P(Sᵢ|D)
#   （朴素贝叶斯假设：症状在给定疾病时条件独立）

# 疾病先验概率（基于发病率统计）
DISEASE_PRIORS = {
    "D001": 0.08,  # 猫瘟
    "D002": 0.12,  # 猫感冒（常见）
    "D003": 0.06,  # 猫肠炎
    "D004": 0.05,  # 犬细小病毒
    "D005": 0.10,  # 犬感冒（常见）
    "D006": 0.04,  # 犬冠状病毒
    "D007": 0.03,  # 猫尿路感染
    "D008": 0.03,  # 犬尿路感染
    "D009": 0.01,  # 猫艾滋病（罕见）
    "D010": 0.04,  # 犬副流感
}

# 症状条件概率表（CPT）
# P(S|D): 疾病 D 存在时症状 S 出现的概率
# P(S|¬D): 疾病 D 不存在时症状 S 出现的概率（背景噪音）
# 选取必要症状和排除症状构建 CPT
SYMPTOM_CPT = {
    # 疾病D001: 猫瘟
    "D001": {
        "发热":      {"present": 0.90, "absent": 0.15},
        "呕吐":      {"present": 0.85, "absent": 0.10},
        "腹泻":      {"present": 0.80, "absent": 0.12},
        "咳嗽":      {"present": 0.05, "absent": 0.20},  # 排除症状
        "流鼻涕":    {"present": 0.03, "absent": 0.18},  # 排除症状
    },
    # 疾病D002: 猫感冒
    "D002": {
        "打喷嚏":    {"present": 0.90, "absent": 0.12},
        "流鼻涕":    {"present": 0.85, "absent": 0.15},
        "发热":      {"present": 0.10, "absent": 0.20},  # 排除症状
        "呕吐":      {"present": 0.05, "absent": 0.12},  # 排除症状
    },
    # 疾病D003: 猫肠炎
    "D003": {
        "腹泻":      {"present": 0.90, "absent": 0.15},
        "呕吐":      {"present": 0.80, "absent": 0.12},
        "发热":      {"present": 0.10, "absent": 0.20},  # 排除症状
        "咳嗽":      {"present": 0.05, "absent": 0.18},  # 排除症状
    },
    # 疾病D004: 犬细小病毒
    "D004": {
        "呕吐":      {"present": 0.92, "absent": 0.10},
        "腹泻":      {"present": 0.88, "absent": 0.12},
        "精神萎靡":  {"present": 0.85, "absent": 0.08},
        "咳嗽":      {"present": 0.05, "absent": 0.15},  # 排除症状
    },
    # 疾病D005: 犬感冒
    "D005": {
        "打喷嚏":    {"present": 0.88, "absent": 0.10},
        "流鼻涕":    {"present": 0.85, "absent": 0.12},
        "呕吐":      {"present": 0.05, "absent": 0.12},  # 排除症状
        "腹泻":      {"present": 0.05, "absent": 0.12},  # 排除症状
    },
    # 疾病D006: 犬冠状病毒
    "D006": {
        "呕吐":      {"present": 0.85, "absent": 0.10},
        "腹泻":      {"present": 0.82, "absent": 0.12},
        "发热":      {"present": 0.10, "absent": 0.20},  # 排除症状
    },
    # 疾病D007: 猫尿路感染
    "D007": {
        "尿频":      {"present": 0.90, "absent": 0.08},
        "尿急":      {"present": 0.85, "absent": 0.06},
        "尿痛":      {"present": 0.80, "absent": 0.05},
        "腹泻":      {"present": 0.05, "absent": 0.15},  # 排除症状
    },
    # 疾病D008: 犬尿路感染
    "D008": {
        "尿频":      {"present": 0.88, "absent": 0.08},
        "尿急":      {"present": 0.82, "absent": 0.06},
        "腹泻":      {"present": 0.05, "absent": 0.15},  # 排除症状
    },
    # 疾病D009: 猫艾滋病
    "D009": {
        "发热":      {"present": 0.85, "absent": 0.15},
        "淋巴结肿大": {"present": 0.80, "absent": 0.05},
        "腹泻":      {"present": 0.10, "absent": 0.15},  # 排除症状
    },
    # 疾病D010: 犬副流感
    "D010": {
        "咳嗽":      {"present": 0.88, "absent": 0.12},
        "打喷嚏":    {"present": 0.80, "absent": 0.10},
        "腹泻":      {"present": 0.05, "absent": 0.15},  # 排除症状
    },
}


def build_kb(diseases_csv=None, symptoms_csv=None, output_path=None):
    """
    从 CSV + 专家先验生成贝叶斯知识库 JSON 文件

    输出 bayesian_kb.json 包含：
      1. 疾病先验概率 P(D)
      2. 症状条件概率表 P(S|D) 和 P(S|¬D)
      3. 疾病-症状关系（从 diseases.csv 加载，用于物种过滤和证据收集）
      4. 症状基线严重度（从 symptoms.csv 加载，供 P4 对比用）
    """
    if diseases_csv is None:
        diseases_csv = os.path.join(SHARED_DATA_DIR, "diseases.csv")
    if symptoms_csv is None:
        symptoms_csv = os.path.join(SHARED_DATA_DIR, "symptoms.csv")
    if output_path is None:
        output_path = OUTPUT_JSON

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
            "prior": DISEASE_PRIORS.get(did, 0.05),
            "cpt": SYMPTOM_CPT.get(did, {}),
        })

    df_sym = pd.read_csv(symptoms_csv, encoding="utf-8-sig")
    symptom_baselines = dict(zip(
        df_sym["症状名称"],
        df_sym["严重度"].astype(float)
    ))

    kb = {
        "paradigm": "概率推理（贝叶斯网络）",
        "description": "P5 宠物疾病贝叶斯推理知识库",
        "network_structure": "朴素贝叶斯：疾病(根) → 症状(叶)，症状条件独立",
        "inference_method": "P(D|S) ∝ P(D) × ∏ P(Sᵢ|D)",
        "diseases": diseases,
        "symptom_baselines": symptom_baselines,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print(f"✅ 贝叶斯知识库已生成：{output_path}（{os.path.getsize(output_path)} bytes）")
    print(f"   网络结构：朴素贝叶斯（疾病→症状）")
    print(f"   推理方法：P(D|S) ∝ P(D) × ∏ P(Sᵢ|D)")
    print(f"   疾病定义：{len(diseases)} 种（含先验概率 + CPT）")
    print(f"   症状基线：{len(symptom_baselines)} 个")
    return output_path


if __name__ == "__main__":
    print("🏗️  开始构建贝叶斯知识库...")
    build_kb()
    print("🎉 完成！可用 reasoner.py 加载并执行贝叶斯推理。")

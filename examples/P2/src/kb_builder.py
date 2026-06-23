# -*- coding: utf-8 -*-
"""
知识库构建模块 —— CSV → Prolog 事实文件
对比 P1 的 onto_builder.py：CSV → OWL 本体（三层公理编码）

核心差异：
  P1：疾病是 OWL 类，症状是个体，用 equivalent_to/necessary.value 编码
  P2：疾病是 Prolog 谓词，症状是原子，用事实 + 规则编码
"""

import pandas as pd
import os

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
OUTPUT_PL = os.path.join(LOCAL_DATA_DIR, "pet_kb.pl")


def build_kb(diseases_csv=None, output_path=None):
    """
    从 CSV 生成 Prolog 事实文件 pet_kb.pl
    """
    if diseases_csv is None:
        diseases_csv = os.path.join(SHARED_DATA_DIR, "diseases.csv")
    if output_path is None:
        output_path = OUTPUT_PL

    df = pd.read_csv(diseases_csv, encoding="utf-8-sig")

    disease_facts = []
    necessary_facts = []
    nos_facts = []

    for _, row in df.iterrows():
        did = row["疾病ID"].lower()  # Prolog 原子必须小写开头
        name = row["疾病名称"]
        species = str(row.get("物种", "pet")).lower()

        disease_facts.append(f"disease({did}, '{name}', {species}).")

        nec_str = row.get("必要症状", "")
        if pd.notna(nec_str) and nec_str.strip():
            for sname in nec_str.split(";"):
                sname = sname.strip()
                if sname:
                    necessary_facts.append(f"necessary({did}, '{sname}').")

        nos_str = row.get("排除症状", "")
        if pd.notna(nos_str) and nos_str.strip():
            for sname in nos_str.split(";"):
                sname = sname.strip()
                if sname:
                    nos_facts.append(f"nos({did}, '{sname}').")

    lines = []
    lines.append("% -*- coding: utf-8 -*-")
    lines.append("% ============================================================")
    lines.append("% P2 宠物疾病知识库（由 kb_builder.py 从 CSV 自动生成）")
    lines.append("% 推理范式：Prolog 规则推理（Horn 子句 + CWA）")
    lines.append("% ============================================================")
    lines.append("")

    lines.append("% --- 疾病定义 ---")
    lines.extend(disease_facts)
    lines.append("")

    lines.append("% --- 必要症状 ---")
    lines.extend(necessary_facts)
    lines.append("")

    lines.append("% --- 排除症状 ---")
    lines.extend(nos_facts)
    lines.append("")

    # 传播关系（演示 Prolog 递归能力）
    lines.append("% --- 疾病传播关系（演示 Prolog 递归推理）---")
    lines.append("transmit_to(d002, d001).  % 猫感冒未治疗可能继发猫瘟")
    lines.append("transmit_to(d005, d004).  % 犬感冒未治疗可能继发犬细小")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ Prolog 知识库已生成：{output_path}（{os.path.getsize(output_path)} bytes）")
    return output_path


if __name__ == "__main__":
    print("🏗️  开始构建 Prolog 知识库...")
    build_kb()
    print("🎉 完成！可用 SWI-Prolog 加载：swipl -s src/rules.pl -s data/pet_kb.pl")

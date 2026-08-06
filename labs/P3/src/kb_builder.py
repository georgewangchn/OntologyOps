# -*- coding: utf-8 -*-
"""
知识库构建模块 —— CSV → Turtle 三元组（pet.ttl）
对比 P1 的 onto_builder.py：CSV → OWL 本体（equivalent_to + SubClassOf + SWRL 个体）
对比 P2 的 kb_builder.py：CSV → Prolog 事实（disease/necessary/nos 谓词）

核心差异：
  P1：疾病是 OWL 类，用 equivalent_to 编码充要条件
  P2：疾病是 Prolog 谓词，用事实 + 规则编码
  P3：疾病是 RDF 资源，用三元组编码，推理由 Jena 规则引擎在查询时执行
"""

import pandas as pd
import os

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
OUTPUT_TTL = os.path.join(LOCAL_DATA_DIR, "pet.ttl")


def build_kb(diseases_csv=None, output_path=None):
    """从 CSV 生成 Turtle 三元组文件 pet.ttl"""
    if diseases_csv is None:
        diseases_csv = os.path.join(SHARED_DATA_DIR, "diseases.csv")
    if output_path is None:
        output_path = OUTPUT_TTL

    df = pd.read_csv(diseases_csv, encoding="utf-8-sig")

    lines = []
    lines.append("@prefix :    <http://petbps.com/ontology/pet_disease#> .")
    lines.append("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    lines.append("@prefix rdfs:<http://www.w3.org/2000/01/rdf-schema#> .")
    lines.append("@prefix owl: <http://www.w3.org/2002/07/owl#> .")
    lines.append("")

    # 类定义
    lines.append("# === 类定义 ===")
    lines.append(":疾病 a owl:Class .")
    lines.append(":症状 a owl:Class .")
    lines.append(":物种 a owl:Class .")
    lines.append(":病例 a owl:Class .")
    lines.append("")
    lines.append("# === 物种个体 ===")
    lines.append(":cat rdf:type :物种 ; rdfs:label \"cat\" .")
    lines.append(":dog rdf:type :物种 ; rdfs:label \"dog\" .")
    lines.append("")

    # 对象属性
    lines.append("# === 对象属性 ===")
    lines.append(":has a owl:ObjectProperty ; rdfs:domain :病例 ; rdfs:range :症状 .")
    lines.append(":has_species a owl:ObjectProperty ; rdfs:range :物种 .")
    lines.append(":necessary a owl:ObjectProperty ; rdfs:domain :疾病 ; rdfs:range :症状 .")
    lines.append(":nos a owl:ObjectProperty ; rdfs:domain :疾病 ; rdfs:range :症状 .")
    lines.append(":suspected a owl:ObjectProperty ; rdfs:range :疾病 .")
    lines.append(":excluded a owl:ObjectProperty ; rdfs:range :疾病 .")
    lines.append(":diagnosed a owl:ObjectProperty ; rdfs:range :疾病 .")
    lines.append(":contain a owl:ObjectProperty, owl:TransitiveProperty .")
    lines.append("")

    # 疾病个体
    lines.append("# === 疾病个体 ===")
    for _, row in df.iterrows():
        did = row["疾病ID"].lower()
        name = row["疾病名称"]
        species = str(row.get("物种", "pet")).lower()

        # 疾病基本信息
        lines.append(":{} rdf:type :疾病 ; rdfs:label \"{}\" ; :has_species :{} .".format(did, name, species))

        # 必要症状
        nec_str = row.get("必要症状", "")
        if pd.notna(nec_str) and nec_str.strip():
            for sname in nec_str.split(";"):
                sname = sname.strip()
                if sname:
                    lines.append(":{} :necessary :{} .".format(did, sname))

        # 排除症状
        nos_str = row.get("排除症状", "")
        if pd.notna(nos_str) and nos_str.strip():
            for sname in nos_str.split(";"):
                sname = sname.strip()
                if sname:
                    lines.append(":{} :nos :{} .".format(did, sname))
        lines.append("")

    # 症状个体
    symptoms_csv = os.path.join(SHARED_DATA_DIR, "symptoms.csv")
    if os.path.exists(symptoms_csv):
        df_sym = pd.read_csv(symptoms_csv, encoding="utf-8-sig")
        lines.append("# === 症状个体 ===")
        for _, row in df_sym.iterrows():
            sname = row["症状名称"]
            lines.append(":{} rdf:type :症状 ; rdfs:label \"{}\" .".format(sname, sname))
        lines.append("")

    # 传播关系（演示 Jena 传递闭包）
    # d010 → d005 → d004 构成长度 2 的链，传递闭包规则可触发
    lines.append("# === 传播关系（演示 Jena 前向链传递闭包）===")
    lines.append(":d002 :contain :d001 .  # 猫感冒 → 猫瘟")
    lines.append(":d005 :contain :d004 .  # 犬感冒 → 犬细小")
    lines.append(":d010 :contain :d005 .  # 犬副流感 → 犬感冒（构成 d010→d005→d004 链）")
    lines.append("")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ Turtle 知识库已生成：{output_path}（{os.path.getsize(output_path)} bytes）")
    return output_path


if __name__ == "__main__":
    print("🏗️  开始构建 Turtle 知识库...")
    build_kb()
    print("🎉 完成！Jena Fuseki 会自动加载此文件并执行前向链推理。")

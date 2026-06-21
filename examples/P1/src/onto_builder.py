# -*- coding: utf-8 -*-
"""
本体构建模块 —— 基于真实宠物 CDSS 项目重构
功能：
  1. 定义疾病/症状/物种等核心类
  2. 定义对象属性（necessary / nos / needY 等）
  3. 从 CSV 加载疾病层次结构和症状关联
  4. 保存为 OWL 文件，供推理机加载
"""

from owlready2 import *
import pandas as pd
import os

# ── 路径配置 ─────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
OUTPUT_OWL = os.path.join(DATA_DIR, "pet_ontology.owl")
IRI_BASE = "http://petbps.com/ontology/pet_disease"

# ── 核心构建函数 ──────────────────────────────────────────

def create_ontology(iri=IRI_BASE):
    """创建空白本体，定义所有类、属性"""
    onto_path.append(DATA_DIR)
    onto = get_ontology(iri)

    with onto:
        # —— 核心类 ——
        class 疾病(Thing): pass
        class 症状(Thing): pass
        class 物种(Thing): pass
        class 品种(Thing): pass
        class 年龄(Thing): pass
        class 性别(Thing): pass
        class 部位(Thing): pass
        class 诱因(Thing): pass
        class 病史(Thing): pass
        class 并发症(Thing): pass
        class 检查(Thing): pass
        class 指标(Thing): pass

        # —— 对象属性 ——
        class has(ObjectProperty):
            domain = [疾病]
            range   = [症状]

        class necessary(ObjectProperty):
            """必要症状：罹患某病必须具备的症状"""
            domain = [疾病]
            range   = [症状]

        class nos(ObjectProperty):
            """排除性症状：出现该症状可排除某病"""
            domain = [疾病]
            range   = [症状]

        class minus(ObjectProperty):
            """减分性症状：出现该症状降低某病概率"""
            domain = [疾病]
            range   = [症状]

        class needY(ObjectProperty):
            """肯定性检查指标"""
            domain = [疾病]
            range   = [检查]

        class needN(ObjectProperty):
            """否定性检查指标"""
            domain = [疾病]
            range   = [检查]

        class history(ObjectProperty):
            domain = [疾病]
            range   = [病史]

        class concurrent(ObjectProperty):
            """并发症"""
            domain = [疾病]
            range   = [并发症]

        class contain(ObjectProperty, TransitiveProperty):
            """传染性（传递性）"""
            pass

        # ── SWRL 规则用属性 ─────────────────────
        class suspected(ObjectProperty):
            """疑似疾病：病例疑似罹患某病（由 SWRL 规则推断）"""
            domain = [Thing]
            range   = [疾病]

        class excluded(ObjectProperty):
            """排除疾病：因排除症状而排除某病（由 SWRL 规则推断）"""
            domain = [Thing]
            range   = [疾病]

    print(f"✅ 本体框架已创建：{iri}")
    return onto


def load_diseases(onto, csv_path=None):
    """
    从 diseases.csv 加载疾病层次结构
    CSV 列：疾病ID, 疾病名称, 物种, 父类名称
    """
    if csv_path is None:
        csv_path = os.path.join(DATA_DIR, "diseases.csv")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    with onto:
        for _, row in df.iterrows():
            disease_id   = row["疾病ID"]
            name        = row["疾病名称"]
            pet_type    = str(row.get("物种", "pet")).lower()
            father_name = row.get("父类", "")

            # 创建疾病类（紧贴 Thing，后续通过 is_a 建立层次）
            D = types.new_class(disease_id, (onto.疾病,))
            D.label.append(name)

            # 建立父子层次
            if pd.notna(father_name) and father_name:
                father = onto[father_name]
                if father:
                    D.is_a.append(father)
                    print(f"  {name} → 父类：{father_name}")
                else:
                    print(f"  ⚠️  未找到父类：{father_name}（{name}）")
            else:
                # 顶级疾病，直接挂到 疾病 下
                D.is_a.append(onto.疾病)

    print(f"✅ 已加载 {len(df)} 个疾病")
    return onto


def load_symptoms(onto, csv_path=None):
    """
    从 symptoms.csv 加载「疾病-必要症状」关联
    （简化版：实际项目中从数据库读取更完整）
    """
    if csv_path is None:
        csv_path = os.path.join(DATA_DIR, "symptoms.csv")
    if not os.path.exists(csv_path):
        print(f"⚠️  未找到 {csv_path}，跳过症状加载")
        return onto

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    with onto:
        for _, row in df.iterrows():
            symptom_name = row["症状名称"]
            # 创建症状个体
            s = onto.症状(symptom_name)
            if "严重度" in row and pd.notna(row["严重度"]):
                s.label.append(f"{symptom_name}(严重度:{row['严重度']})")

    print(f"✅ 已加载 {len(df)} 个症状")
    return onto


def add_symptom_relations(onto, csv_path=None):
    """
    根据 diseases.csv 中的「必要症状」列，为疾病类添加 OWL 属性限制
    （让 HermiT 能真正推理：满足必要条件 → 推断属于该疾病）
    格式：必要症状 = "发热;呕吐;腹泻"（分号分隔）
    """
    if csv_path is None:
        csv_path = os.path.join(DATA_DIR, "diseases.csv")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    with onto:
        for _, row in df.iterrows():
            disease_id = row["疾病ID"]
            d = onto[disease_id]
            if d is None:
                continue

            # 必要症状 → 用 necessary.value[症状个体] 限制
            nec_str = row.get("必要症状", "")
            if pd.notna(nec_str) and nec_str.strip():
                for sname in nec_str.split(";"):
                    sname = sname.strip()
                    # 获取症状个体（已在 load_symptoms 中创建）
                    s_ind = onto[sname]
                    if s_ind is None:
                        # 若尚未创建，先创建症状个体
                        s_ind = onto.症状(sname)
                    # 添加属性限制：该类个体必须 necessary 关联到 s_ind
                    d.is_a.append(onto.necessary.value(s_ind))

            # 排除症状 → 用 nos.max(0, s_ind) 表示「不能有该症状」
            nos_str = row.get("排除症状", "")
            if pd.notna(nos_str) and nos_str.strip():
                for sname in nos_str.split(";"):
                    sname = sname.strip()
                    s_ind = onto[sname]
                    if s_ind is None:
                        s_ind = onto.症状(sname)
                    d.is_a.append(onto.nos.max(0, s_ind))

    print("✅ 症状-疾病关系已建立")
    return onto


def save_ontology(onto, output_path=None):
    """保存本体为 OWL/RDF XML 格式"""
    if output_path is None:
        output_path = OUTPUT_OWL
    onto.save(file=output_path, format="rdfxml")
    print(f"✅ 本体已保存：{output_path}（{os.path.getsize(output_path)} bytes）")
    return output_path


# ── CLI 入口 ─────────────────────────────────────────────

if __name__ == "__main__":
    print("🏗️  开始构建宠物疾病本体...")
    onto = create_ontology()
    onto = load_diseases(onto)
    onto = load_symptoms(onto)
    onto = add_symptom_relations(onto)
    save_ontology(onto)
    print("🎉 完成！可用 Protégé 或 owlready2 加载查看。")

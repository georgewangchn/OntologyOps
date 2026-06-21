# -*- coding: utf-8 -*-
"""
推理机模块 —— 基于真实宠物 CDSS 项目重构
功能：
  1. 加载已构建的 OWL 本体
  2. 嵌入 SWRL 规则（通过 owlready2.Imp）
  3. 调用 HermiT 推理机（通过 owlready2 封装）
  4. 对输入病例执行「症状 → 疾病」推理
  5. 输出按置信度排序的疾病列表
"""

from owlready2 import *
from swrl_rules import apply_swrl_rules  # 嵌入 SWRL 规则
import json
import os

# ── 路径配置 ─────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
DEFAULT_OWL = os.path.join(DATA_DIR, "pet_ontology.owl")
IRI_BASE    = "http://petbps.com/ontology/pet_disease"


# ── 推理函数 ──────────────────────────────────────

def load_ontology(owl_path=None):
    """加载 OWL 本体文件"""
    if owl_path is None:
        owl_path = DEFAULT_OWL
    if not os.path.exists(owl_path):
        raise FileNotFoundError(f"未找到本体文件：{owl_path}\n请先运行 onto_builder.py 生成本体。")

    onto_path.append(DATA_DIR)
    onto = get_ontology(f"file://{os.path.abspath(owl_path)}").load()
    print(f"✅ 本体已加载：{len(list(onto.classes()))} 个类")
    return onto


def run_reasoner(onto, reasoner="hermit"):
    """
    执行推理
    :param reasoner: "hermit" | "pellet" | "jfact"
    """
    print(f"🧠 正在调用 {reasoner.upper()} 推理机...")

    if reasoner == "hermit":
        with onto:
            sync_reasoner(HermiT, infer_property_values=True, debug=0)
    elif reasoner == "pellet":
        with onto:
            sync_reasoner(Pellet, infer_property_values=True, debug=0)
    else:
        with onto:
            sync_reasoner(infer_property_values=True, debug=0)

    print(f"✅ 推理完成")
    return onto


def diagnose(onto, case_dict):
    """
    对一个病例执行诊断推理
    :param case_dict: 病例字典，格式：
        {
          "pet_type": "cat",
          "symptoms": ["发热", "呕吐", "腹泻"],
          "breed": "英短",
          "age": 2
        }
    :return: 排序后的 (疾病, 置信度) 列表
    """
    # 0. 嵌入 SWRL 规则（owlready2.Imp，HermiT 推理时会自动处理）
    onto = apply_swrl_rules(onto)

    with onto:
        # 1. 创建临时个体（代表当前病例）
        case_id   = f"case_{hash(str(case_dict)) % 100000}"
        # 先作为 Thing 的个体，让推理机推断它属于哪个疾病子类
        case_instance = onto.Thing(case_id)

        # 2. 断言症状（用 has 属性关联到症状个体）
        for sname in case_dict.get("symptoms", []):
            s_ind = onto[sname]
            if s_ind is None:
                s_ind = onto.症状(sname)
            case_instance.has.append(s_ind)

        # 3. 物种断言（可选）
        pet_type = case_dict.get("pet_type", "pet").lower()
        # 如果本体中有物种个体，可以关联：
        # if pet_type in onto and onto[pet_type]:
        #     case_instance.be.append(onto[pet_type])

    # 4. 推理（HermiT 会根据 OWL 属性限制 + SWRL 规则推断）
    run_reasoner(onto)

    # 5. 收集推理结果：case_instance 被推断为哪些疾病类的实例
    results = []
    for cls in onto.疾病.descendants():
        if case_instance in cls.instances():
            confidence = _calc_confidence(cls, case_dict, onto)
            results.append((cls, confidence))

    # 5b. 同时收集 SWRL 规则推断的 suspected / excluded 关系
    with onto:
        if hasattr(case_instance, "suspected") and list(case_instance.suspected):
            for d in case_instance.suspected:
                if (d, 0.8) not in results:
                    results.append((d, 0.8))
        if hasattr(case_instance, "excluded") and list(case_instance.excluded):
            # 被排除的疾病从结果中移除（或标为置信度 0）
            results = [(cls, conf) for (cls, conf) in results
                       if cls not in list(case_instance.excluded)]

    # 6. 清理临时个体
    with onto:
        destroy_entity(case_instance)

    # 7. 排序
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def _calc_confidence(disease_cls, case_dict, onto):
    """计算该疾病对当前病例的置信度（解析 is_a / equivalent_to 中的 necessary.value 限制）"""
    symptoms = case_dict.get("symptoms", [])

    # 从 is_a 和 equivalent_to 中解析所有 necessary.value(症状个体) 限制
    restrictions = list(getattr(disease_cls, "is_a", [])) + list(getattr(disease_cls, "equivalent_to", []))

    necessary_symptoms = []
    for res in restrictions:
        try:
            # owlready2 的 Restriction 对象：res.property 和 res.value
            if hasattr(res, "property") and res.property is onto.necessary and hasattr(res, "value") and res.value is not None:
                necessary_symptoms.append(res.value.name)
            # 处理 and_ 组合限制
            elif hasattr(res, "Classes"):  # and_ 对象
                for sub in res.Classes:
                    if hasattr(sub, "property") and sub.property is onto.necessary and hasattr(sub, "value") and sub.value is not None:
                        necessary_symptoms.append(sub.value.name)
        except Exception:
            pass

    if not necessary_symptoms:
        return 0.1  # 无必要症状定义，低置信度

    match_count = sum(1 for s in symptoms if s in necessary_symptoms)
    return min(0.99, match_count / len(necessary_symptoms) + 0.1)


def print_diagnosis(results, top_n=5):
    """格式化打印诊断结果"""
    print("\n" + "─" * 50)
    print("  📋 诊断结果（按置信度排序）")
    print("─" * 50)
    for i, (cls, conf) in enumerate(results[:top_n], 1):
        name = cls.label[0] if cls.label else cls.name
        bar  = "█" * int(conf * 10)
        print(f"  {i}. {name:<20} 置信度：{conf:.2f}  {bar}")
    if len(results) > top_n:
        print(f"  ...（共 {len(results)} 个匹配疾病）")
    print("─" * 50 + "\n")


# ── CLI 入口 ──────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="宠物疾病本体推理")
    parser.add_argument("--input", default="../data/sample_case.json", help="病例 JSON 文件路径")
    parser.add_argument("--reasoner", default="hermit", choices=["hermit", "pellet"], help="推理机选择")
    args = parser.parse_args()

    print("🏥 宠物疾病诊断推理系统")
    print("=" * 50)

    # 加载病例
    with open(args.input, encoding="utf-8") as f:
        case = json.load(f)
    print(f"📋 病例：{case.get('note', args.input)}")
    print(f"   症状：{', '.join(case.get('symptoms', []))}")
    print(f"   物种：{case.get('pet_type', '未知')}")
    print()

    # 加载本体 + 推理
    onto = load_ontology()
    results = diagnose(onto, case)
    print_diagnosis(results)

    if not results:
        print("⚠️  未匹配到任何疾病，请检查本体构建或症状输入。")

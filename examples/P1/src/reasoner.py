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
            sync_reasoner_hermit([onto], infer_property_values=True, debug=0)
    elif reasoner == "pellet":
        with onto:
            sync_reasoner_pellet([onto], infer_property_values=True, debug=0)
    else:
        with onto:
            sync_reasoner([onto], infer_property_values=True, debug=0)

    print(f"✅ 推理完成")
    return onto


def _get_exclusion_symptoms(disease_cls):
    """从疾病类的 comment 注解中提取排除症状列表"""
    for comment in getattr(disease_cls, "comment", []):
        if isinstance(comment, str) and comment.startswith("nos:"):
            return [s.strip() for s in comment[4:].split(";") if s.strip()]
    return []


def _map_kb_to_class(d_kb, onto):
    """将疾病知识个体（如 D001_kb）映射回疾病类（D001）"""
    name = d_kb.name
    if not name.endswith("_kb"):
        return None
    cls = onto[name.replace("_kb", "")]
    return cls


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

    推理流程（三层推理 + 排除）：
      1. OWL 分类：HermiT 根据 equivalent_to 从症状反推疾病类
      2. SWRL 规则：necessary / nos 规则推断 suspected / excluded
      3. Python 排除：检查病例症状是否命中疾病排除症状
    """
    # 0. 嵌入 SWRL 规则（owlready2.Imp，HermiT 推理时会自动处理）
    onto = apply_swrl_rules(onto)

    with onto:
        # 1. 创建临时个体（代表当前病例）
        case_id   = f"case_{hash(str(case_dict)) % 100000}"
        case_instance = Thing(case_id)

        # 2. 断言症状（用 has 属性关联到症状个体）
        for sname in case_dict.get("symptoms", []):
            s_ind = onto[sname]
            if s_ind is None:
                s_ind = onto.症状(sname)
            case_instance.has.append(s_ind)

    # 3. 推理（HermiT 根据 equivalent_to + SWRL 规则推断）
    run_reasoner(onto)

    # 4. OWL 分类结果：case_instance 被推断为哪些疾病类的实例
    results = []
    existing_classes = set()
    for cls in onto.疾病.descendants():
        if cls is onto.疾病:
            continue
        if case_instance in cls.instances():
            confidence = _calc_confidence(cls, case_dict, onto)
            results.append((cls, confidence))
            existing_classes.add(cls)

    # 5. SWRL 规则推断的 suspected（规则1：必要症状匹配 → 疑似）
    with onto:
        if hasattr(case_instance, "suspected") and list(case_instance.suspected):
            for d_kb in case_instance.suspected:
                disease_cls = _map_kb_to_class(d_kb, onto)
                if disease_cls and disease_cls not in existing_classes:
                    conf = _calc_confidence(disease_cls, case_dict, onto)
                    results.append((disease_cls, conf))
                    existing_classes.add(disease_cls)

    # 6. 排除逻辑
    # 6a. SWRL 规则推断的 excluded（规则2：排除症状 → 排除）
    excluded_classes = set()
    with onto:
        if hasattr(case_instance, "excluded") and list(case_instance.excluded):
            for d_kb in case_instance.excluded:
                disease_cls = _map_kb_to_class(d_kb, onto)
                if disease_cls:
                    excluded_classes.add(disease_cls)

    # 6b. Python 排除检查：病例症状是否命中疾病排除症状
    case_symptom_set = set(case_dict.get("symptoms", []))
    filtered = []
    for cls, conf in results:
        if cls in excluded_classes:
            continue
        nos_symptoms = _get_exclusion_symptoms(cls)
        if case_symptom_set & set(nos_symptoms):
            continue
        filtered.append((cls, conf))
    results = filtered

    # 7. 清理临时个体
    with onto:
        destroy_entity(case_instance)

    # 8. 排序
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

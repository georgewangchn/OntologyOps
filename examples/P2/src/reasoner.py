# -*- coding: utf-8 -*-
"""
推理机模块 —— pyswip 调用 SWI-Prolog 执行规则推理
对比 P1 的 reasoner.py：owlready2 调用 HermiT 执行 OWL 分类

核心差异：
  P1：HermiT 做 OWL 分类（equivalent_to 双向推理），Python 收集结果
  P2：Prolog 做目标驱动推理（SLD 归结），Python 直接查询

  P1（OWA）：未断言的症状 ≠ 没有，不能据此排除
  P2（CWA）：未断言的症状 = 没有，\\+ has(P, S) 成功
"""

from pyswip import Prolog
import json
import os

SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
RULES_PL = os.path.join(os.path.dirname(__file__), "rules.pl")
KB_PL = os.path.join(LOCAL_DATA_DIR, "pet_kb.pl")


def load_knowledge_base(prolog=None):
    """加载 Prolog 规则 + 知识库"""
    if prolog is None:
        prolog = Prolog()
    prolog.consult(RULES_PL)
    if not os.path.exists(KB_PL):
        raise FileNotFoundError(f"未找到知识库文件：{KB_PL}\n请先运行 kb_builder.py 生成。")
    prolog.consult(KB_PL)
    print(f"✅ Prolog 知识库已加载")
    return prolog


def diagnose(prolog, case_dict):
    """
    对一个病例执行诊断推理

    推理流程：
      1. 断言病例症状（has 谓词）+ 物种（has_species 谓词）
      2. 查询 diagnose/2（确诊：全匹配 + 排除未命中 + 物种匹配）
      3. 查询 suspect/3（疑似：部分匹配 + 排除未命中 + 物种匹配）
      4. 查询 excluded/2（排除：命中排除症状）
      5. 清理临时断言

    :return: 排序后的 (疾病名, 置信度, 是否确诊) 列表
    """
    patient = "case"
    symptoms = case_dict.get("symptoms", [])
    pet_type = case_dict.get("pet_type", "pet")

    try:
        # 1. 断言症状 + 物种
        for sname in symptoms:
            safe_sname = _escape_prolog_atom(sname)
            prolog.assertz(f"has({patient}, '{safe_sname}')")
        prolog.assertz(f"has_species({patient}, {pet_type})")

        # 2. 确诊查询（必要症状全匹配 + 物种匹配）
        # pyswip 不允许嵌套查询，先收集所有结果再处理
        confirmed = set()
        diagnose_results = list(prolog.query(f"diagnose({patient}, Disease)"))
        for result in diagnose_results:
            confirmed.add(result["Disease"])

        # 3. 疑似查询（部分匹配 + 置信度 + 物种匹配）
        suspect_results = list(prolog.query(f"suspect({patient}, Disease, Confidence)"))

        # 4. 排除查询（用于解释推理链）
        excluded_ids = []
        excluded_results = list(prolog.query(f"excluded({patient}, Disease)"))
        for result in excluded_results:
            excluded_ids.append(result["Disease"])
    finally:
        # 5. 清理临时断言（确保异常时也清理）
        prolog.retractall(f"has({patient}, _)")
        prolog.retractall(f"has_species({patient}, _)")

    # 6. 查询疾病名称（非嵌套，在所有查询完成后）
    results = []
    for result in suspect_results:
        did = result["Disease"]
        conf = float(result["Confidence"])
        is_confirmed = did in confirmed
        disease_name = _get_disease_name(prolog, did)
        results.append((disease_name, conf, is_confirmed, did))

    excluded = []
    seen = set()
    for did in excluded_ids:
        if did not in seen:
            seen.add(did)
            excluded.append(_get_disease_name(prolog, did))

    # 7. 排序：确诊优先，然后按置信度降序
    results.sort(key=lambda x: (not x[2], -x[1]))
    return results, excluded


def _get_disease_name(prolog, disease_id):
    """从知识库查询疾病名称"""
    for result in prolog.query(f"disease({disease_id}, Name, _)"):
        return result["Name"]
    return disease_id


def _escape_prolog_atom(text):
    """转义 Prolog 原子中的特殊字符（防止注入/语法错误）"""
    return str(text).replace("\\", "\\\\").replace("'", "\\'")


def explain(prolog, case_dict):
    """
    生成推理链解释（可追溯的诊断依据）

    :return: 每个候选疾病的推理链
    """
    patient = "case"
    symptoms = case_dict.get("symptoms", [])
    pet_type = case_dict.get("pet_type", "pet")

    try:
        for sname in symptoms:
            safe_sname = _escape_prolog_atom(sname)
            prolog.assertz(f"has({patient}, '{safe_sname}')")
        prolog.assertz(f"has_species({patient}, {pet_type})")

        # 先收集所有查询结果（避免嵌套查询）
        raw_explanations = list(prolog.query(f"explain({patient}, Disease, Explanation)"))
    finally:
        prolog.retractall(f"has({patient}, _)")
        prolog.retractall(f"has_species({patient}, _)")

    # 再查询疾病名称
    explanations = []
    for result in raw_explanations:
        did = result["Disease"]
        exp = result["Explanation"]
        disease_name = _get_disease_name(prolog, did)
        explanations.append({
            "disease_id": did,
            "disease_name": disease_name,
            "matched": _prolog_list_to_str(exp.get("matched", [])),
            "missing": _prolog_list_to_str(exp.get("missing", [])),
            "excluded": _prolog_list_to_str(exp.get("excluded", [])),
        })

    return explanations


def _prolog_list_to_str(prolog_list):
    """将 pyswip 返回的列表转为 Python 字符串列表"""
    if isinstance(prolog_list, list):
        return [str(x) if not isinstance(x, str) else x for x in prolog_list]
    return []


def query_transmit(prolog, disease_id):
    """
    查询疾病传播链（演示 Prolog 递归推理能力）
    OWL/SWRL 无法表达条件递归，这是 Prolog 的独有优势
    """
    raw_results = list(prolog.query(f"can_transmit({disease_id}, Target)"))
    results = []
    for result in raw_results:
        target = result["Target"]
        target_name = _get_disease_name(prolog, target)
        results.append({"from": disease_id, "to": target, "to_name": target_name})
    return results


def print_diagnosis(results, excluded=None):
    """格式化打印诊断结果"""
    print("\n" + "─" * 50)
    print("  📋 诊断结果（Prolog 规则推理 · CWA）")
    print("─" * 50)
    for i, (name, conf, confirmed, did) in enumerate(results[:5], 1):
        tag = " ✅确诊" if confirmed else " ⚠️疑似"
        bar = "█" * int(conf * 10)
        print(f"  {i}. {name:<16} 置信度：{conf:.2f}  {bar}{tag}")
    if excluded:
        print(f"\n  🚫 排除：{', '.join(excluded)}")
    print("─" * 50 + "\n")


# ── CLI 入口 ──────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="宠物疾病诊断（Prolog 规则推理）")
    parser.add_argument("--input", default=os.path.join(SHARED_DATA_DIR, "sample_case.json"), help="病例 JSON 文件路径")
    args = parser.parse_args()

    print("🏥 宠物疾病诊断推理系统（Prolog）")
    print("=" * 50)

    with open(args.input, encoding="utf-8") as f:
        case = json.load(f)
    print(f"📋 病例：{case.get('note', args.input)}")
    print(f"   症状：{', '.join(case.get('symptoms', []))}")
    print(f"   物种：{case.get('pet_type', '未知')}")
    print()

    prolog = load_knowledge_base()
    results, excluded = diagnose(prolog, case)
    print_diagnosis(results, excluded)

    # 打印推理链
    print("  🔗 推理链解释：")
    explanations = explain(prolog, case)
    for exp in explanations:
        print(f"\n  [{exp['disease_name']}]")
        if exp["matched"]:
            print(f"    匹配：{', '.join(exp['matched'])} ✅")
        if exp["missing"]:
            print(f"    缺失：{', '.join(exp['missing'])} ❌")
        if exp["excluded"]:
            print(f"    排除症状命中：{', '.join(exp['excluded'])} 🚫")
        else:
            print(f"    排除症状：无命中 ✅")

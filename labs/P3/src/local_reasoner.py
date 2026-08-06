# -*- coding: utf-8 -*-
"""
本地推理适配器 —— 用 rdflib 模拟 Jena 前向链推理
当 Docker/Fuseki 不可用时，用 rdflib 的 SPARQL + 手动规则执行替代

教学说明：
  生产环境应使用 Jena Fuseki（前向链预计算，SPARQL 查询一体化）
  本模块仅用于本地测试/教学演示，展示规则推理的逻辑
  两者的 SPARQL 查询语法完全一致，切换到 Fuseki 只需改 endpoint
"""

from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import RDF, RDFS
import os

PET = Namespace("http://petbps.com/ontology/pet_disease#")
FUSEKI_DATA = os.path.join(os.path.dirname(__file__), "../data/pet.ttl")

_graph = None


def get_graph():
    """获取全局 Graph（单例）"""
    global _graph
    if _graph is None:
        _graph = Graph()
        _graph.bind("pet", PET)
        _graph.parse(FUSEKI_DATA, format="turtle")
        print(f"✅ 本地图已加载：{len(_graph)} 条三元组")
    return _graph


def apply_forward_rules(graph, case_uri, pet_type="pet"):
    """
    手动执行前向链规则（模拟 Jena GenericRuleReasoner）

    规则1：传递闭包（contain 传递性）
    规则2：疑似推断 has + necessary → suspected（含物种过滤）
    规则3：排除推断 has + nos → excluded
    规则4：确诊推断 suspected + 无 excluded → diagnosed
    """
    case = URIRef(case_uri)

    # 获取病例物种
    case_species = PET[pet_type]

    # 规则1：传递闭包
    changed = True
    while changed:
        changed = False
        for a, _, b in list(graph.triples((None, PET.contain, None))):
            for _, _, c in list(graph.triples((b, PET.contain, None))):
                if (a, PET.contain, c) not in graph:
                    graph.add((a, PET.contain, c))
                    changed = True

    # 规则2：疑似推断（过滤物种）
    for _, _, symptom in list(graph.triples((case, PET.has, None))):
        for disease, _, _ in list(graph.triples((None, PET.necessary, symptom))):
            if (disease, RDF.type, PET.疾病) in graph:
                # 物种过滤：疾病物种必须与病例物种一致
                disease_species = list(graph.objects(disease, PET.has_species))
                if not disease_species or URIRef(case_species) in disease_species:
                    graph.add((case, PET.suspected, disease))

    # 规则3：排除推断
    for _, _, symptom in list(graph.triples((case, PET.has, None))):
        for disease, _, _ in list(graph.triples((None, PET.nos, symptom))):
            if (disease, RDF.type, PET.疾病) in graph:
                graph.add((case, PET.excluded, disease))

    # 规则4：确诊推断（noValue = 无 excluded 三元组）
    for _, _, disease in list(graph.triples((case, PET.suspected, None))):
        if not list(graph.triples((case, PET.excluded, disease))):
            graph.add((case, PET.diagnosed, disease))


def diagnose_local(case_dict):
    """
    本地诊断推理（rdflib + 手动前向链）

    :return: 排序后的 (疾病名, 置信度, 是否确诊) 列表
    """
    graph = get_graph()
    case_uri = str(PET) + "case_temp"
    case = URIRef(case_uri)

    # 断言症状 + 物种
    graph.add((case, RDF.type, PET.病例))
    pet_type = case_dict.get("pet_type", "pet")
    graph.add((case, PET.has_species, PET[pet_type]))
    for sname in case_dict.get("symptoms", []):
        graph.add((case, PET.has, PET[sname]))

    # 执行前向链规则
    apply_forward_rules(graph, case_uri, pet_type)

    # 查询确诊结果
    diagnosed = set()
    for _, _, disease in graph.triples((case, PET.diagnosed, None)):
        diagnosed.add(disease)

    # 查询疑似结果 + 计算置信度（过滤掉已排除的）
    excluded_set = set()
    for _, _, disease in graph.triples((case, PET.excluded, None)):
        excluded_set.add(disease)

    results = []
    suspect_set = set()
    for _, _, disease in graph.triples((case, PET.suspected, None)):
        if disease not in excluded_set:
            suspect_set.add(disease)

    for disease in suspect_set:
        # 获取疾病名称
        name = str(disease).split("#")[-1]
        for _, _, label in graph.triples((disease, RDFS.label, None)):
            name = str(label)
            break

        # 计算置信度
        nec_total = len(list(graph.triples((disease, PET.necessary, None))))
        case_symptoms = set()
        for _, _, s in graph.triples((case, PET.has, None)):
            case_symptoms.add(s)
        nec_symptoms = set()
        for _, _, s in graph.triples((disease, PET.necessary, None)):
            nec_symptoms.add(s)
        matched = len(case_symptoms & nec_symptoms)
        confidence = matched / nec_total if nec_total > 0 else 0

        is_diagnosed = disease in diagnosed
        results.append((name, confidence, is_diagnosed, str(disease)))

    # 查询排除结果
    excluded = []
    for _, _, disease in graph.triples((case, PET.excluded, None)):
        name = str(disease).split("#")[-1]
        for _, _, label in graph.triples((disease, RDFS.label, None)):
            name = str(label)
            break
        if name not in excluded:
            excluded.append(name)

    # 清理临时三元组
    for s, p, o in list(graph.triples((case, None, None))):
        graph.remove((case, p, o))

    # 排序
    results.sort(key=lambda x: (not x[2], -x[1]))
    return results, excluded


def query_transitive_local():
    """查询传递闭包"""
    graph = get_graph()
    print("\n  🔗 传递闭包（前向链预计算）：")
    for a, _, b in graph.triples((None, PET.contain, None)):
        a_name = str(a).split("#")[-1]
        b_name = str(b).split("#")[-1]
        for _, _, label in graph.triples((a, RDFS.label, None)):
            a_name = str(label)
        for _, _, label in graph.triples((b, RDFS.label, None)):
            b_name = str(label)
        print(f"    {a_name} → {b_name}")


def print_diagnosis(results, excluded=None):
    print("\n" + "─" * 50)
    print("  📋 诊断结果（Jena 前向链 + SPARQL）")
    print("─" * 50)
    for i, (name, conf, confirmed, uri) in enumerate(results[:5], 1):
        tag = " ✅确诊" if confirmed else " ⚠️疑似"
        bar = "█" * int(conf * 10)
        print(f"  {i}. {name:<16} 置信度：{conf:.2f}  {bar}{tag}")
    if excluded:
        print(f"\n  🚫 排除：{', '.join(excluded)}")
    print("─" * 50 + "\n")

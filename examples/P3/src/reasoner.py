# -*- coding: utf-8 -*-
"""
推理机模块 —— 通过 SPARQL 查询 Jena Fuseki，推理内置到查询管线
对比 P1 reasoner.py：owlready2 调用 HermiT 做 OWL 分类，Python 收集结果
对比 P2 reasoner.py：pyswip 调用 SWI-Prolog 做目标驱动推理

核心差异：
  P1：先推理（sync_reasoner），再在结果中查询（cls.instances()）
  P2：查询即推理（Prolog query 同时执行规则）
  P3：推理内置到查询（Jena 前向链预计算，SPARQL 查询时自动包含推理结果）
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import json
import os

FUSEKI_QUERY = os.environ.get("FUSEKI_QUERY", "http://localhost:3030/pet/sparql")
FUSEKI_UPDATE = os.environ.get("FUSEKI_UPDATE", "http://localhost:3030/pet/update")
SHARED_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../shared_data")


def get_sparql():
    """获取 SPARQL 查询连接"""
    sparql = SPARQLWrapper(FUSEKI_QUERY)
    sparql.setReturnFormat(JSON)
    return sparql


def get_sparql_update():
    """获取 SPARQL UPDATE 连接"""
    sparql = SPARQLWrapper(FUSEKI_UPDATE)
    sparql.setReturnFormat(JSON)
    return sparql


def load_knowledge_base():
    """检查 Fuseki 连接（知识库由 Fuseki 自动加载）"""
    sparql = get_sparql()
    sparql.setQuery("SELECT COUNT(*) AS ?count WHERE { ?s ?p ?o }")
    try:
        results = sparql.query().convert()
        count = int(results["results"]["bindings"][0]["count"]["value"])
        print(f"✅ Fuseki 连接成功：{FUSEKI_QUERY}（{count} 条三元组）")
        return sparql
    except Exception as e:
        raise ConnectionError(
            f"无法连接 Fuseki：{FUSEKI_QUERY}\n"
            f"请先启动：docker-compose up -d\n"
            f"错误：{e}"
        )


def diagnose(case_dict):
    """
    对一个病例执行诊断推理

    推理流程（推理内置到查询管线）：
      1. 通过 SPARQL UPDATE 断言病例症状（has 三元组）+ 物种
      2. Jena 前向链自动触发规则 2/3/4（suspected/excluded/diagnosed）
      3. SPARQL 查询推理结果（查询时自动包含推断的三元组）
      4. 清理临时三元组

    :return: 排序后的 (疾病名, 置信度, 是否确诊) 列表
    """
    symptoms = case_dict.get("symptoms", [])
    pet_type = case_dict.get("pet_type", "pet")
    case_uri = "http://petbps.com/ontology/pet_disease#case_temp"

    try:
        # 1. 断言症状 + 物种（SPARQL UPDATE）
        insert_parts = [f"<{case_uri}> rdf:type :病例 ."]
        insert_parts.append(f"<{case_uri}> :has_species :{pet_type} .")
        for sname in symptoms:
            insert_parts.append(f"<{case_uri}> :has :{sname} .")
        insert_query = """
            PREFIX : <http://petbps.com/ontology/pet_disease#>
            INSERT DATA {
                __PARTS__
            }
        """.replace("__PARTS__", "\n            ".join(insert_parts))

        sparql_update = get_sparql_update()
        sparql_update.setMethod("POST")
        sparql_update.setQuery(insert_query)
        sparql_update.query()

        # 2. 查询确诊结果（Jena 前向链已自动推断 diagnosed 三元组）
        diagnosed_query = """
            PREFIX : <http://petbps.com/ontology/pet_disease#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?disease ?label WHERE {
                <case_uri> :diagnosed ?disease .
                ?disease rdfs:label ?label .
            } ORDER BY ?label
        """.replace("<case_uri>", f"<{case_uri}>")

        sparql = get_sparql()
        sparql.setMethod("GET")
        sparql.setQuery(diagnosed_query)
        diagnosed_results = sparql.query().convert()
        diagnosed = set()
        for binding in diagnosed_results["results"]["bindings"]:
            diagnosed.add(binding["disease"]["value"])

        # 3. 查询疑似结果（suspected 三元组，排除 excluded，过滤物种）
        suspect_query = """
            PREFIX : <http://petbps.com/ontology/pet_disease#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?disease ?label (COUNT(DISTINCT ?nec) AS ?necessary_count)
            (COUNT(DISTINCT ?matched) AS ?matched_count) WHERE {
                <case_uri> :suspected ?disease .
                ?disease rdfs:label ?label .
                ?disease :necessary ?nec .
                ?disease :has_species ?dspecies .
                <case_uri> :has_species ?cspecies .
                FILTER(?dspecies = ?cspecies)
                OPTIONAL {
                    <case_uri> :has ?matched .
                    ?disease :necessary ?matched .
                }
                FILTER NOT EXISTS { <case_uri> :excluded ?disease }
            } GROUP BY ?disease ?label
            ORDER BY DESC(?matched_count)
        """.replace("<case_uri>", f"<{case_uri}>")

        sparql.setQuery(suspect_query)
        suspect_results = sparql.query().convert()

        results = []
        for binding in suspect_results["results"]["bindings"]:
            disease_uri = binding["disease"]["value"]
            disease_name = binding["label"]["value"]
            nec_count = int(binding["necessary_count"]["value"])
            matched_count = int(binding["matched_count"]["value"])
            confidence = matched_count / nec_count if nec_count > 0 else 0
            is_diagnosed = disease_uri in diagnosed
            results.append((disease_name, confidence, is_diagnosed, disease_uri))

        # 4. 查询排除结果
        excluded_query = """
            PREFIX : <http://petbps.com/ontology/pet_disease#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT DISTINCT ?label WHERE {
                <case_uri> :excluded ?disease .
                ?disease rdfs:label ?label .
            }
        """.replace("<case_uri>", f"<{case_uri}>")

        sparql.setQuery(excluded_query)
        excluded_results = sparql.query().convert()
        excluded = [binding["label"]["value"]
                    for binding in excluded_results["results"]["bindings"]]

    finally:
        # 5. 清理临时三元组（确保异常时也清理）
        delete_query = """
            PREFIX : <http://petbps.com/ontology/pet_disease#>
            DELETE WHERE { <case_uri> ?p ?o }
        """.replace("<case_uri>", f"<{case_uri}>")

        sparql_update = get_sparql_update()
        sparql_update.setMethod("POST")
        sparql_update.setQuery(delete_query)
        try:
            sparql_update.query()
        except Exception:
            pass

    # 6. 排序
    results.sort(key=lambda x: (not x[2], -x[1]))
    return results, excluded


def query_transitive():
    """
    查询传递闭包（演示 Jena 前向链预计算）
    对比 P2 Prolog：递归查询时才计算
    对比 P1 OWL：TransitiveProperty 声明式
    """
    query = """
        PREFIX : <http://petbps.com/ontology/pet_disease#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?from_label ?to_label WHERE {
            ?from :contain ?to .
            ?from rdfs:label ?from_label .
            ?to rdfs:label ?to_label .
        }
    """
    sparql = get_sparql()
    sparql.setQuery(query)
    results = sparql.query().convert()

    print("\n  🔗 传递闭包（Jena 前向链预计算）：")
    for binding in results["results"]["bindings"]:
        print(f"    {binding['from_label']['value']} → {binding['to_label']['value']}")


def print_diagnosis(results, excluded=None):
    """格式化打印诊断结果"""
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="宠物疾病诊断（Jena Fuseki + SPARQL）")
    parser.add_argument("--input", default=os.path.join(SHARED_DATA_DIR, "sample_case.json"), help="病例 JSON 文件路径")
    args = parser.parse_args()

    print("🏥 宠物疾病诊断推理系统（Jena Fuseki）")
    print("=" * 50)

    with open(args.input, encoding="utf-8") as f:
        case = json.load(f)
    print(f"📋 病例：{case.get('note', args.input)}")
    print(f"   症状：{', '.join(case.get('symptoms', []))}")
    print(f"   物种：{case.get('pet_type', '未知')}")
    print()

    load_knowledge_base()
    results, excluded = diagnose(case)
    print_diagnosis(results, excluded)

    query_transitive()

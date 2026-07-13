"""
PL6 工具集 —— 8 个 LangChain @tool 函数

PL6 独有工具：
  - compare_engine_results: 对比五种推理引擎的结果差异
  - explain_arbitration: 解释仲裁器的冲突消解逻辑
"""

import os
import sys
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_P6_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "P6", "src"
)
if _P6_DIR not in sys.path:
    sys.path.insert(0, _P6_DIR)


def create_pl6_tools(state, diagnose_fn, report_builder):
    """创建 PL6 工具集（闭包工厂模式）"""

    @tool
    def lookup_symptom_multi(symptom_name: str) -> str:
        """在多种推理引擎的知识库中查找症状关联疾病。"""
        results = {}
        engine_names = {
            "P4": ("P4模糊", "fuzzy"),
            "P5": ("P5贝叶斯", "bayesian"),
        }

        for engine_key, (label, _) in engine_names.items():
            try:
                if engine_key == "P4":
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "P4", "src"))
                    from reasoner import load_knowledge_base
                    kb = load_knowledge_base()
                    related = []
                    for d in kb["diseases"]:
                        if symptom_name in d.get("necessary_symptoms", []) or symptom_name in d.get("exclusion_symptoms", []):
                            related.append(d["name"])
                    results[label] = related if related else ["无关联"]
                elif engine_key == "P5":
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "P5", "src"))
                    from reasoner import load_knowledge_base
                    kb = load_knowledge_base()
                    related = []
                    for d in kb["diseases"]:
                        cpt = d.get("cpt", {})
                        if symptom_name in cpt:
                            probs = cpt[symptom_name]
                            related.append(f"{d['name']}(P(S|D)={probs['present']:.2f})")
                    results[label] = related if related else ["无关联"]
            except Exception as e:
                results[label] = [f"加载失败: {e}"]

        lines = [f"症状「{symptom_name}」在多引擎知识库中的关联："]
        for label, related in results.items():
            lines.append(f"  {label}: {', '.join(related)}")
        return "\n".join(lines)

    @tool
    def lookup_disease_multi(disease_name: str) -> str:
        """查找疾病在多种推理引擎中的知识表示。"""
        lines = [f"疾病「{disease_name}」的多引擎知识表示："]

        # P4 模糊
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "P4", "src"))
            from reasoner import load_knowledge_base
            kb = load_knowledge_base()
            for d in kb["diseases"]:
                if disease_name in d["name"] or disease_name.upper() in d["id"]:
                    lines.append(f"  P4(模糊): 必要={d.get('necessary_symptoms', [])}, 排除={d.get('exclusion_symptoms', [])}")
                    break
        except Exception as e:
            lines.append(f"  P4(模糊): 加载失败")

        # P5 贝叶斯
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "P5", "src"))
            from reasoner import load_knowledge_base
            kb = load_knowledge_base()
            for d in kb["diseases"]:
                if disease_name in d["name"] or disease_name.upper() in d["id"]:
                    prior = d.get("prior", 0.05)
                    lines.append(f"  P5(贝叶斯): 先验P(D)={prior:.2%}, CPT症状数={len(d.get('cpt', {}))}")
                    break
        except Exception as e:
            lines.append(f"  P5(贝叶斯): 加载失败")

        return "\n".join(lines)

    @tool
    def add_observation(symptom_name: str, severity: str = "中度") -> str:
        """记录观察到的症状。"""
        state.add_observation(symptom_name, severity)
        return f"已记录症状：{symptom_name}（{severity}）。当前已记录 {len(state.observations)} 个症状。"

    @tool
    def set_pet_info(species: str, breed: str = "", age: str = "", sex: str = "") -> str:
        """设置宠物基本信息。"""
        state.set_subject(species=species, breed=breed, age=age, sex=sex)
        return f"已设置宠物信息：{species}，{breed}，{age}岁，{sex}。"

    @tool
    def run_multi_engine_reasoning() -> str:
        """运行多范式分层仲裁推理，返回融合后的诊断结果。"""
        if not state.is_ready_for_reasoning():
            return "信息不足，请先设置宠物信息并记录至少2个症状。"

        case_dict = state.to_case_dict()
        try:
            results = diagnose_fn(case_dict)
        except Exception as e:
            return f"推理失败：{e}"

        if not results:
            return "推理完成，但未找到匹配的疾病。"

        report = report_builder(state, results)
        return report.format_for_user()

    @tool
    def compare_engine_results() -> str:
        """对比五种推理引擎的结果差异（PL6 独有）。"""
        if not state.is_ready_for_reasoning():
            return "信息不足，请先设置宠物信息并记录至少2个症状。"

        case_dict = state.to_case_dict()
        try:
            results = diagnose_fn(case_dict)
        except Exception as e:
            return f"推理失败：{e}"

        lines = ["多引擎结果对比："]
        for r in results[:5]:
            lines.append(f"\n  {r['disease']} (最终: {r['confidence']:.2%} [{r['level']}])")
            if r.get("conflict"):
                lines.append(f"    ⚠️ 存在冲突")
            for engine, info in r.get("engine_results", {}).items():
                lines.append(f"    {engine}: {info['confidence']:.2f} [{info['level']}]")
            lines.append(f"    仲裁：{r.get('arbitration_note', '')}")

        return "\n".join(lines)

    @tool
    def explain_arbitration() -> str:
        """解释仲裁器的冲突消解逻辑（PL6 独有）。"""
        return """仲裁器冲突消解逻辑：

1. 确定性层（P1+P2+P3）一致确诊 → 直接采纳，置信度=1.0
2. 确定性层一致排除 → 直接排除，置信度=0.0
3. 确定性层冲突 → 标记冲突，以贝叶斯后验为准
4. 确定性层部分一致 → 加权融合：贝叶斯×0.6 + 模糊×0.4
5. 模糊与概率差异 > 0.3 → 标注冲突

权重设计理由：
  贝叶斯 0.6 > 模糊 0.4
  因为贝叶斯输出有概率论保证，模糊输出是启发式匹配度
  贝叶斯利用先验知识，模糊不利用
  贝叶斯考虑负证据（未出现症状），模糊忽略"""

    @tool
    def get_case_summary() -> str:
        """返回当前病例摘要。"""
        if not state.subject.species:
            return "信息不足：尚未设置宠物信息。"
        if len(state.observations) < 2:
            return f"信息不足：已记录 {len(state.observations)} 个症状（至少需要2个）。"
        return state.get_summary()

    return [
        lookup_symptom_multi,
        lookup_disease_multi,
        add_observation,
        set_pet_info,
        run_multi_engine_reasoning,
        compare_engine_results,
        explain_arbitration,
        get_case_summary,
    ]

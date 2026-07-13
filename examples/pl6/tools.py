"""
PL6 工具集 —— 8 个 LangChain @tool 函数

PL6 独有工具：
  - compare_engine_results: 对比三种推理引擎的结果差异 + 各引擎似然比
  - explain_arbitration: 解释贝叶斯元推理的融合逻辑

核心变化（对比旧版）：
  旧版：解释分层仲裁（P1-P3 投票 + P4/P5 加权 0.6/0.4）
  新版：解释贝叶斯元推理（各引擎输出转 LR + 乘法融合 + 归一化）
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

        # P2 Prolog (结构化规则)
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "P2", "src"))
            from reasoner import load_knowledge_base
            prolog = load_knowledge_base()
            related = list(prolog.query(f"disease(D, '{disease_name}', Species)"))
            if related:
                did = related[0]["D"]
                nec = list(prolog.query(f"necessary({did}, S)"))
                nos = list(prolog.query(f"nos({did}, S)"))
                lines.append(f"  P2(Prolog): ID={did}, 必要={[r['S'] for r in nec]}, 排除={[r['S'] for r in nos]}")
            else:
                lines.append(f"  P2(Prolog): 未找到")
        except Exception as e:
            lines.append(f"  P2(Prolog): 加载失败")

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
        """运行多范式贝叶斯元推理，返回融合后的诊断结果。"""
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
        """对比三种推理引擎的结果差异及各引擎似然比（PL6 独有）。"""
        if not state.is_ready_for_reasoning():
            return "信息不足，请先设置宠物信息并记录至少2个症状。"

        case_dict = state.to_case_dict()
        try:
            results = diagnose_fn(case_dict)
        except Exception as e:
            return f"推理失败：{e}"

        lines = ["多引擎结果对比（贝叶斯元推理）："]
        for r in results[:5]:
            lines.append(f"\n  {r['disease']} (最终后验: {r['confidence']:.2%} [{r['level']}])")
            if r.get("conflict"):
                lines.append(f"    [!] 似然比方向冲突")
            for engine, info in r.get("engine_results", {}).items():
                lines.append(f"    {engine}: conf={info['confidence']:.2f} [{info['level']}] LR={info['lr']:.2f}")
            lines.append(f"    融合：{r.get('arbitration_note', '')}")

        return "\n".join(lines)

    @tool
    def explain_arbitration() -> str:
        """解释贝叶斯元推理的融合逻辑（PL6 独有）。"""
        return """贝叶斯元推理融合逻辑：

1. 引擎选择
   - P2 (Prolog/SLD, CWA)：确定性推理，提供结构化规则知识
   - P4 (Mamdani 模糊)：提供症状严重度连续信息
   - P5 (朴素贝叶斯)：提供先验概率 + 条件概率表
   - P1/P3 不再运行：与 P2 共享同一知识源，投票=一人投三票

2. 似然比转换（各引擎输出统一为 LR）
   - P2 确定性推理：
     确诊 -> LR=5.0 (强支持)
     疑似 -> LR=1.5 (弱支持)
     排除 -> LR=0.1 (强反对)
   - P4 模糊推理：
     LR = exp(3.0 * (confidence - 0.5))
     conf=0.5 -> LR=1.0 (中性)
     conf=1.0 -> LR=4.48 (强支持)
     conf=0.0 -> LR=0.22 (强反对)
   - P5 贝叶斯推理：
     LR = posterior / prior (后验相对先验的提升倍数)

3. 贝叶斯乘法融合
   P_final(D) proportional to P_prior(D) x LR_struct x LR_fuzzy x LR_bayesian
   归一化后得到最终后验概率分布

4. 冲突检测
   如果各引擎的 LR 方向不一致（一个 >1 支持，一个 <1 反对），
   且最大 LR / 最小 LR > 5.0，标记冲突。

为什么比旧版分层仲裁更好：
   - 旧版权重 0.6/0.4 无理论依据，贝叶斯后验和模糊匹配度语义不同不能加权
   - 新版似然比有概率论保证（贝叶斯定理链式法则）
   - 各引擎增量信息被显式利用：规则知识->LR_struct, 严重度->LR_fuzzy, 先验+CPT->LR_bayesian
   - P1-P3 不再冗余运行，消除假一致性"""

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

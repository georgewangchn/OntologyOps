# -*- coding: utf-8 -*-
"""
SWRL 规则模块 —— 用 owlready2.Imp 实现真实可执行的 SWRL 规则
SWRL（Semantic Web Rule Language）= OWL 表达力 + 规则推理
这些规则会被 HermiT 推理机在执行 sync_reasoner() 时一并处理。

教学说明：
  - 规则 1/2 展示 SWRL 语法（部分功能与 OWL 属性限制重叠，教学演示用）
  - 实际推理主要依靠 OWL 属性限制（necessary.value 等）
  - SWRL 规则展示"规则可以实现但 OWL 限制难以表达"的场景
"""

from owlready2 import *
import os

# ── 规则定义（owlready2.Imp 实现）─────────────────────────────
# 每条规则在 owlready2 中是一个 Imp 实例，通过 set_as_rule() 写入 SWRL

SWRL_RULES = [
    # ── 规则 1：必要症状全匹配 → 疑似疾病 ────────────────
    {
        "name": "necessary_symptom_rule",
        "desc": "病例出现某病的任一必要症状时，标记为疑似该病（部分匹配，全匹配由 equivalent_to 负责）",
    },
    # ── 规则 2：排除性症状 → 排除疾病 ─────────────────────
    {
        "name": "nos_symptom_exclusion",
        "desc": "病例出现某病的排除性症状时，标记为排除该病",
    },
]


_swrl_applied = False


def apply_swrl_rules(onto):
    """
    将 SWRL 规则以 owlready2.Imp 形式嵌入本体。
    HermiT 在执行 sync_reasoner() 时会自动处理这些规则。
    """
    global _swrl_applied
    if _swrl_applied:
        return onto

    print("📏 正在嵌入 SWRL 规则（owlready2.Imp）...")

    with onto:
    # ── 规则 1：必要症状任一匹配 → 疑似疾病 ────────────────
    # 注意：SWRL 无法表达全称量化（"所有必要症状都出现"），
    # 因此此规则在任一必要症状匹配时即触发（部分匹配）。
    # 全匹配由 OWL equivalent_to（Layer 1）负责。
    # has(?p, ?s) ∧ necessary(?d, ?s) ∧ 疾病(?d) ∧ 症状(?s)
    # → suspected(?p, ?d)
        rule1 = Imp()
        rule1.label.append("necessary_symptom_rule")
        rule1.set_as_rule("""
            has(?p, ?s), necessary(?d, ?s), 疾病(?d), 症状(?s)
            -> suspected(?p, ?d)
        """)

        # ── 规则 2：排除性症状 → 排除疾病 ─────────────────────
        # has(?p, ?s) ∧ nos(?d, ?s) ∧ 疾病(?d) ∧ 症状(?s)
        # → excluded(?p, ?d)
        rule2 = Imp()
        rule2.label.append("nos_symptom_exclusion")
        rule2.set_as_rule("""
            has(?p, ?s), nos(?d, ?s), 疾病(?d), 症状(?s)
            -> excluded(?p, ?d)
        """)

    print(f"✅ 已嵌入 {len(SWRL_RULES)} 条 SWRL 规则（owlready2.Imp）")
    print("   HermiT 推理时会自动处理这些规则。")
    _swrl_applied = True
    return onto


def print_rules():
    """打印所有规则（供文档 / Notebook 使用）"""
    print("\n" + "=" * 50)
    print("  SWRL 规则清单（已嵌入本体，可被 HermiT 执行）")
    print("=" * 50)
    for i, rule in enumerate(SWRL_RULES, 1):
        print(f"\n【规则 {i}】{rule['name']}")
        print(f"  说明：{rule['desc']}")
    print("\n" + "=" * 50)


def get_rule_objects(onto):
    """
    返回本体中所有 Imp 规则对象（供高级用户检查规则内容）
    """
    return list(onto.imp_classes())


# ── CLI 入口 ─────────────────────────────────────

if __name__ == "__main__":
    print("📏 SWRL 规则模块（教学演示版）")
    print("=" * 50)
    print("本模块将诊断规则编码为可执行 SWRL，由 HermiT 推理机执行。")
    print()
    print_rules()
    print()
    print("💡 使用方法：")
    print("  from swrl_rules import apply_swrl_rules")
    print("  onto = apply_swrl_rules(onto)")
    print("  # 然后调用 reasoner.run_reasoner(onto)")
    print()
    print("📌 与历史生产系统的区别：")
    print("  生产系统（/owl/data/swrl.ttl）：350+ 条 Jena Rules")
    print("  本教学示例：2 条 SWRL 规则（owlready2.Imp 实现）")

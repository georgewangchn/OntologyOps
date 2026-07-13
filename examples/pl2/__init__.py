"""
PL2 —— P2 (Prolog 逻辑推理) + LLM Agent

架构：
  OntologyAgent (agent_core)
    + create_pl2_tools()        ← 本模块提供
    + pl2_diagnose()            ← 包装 P2 的 Prolog 推理
    + build_pl2_report()        ← 格式化为 DiagnosisReport
    + system_prompt             ← 宠物疾病诊断角色定义

运行：
  cd ontologyops/examples
  python pl2/run.py
"""

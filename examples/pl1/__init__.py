"""
PL1 —— P1 (OWL 本体推理) + LLM Agent

架构：
  OntologyAgent (agent_core)
    + create_pl1_tools()        ← 本模块提供
    + pl1_diagnose()           ← 包装 P1 的 OWL 推理
    + build_pl1_report()        ← 格式化为 DiagnosisReport
    + system_prompt             ← 宠物疾病诊断角色定义

运行：
  cd ontologyops/examples
  python pl1/run.py
"""

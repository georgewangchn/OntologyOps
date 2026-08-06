"""
PL5 — LLM Agent + Bayesian 推理

将 P5 的朴素贝叶斯推理引擎用 LangGraph Agent 包装。
用户用自然语言描述宠物症状，Agent 自动查知识库、收集信息、
触发贝叶斯推理、解释后验概率，还能查询先验概率和似然比。
"""

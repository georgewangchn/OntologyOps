# -*- coding: utf-8 -*-
"""
FastAPI 接口模块 —— 将 Prolog 推理封装为 REST API
复用 swipl-fastapi 的部署模式（Gunicorn + Uvicorn）

对比 P1：P1 的 diagnosis.py 提供 diagnose_api() 但未启动 HTTP 服务
本模块完整提供 HTTP API，可直接 docker部署
"""

from fastapi import FastAPI
from pydantic import BaseModel
from reasoner import load_knowledge_base, diagnose, explain
import asyncio
import os

app = FastAPI(title="P2 · 宠物疾病诊断 API", version="1.0")

# 启动时加载知识库（全局单例）
_prolog = None
_prolog_lock = asyncio.Lock()


def get_prolog():
    global _prolog
    if _prolog is None:
        _prolog = load_knowledge_base()
    return _prolog


class CaseInput(BaseModel):
    pet_type: str = "cat"
    symptoms: list[str]
    breed: str = ""
    age: int = 0


@app.get("/")
async def root():
    return {"message": "P2 · 宠物疾病诊断 API（Prolog 规则推理）"}


@app.post("/diagnose")
async def api_diagnose(case: CaseInput):
    """诊断接口：输入症状，返回疑似疾病列表"""
    prolog = get_prolog()
    case_dict = {"pet_type": case.pet_type, "symptoms": case.symptoms}
    async with _prolog_lock:
        results, excluded = diagnose(prolog, case_dict)
    return {
        "success": True,
        "pet_type": case.pet_type,
        "symptoms": case.symptoms,
        "results": [
            {
                "disease": name,
                "confidence": round(conf, 2),
                "confirmed": is_confirmed,
                "disease_id": did,
            }
            for name, conf, is_confirmed, did in results
        ],
        "excluded": excluded,
    }


@app.post("/explain")
async def api_explain(case: CaseInput):
    """推理链解释接口：返回每个候选疾病的匹配/缺失/排除详情"""
    prolog = get_prolog()
    case_dict = {"pet_type": case.pet_type, "symptoms": case.symptoms}
    async with _prolog_lock:
        explanations = explain(prolog, case_dict)
    return {"success": True, "explanations": explanations}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

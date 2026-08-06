#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# P3 环境初始化脚本
# 用法：bash setup_env.sh
#
# P3 需要 Jena Fuseki（Docker）+ Python SPARQLWrapper
# 对比 P1：需要 JVM（HermiT）+ owlready2-Chinese 补丁
# 对比 P2：需要 SWI-Prolog + pyswip
#
# 说明：Docker 仅用于生产级 Fuseki SPARQL 端点。
# 本地测试（test_p3.py）用 rdflib 模拟前向链推理，无需 Docker。
# 无 Docker 时脚本仍会创建 venv + 安装依赖 + 构建知识库，仅跳过 Fuseki 启动。

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ── 1. 检查 Docker（可选，仅 Fuseki 模式需要）─────────
HAVE_DOCKER=0
if command -v docker &> /dev/null; then
    HAVE_DOCKER=1
    echo "✅ Docker 可用（将启动 Jena Fuseki）"
else
    echo "⚠️  未找到 Docker，跳过 Fuseki 启动。"
    echo "   本地测试（test_p3.py）仍可运行（rdflib 本地模式）。"
    echo "   生产环境请安装 Docker 后运行 docker-compose up -d。"
fi

# ── 2. 创建虚拟环境 ──────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建虚拟环境：$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── 3. 安装依赖 ──────────────────────────────────
echo "📥 安装依赖..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# ── 4. 构建知识库 ────────────────────────────────
echo "🏗️  构建 Turtle 知识库..."
cd "$SCRIPT_DIR/src"
python kb_builder.py

# ── 5. 启动 Fuseki（仅 Docker 可用时）──────────────
if [ "$HAVE_DOCKER" -eq 1 ]; then
    echo "🐳 启动 Jena Fuseki..."
    cd "$SCRIPT_DIR"
    docker-compose up -d

    echo "⏳ 等待 Fuseki 就绪..."
    for i in $(seq 1 30); do
        if curl -sf http://localhost:3030/$/ping &> /dev/null; then
            echo "✅ Fuseki 已就绪：http://localhost:3030"
            break
        fi
        sleep 2
    done

    # ── 6. 验证 SPARQL 端点 ────────────────────────
    echo "✅ 验证 SPARQL 端点..."
    python3 -c "
from SPARQLWrapper import SPARQLWrapper, JSON
s = SPARQLWrapper('http://localhost:3030/pet/sparql')
s.setReturnFormat(JSON)
s.setQuery('SELECT COUNT(*) AS ?c WHERE { ?s ?p ?o }')
r = s.query().convert()
count = r['results']['bindings'][0]['c']['value']
print(f'  Fuseki SPARQL 端点：✅（{count} 条三元组）')
"
fi

echo ""
echo "🎉 环境就绪！运行测试："
echo "   source $VENV_DIR/bin/activate"
echo "   python -m pytest test_p3.py -v"

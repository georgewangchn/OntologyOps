#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# P3 环境初始化脚本
# 用法：bash setup_env.sh
#
# P3 需要 Jena Fuseki（Docker）+ Python SPARQLWrapper
# 对比 P1：需要 JVM（HermiT）+ owlready2-Chinese 补丁
# 对比 P2：需要 SWI-Prolog + pyswip

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ── 1. 检查 Docker ───────────────────────────────
if ! command -v docker &> /dev/null; then
    echo "❌ 未找到 Docker，请先安装"
    exit 1
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

# ── 5. 启动 Fuseki ───────────────────────────────
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

# ── 6. 验证 ──────────────────────────────────────
echo "✅ 验证安装..."
python3 -c "
from SPARQLWrapper import SPARQLWrapper, JSON
s = SPARQLWrapper('http://localhost:3030/pet/sparql')
s.setReturnFormat(JSON)
s.setQuery('SELECT COUNT(*) AS ?c WHERE { ?s ?p ?o }')
r = s.query().convert()
count = r['results']['bindings'][0]['c']['value']
print(f'  Fuseki SPARQL 端点：✅（{count} 条三元组）')
"

echo ""
echo "🎉 环境就绪！运行测试："
echo "   source $VENV_DIR/bin/activate"
echo "   python test_p3.py"

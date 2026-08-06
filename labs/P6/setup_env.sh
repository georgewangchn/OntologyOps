#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# P6 环境初始化脚本
# 用法：bash setup_env.sh
#
# P6 是多范式贝叶斯元推理引擎，融合 P2(Prolog) + P4(模糊) + P5(贝叶斯)。
# 因此 P6 的依赖 = P2 的依赖（pyswip + SWI-Prolog）+ P4 的依赖（scikit-fuzzy 等）。
# P5 是纯标准库实现，无第三方依赖。
# P6 不依赖 P1（OWL/HermiT）：P1/P2/P3 共享同一知识源，取 P2 即可消除冗余。

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ── 1. 检查 SWI-Prolog（P2 引擎需要）──────────────
if ! command -v swipl &> /dev/null; then
    echo "❌ 未找到 SWI-Prolog，请先安装："
    echo ""
    echo "  macOS:  brew install swi-prolog"
    echo "  Ubuntu: sudo apt-get install swi-prolog"
    echo "  Docker: 见 ../P2/docker-compose.yml（使用 swipl:latest 镜像）"
    exit 1
fi
echo "✅ SWI-Prolog: $(swipl --version)"

# ── 2. 检查 JVM（P4 的 scikit-fuzzy 不需要，但 P6 README 提及下游可扩展）──
# P6 本身不需要 JVM，留空即可。

# ── 3. 创建虚拟环境 ──────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建虚拟环境：$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── 4. 安装依赖 ──────────────────────────────────
echo "📥 安装依赖（P2 + P4 的全部依赖，P5 为纯标准库）..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# ── 5. 构建各引擎知识库 ──────────────────────────
echo "🏗️  构建 P2 Prolog 知识库..."
cd "$SCRIPT_DIR/../P2/src"
python kb_builder.py

echo "🏗️  构建 P4 模糊知识库..."
cd "$SCRIPT_DIR/../P4/src"
python kb_builder.py

echo "🏗️  构建 P5 贝叶斯知识库..."
cd "$SCRIPT_DIR/../P5/src"
python kb_builder.py

# ── 6. 验证 ──────────────────────────────────────
echo "✅ 验证安装..."
cd "$SCRIPT_DIR/src"
python3 -c "
import pyswip
import skfuzzy
import numpy
import scipy
print('  P2 桥接（pyswip）：✅')
print('  P4 模糊（scikit-fuzzy）：✅')
print('  P5 纯标准库：✅（无需验证）')
"

echo ""
echo "🎉 环境就绪！运行："
echo "   source $VENV_DIR/bin/activate"
echo "   cd src/"
echo "   python diagnosis.py ../../shared_data/sample_case.json"

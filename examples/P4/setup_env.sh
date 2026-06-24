#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# P4 环境初始化脚本
# 用法：bash setup_env.sh
#
# P4 只需 scikit-fuzzy + numpy + pandas，无需 JVM / SWI-Prolog / Docker
# 对比 P1：需要 JVM（HermiT）+ owlready2-Chinese 补丁
# 对比 P2：需要 SWI-Prolog 运行时
# 对比 P3：需要 Docker（Jena Fuseki）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ── 1. 创建虚拟环境 ──────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建虚拟环境：$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── 2. 安装依赖 ──────────────────────────────────
echo "📥 安装依赖..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# ── 3. 验证 ──────────────────────────────────────
echo "✅ 验证安装..."
python3 -c "
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# 快速验证 scikit-fuzzy 可用
x = np.arange(0, 1.01, 0.01)
mf = fuzz.trapmf(x, [0, 0, 0.3, 0.5])
assert len(mf) == len(x), '隶属度函数长度不匹配'
print('  scikit-fuzzy Mamdani 推理：✅')
"

echo ""
echo "🎉 环境就绪！运行测试："
echo "   source $VENV_DIR/bin/activate"
echo "   python test_p4.py"

#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# P2 环境初始化脚本
# 用法：bash setup_env.sh
#
# P2 需要 SWI-Prolog 运行时 + pyswip Python 桥接库
# 对比 P1：P1 需要 JVM（HermiT）+ owlready2-Chinese 补丁

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ── 1. 检查 SWI-Prolog ──────────────────────────
if ! command -v swipl &> /dev/null; then
    echo "❌ 未找到 SWI-Prolog，请先安装："
    echo ""
    echo "  macOS:  brew install swi-prolog"
    echo "  Ubuntu: sudo apt-get install swi-prolog"
    echo "  Docker: 见 docker-compose.yml（使用 swipl:latest 镜像）"
    exit 1
fi
echo "✅ SWI-Prolog: $(swipl --version)"

# ── 2. 创建虚拟环境 ──────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建虚拟环境：$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── 3. 安装依赖 ──────────────────────────────────
echo "📥 安装依赖..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# ── 4. 验证 ──────────────────────────────────────
echo "✅ 验证安装..."
python3 -c "
from pyswip import Prolog
p = Prolog()
p.assertz('father(john, mich)')
results = list(p.query('father(john, X)'))
assert results, 'pyswip 查询失败'
print('  pyswip + SWI-Prolog：✅')
"

echo ""
echo "🎉 环境就绪！运行测试："
echo "   source $VENV_DIR/bin/activate"
echo "   python test_p2.py"

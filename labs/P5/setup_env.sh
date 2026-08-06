#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# P5 环境初始化脚本
# 用法：bash setup_env.sh
#
# P5 是纯标准库实现（csv/json/os/math），推理引擎无第三方依赖。
# 此脚本仅创建 venv 并安装 pytest（用于跑测试），并构建贝叶斯知识库。

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ── 1. 创建虚拟环境 ──────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建虚拟环境：$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── 2. 安装依赖（仅 pytest）──────────────────────
echo "📥 安装依赖（P5 引擎为纯标准库，仅装 pytest）..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# ── 3. 构建贝叶斯知识库 ──────────────────────────
echo "🏗️  构建贝叶斯知识库..."
cd "$SCRIPT_DIR/src"
python kb_builder.py

# ── 4. 验证 ──────────────────────────────────────
echo "✅ 验证安装..."
python3 -c "
import json, os
kb_path = os.path.join(os.path.dirname(os.path.abspath('.')), 'P5', 'data', 'bayesian_kb.json')
# 直接验证刚构建的文件
kb_path = '../data/bayesian_kb.json'
assert os.path.exists(kb_path), '贝叶斯知识库未生成'
with open(kb_path, encoding='utf-8') as f:
    kb = json.load(f)
assert len(kb['diseases']) >= 10, '疾病数量不足'
print('  贝叶斯知识库：✅（', len(kb['diseases']), '种疾病）')
"

echo ""
echo "🎉 环境就绪！运行测试："
echo "   source $VENV_DIR/bin/activate"
echo "   python -m pytest test_p5.py -v"

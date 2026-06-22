#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# P1 环境初始化脚本
# 用法：bash setup_env.sh
#
# Owlready2-Chinese 仓库只含两个补丁文件（rule.py / reasoning.py），不是可安装包。
# 正确做法：下载 owlready2==0.37 源码 → 覆盖补丁文件 → pip install 打好补丁的源码。

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# ── 1. 创建虚拟环境 ──────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建虚拟环境：$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── 2. 下载 owlready2==0.37 源码 ─────────────────
echo "⬇️  下载 owlready2==0.37 源码..."
pip download owlready2==0.37 --no-binary owlready2 --no-deps -d "$TMP_DIR"
SRC_DIR="$TMP_DIR/$(tar tzf "$TMP_DIR"/Owlready2-0.37.tar.gz | head -1 | cut -d/ -f1)"
tar xzf "$TMP_DIR/Owlready2-0.37.tar.gz" -C "$TMP_DIR"

# ── 3. 覆盖中文补丁文件 ─────────────────────────
echo "🔧 下载并应用 Owlready2-Chinese 补丁..."
git clone --depth=1 https://github.com/georgewangchn/Owlready2-Chinese.git "$TMP_DIR/owlready2-chinese"
cp "$TMP_DIR/owlready2-chinese/rule.py"      "$SRC_DIR/rule.py"
cp "$TMP_DIR/owlready2-chinese/reasoning.py" "$SRC_DIR/reasoning.py"

# ── 4. 从补丁源码安装 ───────────────────────────
echo "📥 安装 owlready2（含中文补丁）..."
pip install "$SRC_DIR"

# ── 5. 安装其余依赖 ─────────────────────────────
echo "📥 安装其余依赖..."
pip install rdflib pandas

# ── 6. 验证 ──────────────────────────────────────
echo "✅ 验证安装..."
python3 -c "
import inspect
import owlready2.rule as rule_mod
from owlready2 import reasoning

src = inspect.getsource(rule_mod._create_rule_parser)
assert 'u4e00' in src, '中文补丁未生效（rule.py）'
print('  SWRL 中文支持：✅')

assert reasoning.JAVA_MEMORY == 1000, '中文补丁未生效（reasoning.py JAVA_MEMORY）'
print('  HermiT 中文解码：✅')
"

echo ""
echo "🎉 环境就绪！运行测试："
echo "   source $VENV_DIR/bin/activate"
echo "   python test_p1.py"

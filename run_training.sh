#!/bin/bash
# run_training.sh — 启动训练脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "启动列车调度器训练"
echo "=========================================="
echo ""

# 切换到项目根目录
cd "$(dirname "$0")"

echo "当前目录: $(pwd)"
echo ""

# 检查 Python 版本
echo "Python 版本:"
python --version
echo ""

# 测试导入
echo "测试导入..."
python test_imports.py
echo ""

# 启动训练
echo "启动训练..."
echo "命令: python -m ai.src.train_scheduler --episodes 5000"
echo ""
python -m ai.src.train_scheduler --episodes 5000

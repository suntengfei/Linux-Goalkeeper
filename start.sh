#!/bin/bash

set -e

echo "========================================"
echo "  Shell监控与AI安全助手 - 启动脚本"
echo "========================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "config.yaml" ]; then
    echo "错误: 找不到 config.yaml 配置文件"
    echo "请复制 config.yaml.example 为 config.yaml 并修改配置"
    exit 1
fi

echo "[1/3] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "  Python版本: $PYTHON_VERSION"

echo "[2/3] 安装依赖..."
pip3 install -q -r requirements.txt 2>/dev/null || pip install -q -r requirements.txt

echo "[3/3] 启动服务..."
echo "  WebSocket服务: ws://localhost:8765"
echo "  Web界面: http://localhost:8080"
echo ""

python3 -m server.main

#!/bin/bash

readonly CONFIG_FILE="config.yaml"
readonly CONFIG_TEMPLATE="config.yaml.example"
readonly REQUIREMENTS_FILE="requirements.txt"
readonly SERVER_MODULE="server.main"

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

echo "========================================"
echo "  Shell监控与AI安全助手 - 启动脚本"
echo "========================================"

if ! cd "${SCRIPT_DIR}"; then
    echo "错误: 无法进入脚本目录 ${SCRIPT_DIR}"
    exit 1
fi

if [ ! -f "${CONFIG_FILE}" ]; then
    echo "错误: 找不到 ${CONFIG_FILE} 配置文件"
    echo "请复制 ${CONFIG_TEMPLATE} 为 ${CONFIG_FILE} 并修改配置"
    exit 1
fi

echo "[1/3] 检查Python环境..."
if ! command -v python3 > /dev/null 2>&1; then
    echo "错误: 未找到Python3，请先安装Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
if [ $? -ne 0 ]; then
    echo "错误: 无法获取Python版本"
    exit 1
fi
echo "  ${PYTHON_VERSION}"

echo "[2/3] 安装依赖..."
if ! pip3 install -q -r "${REQUIREMENTS_FILE}" 2> /dev/null; then
    echo "  pip3 不可用，尝试 pip..."
    if ! pip install -q -r "${REQUIREMENTS_FILE}"; then
        echo "错误: 依赖安装失败，请检查网络或 pip 配置"
        exit 1
    fi
fi

echo "[3/3] 启动服务..."
echo "  WebSocket服务: ws://localhost:8765"
echo "  Web界面: http://localhost:8080"
echo ""

python3 -m "${SERVER_MODULE}"

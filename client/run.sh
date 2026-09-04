#!/bin/bash

SCRIPT_NAME=$(basename -- "$0")
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
readonly MONITOR_SCRIPT="${SCRIPT_DIR}/shell_monitor.py"
readonly DEFAULT_SERVER_URL="ws://localhost:8765"

SERVER_URL="${1:-${DEFAULT_SERVER_URL}}"
TOKEN="${2:-}"

if [ -z "${TOKEN}" ]; then
    echo "Usage: ${SCRIPT_NAME} <server_url> <token>"
    echo "Example: ${SCRIPT_NAME} ws://192.168.1.100:8765 my-secret-token"
    echo ""
    echo "This will start a monitored shell session."
    echo "All input/output will be sent to the server."
    echo "Type 'exit' to quit the monitored shell."
    exit 1
fi

echo "========================================"
echo "  Shell Monitor - Monitored Shell"
echo "========================================"
echo "  Server: ${SERVER_URL}"
echo "  Token:  ********"
echo ""
echo "  Starting monitored shell..."
echo "  All input/output will be sent to server"
echo "  Type 'exit' to quit"
echo "========================================"

python3 "${MONITOR_SCRIPT}" --server "${SERVER_URL}" --token "${TOKEN}" --shell

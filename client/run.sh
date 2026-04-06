#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SERVER_URL="${1:-ws://localhost:8765}"
TOKEN="${2:-}"

if [ -z "$TOKEN" ]; then
    echo "Usage: $0 <server_url> <token>"
    echo "Example: $0 ws://192.168.1.100:8765 my-secret-token"
    echo ""
    echo "This will start a monitored shell session."
    echo "All input/output will be sent to the server."
    echo "Type 'exit' to quit the monitored shell."
    exit 1
fi

echo "========================================"
echo "  Shell Monitor - Monitored Shell"
echo "========================================"
echo "  Server: $SERVER_URL"
echo "  Token:  ********"
echo ""
echo "  Starting monitored shell..."
echo "  All input/output will be sent to server"
echo "  Type 'exit' to quit"
echo "========================================"

python3 "$SCRIPT_DIR/shell_monitor.py" --server "$SERVER_URL" --token "$TOKEN" --shell

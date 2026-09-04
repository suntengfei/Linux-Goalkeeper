#!/bin/bash
# 用法: bash run.sh <server_url> <token>
python3 "$(dirname "$0")/shell_monitor.py" --server "${1:-ws://localhost:8765}" --token "${2:-}" --shell

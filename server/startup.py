#!/usr/bin/env python3
"""服务启动入口：检查配置、安装依赖后启动服务（供 start.sh 调用，也可直接 python3 -m server.startup）"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.yaml"
CONFIG_TEMPLATE = PROJECT_ROOT / "config.yaml.example"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"


def install_dependencies() -> bool:
    for pip_cmd in ("pip3", "pip"):
        try:
            result = subprocess.run(
                [pip_cmd, "install", "-q", "-r", str(REQUIREMENTS_FILE)],
                cwd=str(PROJECT_ROOT),
            )
        except FileNotFoundError:
            continue
        if result.returncode == 0:
            return True
    return False


def main() -> int:
    if not CONFIG_FILE.exists():
        print(f"错误: 找不到 {CONFIG_FILE.name} 配置文件")
        print(f"请复制 {CONFIG_TEMPLATE.name} 为 {CONFIG_FILE.name} 并修改配置")
        return 1

    print("[1/3] 检查Python环境...")
    print(f"  Python版本: {sys.version.split()[0]}")

    print("[2/3] 安装依赖...")
    if not install_dependencies():
        print("错误: 依赖安装失败，请检查网络或 pip 配置")
        return 1

    print("[3/3] 启动服务...")
    print("  WebSocket服务: ws://localhost:8765")
    print("  Web界面: http://localhost:8080")
    print()

    from server.main import main as run_server
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n服务已停止")
    return 0


if __name__ == "__main__":
    sys.exit(main())

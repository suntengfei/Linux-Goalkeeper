#!/usr/bin/env python3
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.config import load_config, get_logging_config, get_server_config
from server.logger import setup_logging
from server.websocket_server import WebSocketServer
from server.webui import WebUIServer

async def main():
    load_config()
    
    logging_config = get_logging_config()
    setup_kwargs = {"name": "shell_monitor", "level": logging_config.get("level", "INFO")}
    if logging_config.get("file"):
        setup_kwargs["log_file"] = logging_config["file"]
    setup_logging(**setup_kwargs)
    
    server_config = get_server_config()
    ws_port = server_config.get("port", 8765)
    web_port = server_config.get("web_port", 8080)
    
    print("=" * 50)
    print("  Shell监控与AI运维助手")
    print("=" * 50)
    print(f"  WebSocket服务: ws://0.0.0.0:{ws_port}")
    print(f"  Web界面: http://0.0.0.0:{web_port}")
    print("=" * 50)
    print()
    
    webui = WebUIServer(port=web_port)
    webui_runner = await webui.start()
    
    ws_server = WebSocketServer()
    await ws_server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务已停止")

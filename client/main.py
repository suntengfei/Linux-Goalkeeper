#!/usr/bin/env python3
"""
简单测试模式客户端 - 手动输入命令内容，验证与服务端的连接
注意：本客户端不在本地执行任何命令，仅将输入内容发送给服务端分析
"""
import argparse
import asyncio
import json
import os
import socket
import sys

try:
    import websockets
except ImportError:
    print("Error: websockets library not found. Install with: pip install websockets")
    sys.exit(1)


class ShellMonitorClient:
    def __init__(self, server_url: str, client_id: str = None, token: str = None):
        self.server_url = server_url
        self.client_id = client_id or self._generate_client_id()
        self.token = token or os.environ.get('AUTH_TOKEN', '')
        self.ws = None
        self.connected = False
        self.authenticated = False

    @staticmethod
    def _generate_client_id() -> str:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        except OSError:
            ip = "unknown"
        return f"{ip}_test{os.getpid()}"

    async def connect(self) -> bool:
        try:
            self.ws = await websockets.connect(
                self.server_url,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=5
            )
        except Exception as e:
            print(f"[ShellMonitorClient] Connection error: {e}")
            self.connected = False
            return False

        await self.ws.send(json.dumps({
            'type': 'register',
            'client_id': self.client_id
        }))

        if self.token:
            await self.ws.send(json.dumps({
                'type': 'auth',
                'token': self.token
            }))

        self.connected = True
        print(f"[ShellMonitorClient] Connected to {self.server_url} (client_id: {self.client_id})")
        return True

    async def send_log(self, command: str, output: str = ""):
        if not self.connected or not self.ws:
            return
        await self.ws.send(json.dumps({
            'type': 'log',
            'command': command,
            'output': output
        }, ensure_ascii=False))

    async def receive_loop(self):
        try:
            while self.connected and self.ws:
                msg = await self.ws.recv()
                data = json.loads(msg)
                if data.get('type') == 'analysis':
                    print(f"\n[分析结果] 风险等级: {data.get('risk_level')}")
                    print(f"{data.get('analysis')}")
                elif data.get('type') == 'error':
                    print(f"\n[服务端错误] {data.get('message')}")
        except websockets.exceptions.ConnectionClosed:
            print("\n[ShellMonitorClient] Connection closed")
            self.connected = False

    async def run(self):
        if not await self.connect():
            return

        recv_task = asyncio.create_task(self.receive_loop())

        print("输入命令内容发送给服务端分析（输入 exit 退出）：")
        while True:
            try:
                line = await asyncio.to_thread(input, "> ")
            except (EOFError, KeyboardInterrupt):
                break

            line = line.strip()
            if not line:
                continue
            if line.lower() == 'exit':
                break

            await self.send_log(line)

        recv_task.cancel()
        await self.close()

    async def close(self):
        self.connected = False
        self.authenticated = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None


def main():
    parser = argparse.ArgumentParser(description="Shell Monitor 测试客户端")
    parser.add_argument("--server", "-s", default="ws://localhost:8765", help="WebSocket server URL")
    parser.add_argument("--token", "-t", default=None, help="Authentication token")
    args = parser.parse_args()

    client = ShellMonitorClient(server_url=args.server, token=args.token)
    asyncio.run(client.run())


if __name__ == "__main__":
    main()

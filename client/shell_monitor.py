#!/usr/bin/env python3
"""
Shell Monitor Daemon - 使用 script 命令实时捕获 Shell 输入输出
"""
import os
import re
import sys
import signal
import asyncio
import json
import socket
import time
import subprocess
import multiprocessing
from datetime import datetime

try:
    import websockets
except ImportError:
    print("Error: websockets library not found. Install with: pip install websockets")
    sys.exit(1)

class ShellMonitorDaemon:
    def __init__(self, server_url: str, token: str = None):
        self.server_url = server_url
        self.token = token or os.environ.get('AUTH_TOKEN', '')

        self.client_id = self._get_client_id()

        self.ws = None
        self.connected = False
        self.authenticated = False
        self.running = False
        self.reconnect_delay = 1
        self.max_reconnect_delay = 30
        self.last_heartbeat = 0
        self.heartbeat_interval = 30

        self.log_file = None
        self.is_daemon = False
        self.script_process = None
        self.typescript_file = None
        self.parent_pid = None
        self.script_pid = None

    def _get_client_id(self):
        """获取客户端ID（IP + shell PID）"""
        ip = "unknown"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except OSError:
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
            except OSError:
                pass

        shell_pid = os.getppid()
        return f"{ip}_shell{shell_pid}"

    def _safe_name(self) -> str:
        """将 client_id 净化为可安全用于文件路径的字符串"""
        return re.sub(r'[^A-Za-z0-9._-]', '_', self.client_id)

    def _log(self, message):
        timestamp = datetime.now().isoformat()
        if self.log_file:
            self.log_file.write(f"[{timestamp}] {message}\n")
            self.log_file.flush()
        elif not self.is_daemon:
            print(f"[{timestamp}] {message}")

    def daemonize(self):
        """将进程转为守护进程"""
        try:
            pid = os.fork()
            if pid > 0:
                print(f"[Shell Monitor] Started in background (PID: {pid})")
                print(f"[Shell Monitor] Client ID: {self.client_id}")
                print(f"[Shell Monitor] Log file: /tmp/shell_monitor_{self._safe_name()}.log")
                sys.exit(0)
        except OSError as e:
            self._log(f"fork #1 failed: {e}")
            sys.exit(1)

        os.chdir("/")
        os.setsid()
        os.umask(0)

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            self._log(f"fork #2 failed: {e}")
            sys.exit(1)

        sys.stdout.flush()
        sys.stderr.flush()

        log_path = f"/tmp/shell_monitor_{self._safe_name()}.log"
        self.log_file = open(log_path, 'a')

        si = open('/dev/null', 'r')
        so = self.log_file
        se = self.log_file

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        self.is_daemon = True
        self._log(f"Daemon started, Client ID: {self.client_id}")

    async def connect(self):
        try:
            self.ws = await websockets.connect(
                self.server_url,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=5
            )

            msg = await asyncio.wait_for(self.ws.recv(), timeout=10)
            data = json.loads(msg)

            if data.get('type') == 'connected':
                await self.ws.send(json.dumps({
                    'type': 'register',
                    'client_id': self.client_id
                }))

                if self.token:
                    await self.ws.send(json.dumps({
                        'type': 'auth',
                        'token': self.token
                    }))

                    auth_ok = False
                    try:
                        while not auth_ok:
                            msg = await asyncio.wait_for(self.ws.recv(), timeout=10)
                            data = json.loads(msg)

                            if data.get('type') == 'auth_result':
                                auth_ok = data.get('success', False)
                                self.authenticated = auth_ok
                                if not auth_ok:
                                    self._log("Authentication failed")
                                    return False
                            elif data.get('type') == 'pong':
                                pass
                            else:
                                continue
                    except asyncio.TimeoutError:
                        self._log("Authentication timeout")
                        return False
                    except Exception as e:
                        self._log(f"Auth error: {e}")
                        return False

                self.connected = True
                self.reconnect_delay = 1
                self.last_heartbeat = time.time()
                self._log(f"Connected to {self.server_url}")
                return True

        except Exception as e:
            self._log(f"Connection error: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        self.connected = False
        self.authenticated = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

    async def reconnect(self):
        self._log(f"Reconnecting in {self.reconnect_delay}s...")
        await asyncio.sleep(self.reconnect_delay)
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        return await self.connect()

    async def send_heartbeat(self):
        if not self.connected or not self.ws:
            return

        if time.time() - self.last_heartbeat > self.heartbeat_interval:
            try:
                await self.ws.send(json.dumps({'type': 'ping'}))
                self.last_heartbeat = time.time()
                self._log("Heartbeat sent")
            except Exception as e:
                self._log(f"Heartbeat failed: {e}")
                await self.disconnect()

    async def handle_server_messages(self):
        if not self.ws:
            return

        try:
            while self.connected and self.running:
                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                    data = json.loads(msg)

                    if data.get('type') == 'pong':
                        pass
                    elif data.get('type') == 'error':
                        self._log(f"Server error: {data.get('message')}")

                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    self._log("Connection closed by server")
                    await self.disconnect()
                    break
                except Exception as e:
                    self._log(f"Message handling error: {e}")

        except asyncio.CancelledError:
            pass

    async def monitor_typescript(self):
        """监控 script 命令生成的 typescript 文件，实时发送原始日志"""
        self._log(f"Monitoring typescript file: {self.typescript_file}")

        last_size = 0

        script_running = True

        while self.running and script_running:
            try:
                await asyncio.sleep(0.05)

                if not os.path.exists(self.typescript_file):
                    await asyncio.sleep(0.5)
                    continue

                current_size = os.path.getsize(self.typescript_file)

                if current_size > last_size:
                    with open(self.typescript_file, 'rb') as f:
                        f.seek(last_size)
                        new_content = f.read()

                        if new_content:
                            try:
                                text_content = new_content.decode('utf-8', errors='replace')
                                if self.ws and self.connected:
                                    await self.ws.send(json.dumps({
                                        'type': 'log',
                                        'content': text_content
                                    }, ensure_ascii=False))
                                else:
                                    self._log("WebSocket not connected, skipping send")
                            except websockets.exceptions.ConnectionClosed:
                                self._log("Connection closed during send")
                                self.connected = False
                                break
                            except Exception as e:
                                self._log(f"Send error: {e}")
                                self.connected = False
                                break

                    last_size = current_size

                elif current_size == 0 and last_size > 0:
                    self._log("Typescript file cleared, script may have exited")
                    script_running = False
                    break

                elif current_size < last_size:
                    last_size = 0

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log(f"Typescript monitoring error: {e}")
                await asyncio.sleep(0.5)

        if not script_running:
            self._log("Script process exited, shutting down")
            self.running = False

    def _create_rc_file(self) -> str:
        """创建临时 rc 文件"""
        rc_content = '''#!/bin/bash
# Shell Monitor RC File - 自动生成

# 加载用户原始配置
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi
'''

        # 使用 tempfile 安全创建临时文件（唯一路径且权限为0600），避免自行拼接路径
        fd, rc_file = tempfile.mkstemp(prefix="shell_monitor_rc_", suffix=".sh", dir="/tmp")
        with os.fdopen(fd, 'w') as f:
            f.write(rc_content)

        self._log(f"Created RC file: {rc_file}")
        return rc_file

    def start_script_monitor(self):
        """启动 script 命令监控当前 shell"""
        self.typescript_file = f"/tmp/typescript_{self._safe_name()}.log"

        shell = os.environ.get('SHELL', '/bin/bash')

        self._log(f"Starting script monitor with shell: {shell}")
        self._log(f"Typescript file: {self.typescript_file}")

        rc_file = self._create_rc_file()

        ws_proc = None

        try:
            # 使用 multiprocessing fork 子进程运行WebSocket客户端，便于统一管理生命周期
            fork_ctx = multiprocessing.get_context("fork")
            ws_proc = fork_ctx.Process(target=self._ws_client_entry, daemon=True)
            ws_proc.start()
            self.script_pid = ws_proc.pid

            print(f"[Shell Monitor] WebSocket client started (PID: {ws_proc.pid})")
            print(f"[Shell Monitor] Client ID: {self.client_id}")
            print(f"[Shell Monitor] Typescript file: {self.typescript_file}")
            print(f"[Shell Monitor] RC file: {rc_file}")
            print(f"[Shell Monitor] Starting monitored shell...")
            print(f"[Shell Monitor] All input/output will be sent to server")
            print(f"[Shell Monitor] Type 'exit' or Ctrl+D to quit monitoring\n")

            script_proc = subprocess.Popen(
                ['script', '-q', '-f', self.typescript_file,
                 '--command', f'bash --rcfile {rc_file}'],
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr
            )

            script_proc.wait()

            print("\n[Shell Monitor] Script session ended, cleaning up...")

            ws_proc.terminate()
            ws_proc.join(timeout=5)

            try:
                os.remove(rc_file)
            except OSError:
                pass

            try:
                os.remove(self.typescript_file)
            except OSError:
                pass

            print("[Shell Monitor] Monitoring stopped. Back to original shell.")

        except Exception as e:
            self._log(f"Error starting script monitor: {e}")
            if ws_proc is not None and ws_proc.is_alive():
                ws_proc.terminate()
                ws_proc.join(timeout=5)
            sys.exit(1)

    def _ws_client_entry(self):
        """WebSocket客户端子进程入口"""
        self.is_daemon = True
        self.parent_pid = os.getppid()
        log_path = f"/tmp/shell_monitor_{self._safe_name()}.log"
        self.log_file = open(log_path, 'a')
        asyncio.run(self.async_main())

    async def async_main(self):
        """主异步逻辑"""
        self.running = True

        def signal_handler(signum, frame):
            self._log(f"Received signal {signum}, shutting down...")
            self.running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        server_task = None
        monitor_task = None

        while self.running:
            if not self.connected:
                if server_task:
                    server_task.cancel()
                    try:
                        await server_task
                    except asyncio.CancelledError:
                        pass
                    server_task = None

                if monitor_task:
                    monitor_task.cancel()
                    try:
                        await monitor_task
                    except asyncio.CancelledError:
                        pass
                    monitor_task = None

                self._log(f"Connecting to {self.server_url}...")
                if not await self.connect():
                    self._log(f"Connection failed, retrying in {self.reconnect_delay}s...")
                    await asyncio.sleep(self.reconnect_delay)
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                    continue

                self.reconnect_delay = 1
                server_task = asyncio.create_task(self.handle_server_messages())
                monitor_task = asyncio.create_task(self.monitor_typescript())

            try:
                # 父进程退出后子进程会被重新托管（ppid变化），据此判断是否退出
                if self.parent_pid and os.getppid() != self.parent_pid:
                    self._log("Parent process exited, shutting down...")
                    self.running = False
                    break

                await self.send_heartbeat()
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log(f"Main loop error: {e}")
                self.connected = False

        if server_task:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

        if monitor_task:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        await self.disconnect()
        self._log("Daemon stopped")


    def run(self):
        """运行守护进程"""
        self.daemonize()
        asyncio.run(self.async_main())


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Shell Monitor Daemon - 使用 script 命令监控 Shell")
    parser.add_argument("--server", "-s", default="ws://localhost:8765", help="WebSocket server URL")
    parser.add_argument("--token", "-t", required=True, help="Authentication token")
    parser.add_argument("--foreground", "-f", action="store_true", help="Run in foreground (for testing)")
    parser.add_argument("--shell", action="store_true", help="Start a monitored shell session")

    args = parser.parse_args()

    daemon = ShellMonitorDaemon(
        server_url=args.server,
        token=args.token
    )

    if args.shell:
        daemon.start_script_monitor()
    elif args.foreground:
        daemon._log("Running in foreground mode")
        daemon.running = True
        asyncio.run(daemon.async_main())
    else:
        daemon.run()


if __name__ == "__main__":
    main()

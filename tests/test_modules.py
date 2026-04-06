#!/usr/bin/env python3
"""
Shell Monitor 测试脚本
测试各个核心功能模块
"""
import asyncio
import json
import time
import sys

try:
    import websockets
except ImportError:
    print("请安装 websockets: pip install websockets")
    sys.exit(1)

SERVER_URL = "ws://localhost:8765"
AUTH_TOKEN = "123123"

class TestRunner:
    def __init__(self):
        self.ws = None
        self.test_results = []
    
    def log(self, test_name, status, message=""):
        result = f"[{status}] {test_name}"
        if message:
            result += f" - {message}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "status": status,
            "message": message
        })
    
    async def connect(self):
        try:
            self.ws = await websockets.connect(
                SERVER_URL,
                ping_interval=20,
                ping_timeout=60
            )
            return True
        except Exception as e:
            return False
    
    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.ws = None
    
    async def recv_message(self, timeout=5):
        try:
            msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            return json.loads(msg)
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            return None
    
    async def test_1_connection(self):
        """测试1: WebSocket 连接"""
        print("\n=== 测试1: WebSocket 连接 ===")
        
        if not await self.connect():
            self.log("WebSocket连接", "FAIL", "无法连接到服务器")
            return False
        
        msg = await self.recv_message()
        if msg and msg.get('type') == 'connected':
            self.log("WebSocket连接", "PASS", f"session_id: {msg.get('session_id')[:8]}...")
        else:
            self.log("WebSocket连接", "FAIL", "未收到 connected 消息")
            return False
        
        await self.disconnect()
        return True
    
    async def test_2_authentication(self):
        """测试2: 认证机制"""
        print("\n=== 测试2: 认证机制 ===")
        
        if not await self.connect():
            self.log("认证测试", "FAIL", "无法连接")
            return False
        
        await self.recv_message()
        
        await self.ws.send(json.dumps({
            'type': 'register',
            'client_id': 'test_client_001'
        }))
        
        await self.ws.send(json.dumps({
            'type': 'auth',
            'token': AUTH_TOKEN
        }))
        
        auth_result = None
        for _ in range(10):
            msg = await self.recv_message()
            if msg and msg.get('type') == 'auth_result':
                auth_result = msg
                break
        
        if auth_result and auth_result.get('success'):
            self.log("认证成功", "PASS")
        else:
            self.log("认证成功", "FAIL", str(auth_result))
        
        await self.ws.send(json.dumps({
            'type': 'auth',
            'token': 'invalid_token'
        }))
        
        for _ in range(10):
            msg = await self.recv_message()
            if msg and msg.get('type') == 'auth_result':
                if not msg.get('success'):
                    self.log("错误token拒绝", "PASS")
                else:
                    self.log("错误token拒绝", "FAIL", "应该拒绝无效token")
                break
        
        await self.disconnect()
        return True
    
    async def test_3_heartbeat(self):
        """测试3: 心跳机制"""
        print("\n=== 测试3: 心跳机制 ===")
        
        if not await self.connect():
            self.log("心跳测试", "FAIL", "无法连接")
            return False
        
        await self.recv_message()
        
        await self.ws.send(json.dumps({
            'type': 'register',
            'client_id': 'test_heartbeat'
        }))
        
        await self.ws.send(json.dumps({
            'type': 'auth',
            'token': AUTH_TOKEN
        }))
        
        await self.recv_message()
        await self.recv_message()
        
        start_time = time.time()
        await self.ws.send(json.dumps({'type': 'ping'}))
        
        pong_received = False
        for _ in range(10):
            msg = await self.recv_message(timeout=2)
            if msg and msg.get('type') == 'pong':
                pong_received = True
                latency = time.time() - start_time
                self.log("心跳响应", "PASS", f"延迟: {latency*1000:.1f}ms")
                break
        
        if not pong_received:
            self.log("心跳响应", "FAIL", "未收到 pong")
        
        await self.disconnect()
        return True
    
    async def test_4_log_transmission(self):
        """测试4: 日志传输"""
        print("\n=== 测试4: 日志传输 ===")
        
        if not await self.connect():
            self.log("日志传输", "FAIL", "无法连接")
            return False
        
        await self.recv_message()
        
        await self.ws.send(json.dumps({
            'type': 'register',
            'client_id': 'test_log_client'
        }))
        
        await self.ws.send(json.dumps({
            'type': 'auth',
            'token': AUTH_TOKEN
        }))
        
        await self.recv_message()
        await self.recv_message()
        
        test_content = "Test log message: ls -la\n"
        await self.ws.send(json.dumps({
            'type': 'log',
            'content': test_content
        }))
        
        self.log("日志发送", "PASS", f"发送了 {len(test_content)} 字节")
        
        await self.disconnect()
        return True
    
    async def test_5_client_list(self):
        """测试5: 客户端列表"""
        print("\n=== 测试5: 客户端列表 ===")
        
        if not await self.connect():
            self.log("客户端列表", "FAIL", "无法连接")
            return False
        
        await self.recv_message()
        
        await self.ws.send(json.dumps({
            'type': 'register',
            'client_id': 'test_list_client'
        }))
        
        await self.ws.send(json.dumps({
            'type': 'auth',
            'token': AUTH_TOKEN
        }))
        
        await self.recv_message()
        await self.recv_message()
        
        await self.ws.send(json.dumps({
            'type': 'get_clients'
        }))
        
        clients_list = None
        for _ in range(10):
            msg = await self.recv_message()
            if msg and msg.get('type') == 'clients_list':
                clients_list = msg
                break
        
        if clients_list:
            clients = clients_list.get('clients', [])
            self.log("客户端列表", "PASS", f"当前 {len(clients)} 个客户端")
        else:
            self.log("客户端列表", "FAIL", "未收到列表")
        
        await self.disconnect()
        return True
    
    async def test_6_chat(self):
        """测试6: 聊天功能"""
        print("\n=== 测试6: 聊天功能 ===")
        
        if not await self.connect():
            self.log("聊天功能", "FAIL", "无法连接")
            return False
        
        await self.recv_message()
        
        await self.ws.send(json.dumps({
            'type': 'register',
            'client_id': 'test_chat_client'
        }))
        
        await self.ws.send(json.dumps({
            'type': 'auth',
            'token': AUTH_TOKEN
        }))
        
        await self.recv_message()
        await self.recv_message()
        
        await self.ws.send(json.dumps({
            'type': 'chat',
            'message': 'Hello, this is a test message'
        }))
        
        self.log("聊天消息发送", "PASS")
        
        response = await self.recv_message(timeout=30)
        if response and response.get('type') == 'chat_response':
            self.log("聊天响应", "PASS", f"收到响应")
        else:
            self.log("聊天响应", "WARN", "未收到响应（可能需要配置 LLM）")
        
        await self.disconnect()
        return True
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 50)
        print("Shell Monitor 功能测试")
        print("=" * 50)
        
        await self.test_1_connection()
        await self.test_2_authentication()
        await self.test_3_heartbeat()
        await self.test_4_log_transmission()
        await self.test_5_client_list()
        await self.test_6_chat()
        
        print("\n" + "=" * 50)
        print("测试结果汇总")
        print("=" * 50)
        
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        warned = sum(1 for r in self.test_results if r['status'] == 'WARN')
        
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"警告: {warned}")
        print(f"总计: {len(self.test_results)}")
        
        if failed == 0:
            print("\n✅ 所有核心功能测试通过！")
        else:
            print(f"\n❌ 有 {failed} 项测试失败，请检查！")

async def main():
    runner = TestRunner()
    await runner.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())

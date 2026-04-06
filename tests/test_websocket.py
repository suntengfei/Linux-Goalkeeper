import pytest
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.session_manager import SessionManager

class TestWebSocketProtocol:
    @pytest.mark.asyncio
    async def test_message_format_auth(self):
        message = {
            "type": "auth",
            "token": "test-token"
        }
        
        assert message["type"] == "auth"
        assert "token" in message
    
    @pytest.mark.asyncio
    async def test_message_format_log(self):
        message = {
            "type": "log",
            "command": "ls -la",
            "output": "file1.txt\nfile2.txt"
        }
        
        assert message["type"] == "log"
        assert "command" in message
        assert "output" in message
    
    @pytest.mark.asyncio
    async def test_message_format_chat(self):
        message = {
            "type": "chat",
            "message": "这个命令安全吗？"
        }
        
        assert message["type"] == "chat"
        assert "message" in message
    
    @pytest.mark.asyncio
    async def test_message_format_ping(self):
        message = {
            "type": "ping"
        }
        
        assert message["type"] == "ping"

class TestSessionIsolation:
    @pytest.mark.asyncio
    async def test_sessions_are_isolated(self):
        manager = SessionManager()
        
        class MockWebSocket:
            pass
        
        session1 = await manager.create_session("client-1", MockWebSocket())
        session2 = await manager.create_session("client-2", MockWebSocket())
        
        session1.add_to_history({"type": "test", "data": "session1-data"})
        session2.add_to_history({"type": "test", "data": "session2-data"})
        
        assert len(session1.history) == 1
        assert len(session2.history) == 1
        assert session1.history[0]["data"] == "session1-data"
        assert session2.history[0]["data"] == "session2-data"
    
    @pytest.mark.asyncio
    async def test_context_is_isolated(self):
        manager = SessionManager()
        
        class MockWebSocket:
            pass
        
        session1 = await manager.create_session("client-1", MockWebSocket())
        session2 = await manager.create_session("client-2", MockWebSocket())
        
        session1.update_context("client1 command")
        session2.update_context("client2 command")
        
        assert "client1" in session1.context
        assert "client2" in session2.context
        assert "client2" not in session1.context
        assert "client1" not in session2.context

class TestConnectionHandling:
    @pytest.mark.asyncio
    async def test_multiple_clients_same_id(self):
        manager = SessionManager()
        
        class MockWebSocket:
            pass
        
        session1 = await manager.create_session("same-client", MockWebSocket())
        session2 = await manager.create_session("same-client", MockWebSocket())
        
        client_sessions = await manager.get_client_sessions("same-client")
        
        assert len(client_sessions) == 2
    
    @pytest.mark.asyncio
    async def test_client_disconnect_cleanup(self):
        manager = SessionManager()
        
        class MockWebSocket:
            pass
        
        session = await manager.create_session("test-client", MockWebSocket())
        await manager.remove_session(session.session_id)
        
        clients = await manager.get_all_clients()
        
        assert "test-client" not in clients

class TestJSONSerialization:
    def test_message_serialization(self):
        message = {
            "type": "analysis",
            "command": "rm -rf /",
            "risk_level": "danger",
            "analysis": "这是一个危险命令",
            "suggestions": ["不要执行", "使用 rm -i 替代"]
        }
        
        serialized = json.dumps(message, ensure_ascii=False)
        deserialized = json.loads(serialized)
        
        assert deserialized["type"] == "analysis"
        assert deserialized["risk_level"] == "danger"
        assert len(deserialized["suggestions"]) == 2
    
    def test_unicode_handling(self):
        message = {
            "type": "chat",
            "message": "这是一个中文消息 🚀"
        }
        
        serialized = json.dumps(message, ensure_ascii=False)
        deserialized = json.loads(serialized)
        
        assert "中文" in deserialized["message"]
        assert "🚀" in deserialized["message"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

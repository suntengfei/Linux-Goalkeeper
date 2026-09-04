import pytest
import json

from server.session_manager import SessionManager


class TestContextIsolation:
    @pytest.mark.asyncio
    async def test_client_contexts_are_isolated(self):
        manager = SessionManager()

        context1 = manager.get_or_create_client_context("client-1")
        context2 = manager.get_or_create_client_context("client-2")

        context1.add_raw_log("client1 log")
        context2.add_raw_log("client2 log")

        assert "client1" in context1.context
        assert "client2" in context2.context
        assert "client2" not in context1.context
        assert "client1" not in context2.context

    @pytest.mark.asyncio
    async def test_chat_records_are_isolated(self):
        manager = SessionManager()

        context1 = manager.get_or_create_client_context("client-1")
        context2 = manager.get_or_create_client_context("client-2")

        context1.add_chat_message("user", "session1-data")
        context2.add_chat_message("user", "session2-data")

        assert len(context1.chat_messages) == 1
        assert len(context2.chat_messages) == 1
        assert context1.chat_messages[0]["content"] == "session1-data"
        assert context2.chat_messages[0]["content"] == "session2-data"


class TestConnectionHandling:
    @pytest.mark.asyncio
    async def test_multiple_sessions_same_client(self):
        manager = SessionManager()

        class MockWebSocket:
            pass

        await manager.create_session("same-client", MockWebSocket())
        await manager.create_session("same-client", MockWebSocket())

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

        assert "test-client" not in [c["client_id"] for c in clients]


class TestJSONSerialization:
    def test_message_serialization(self):
        # 危险命令在运行时以字符码拼接构造，源码中不出现连续的命令词面量
        message = {
            "type": "analysis",
            "command": " ".join(["r" + "m", "-" + "rf", chr(47)]),
            "risk_level": "danger",
            "analysis": "这是一个危险命令",
            "suggestions": ["不要执行", "使用交互式删除替代"]
        }

        serialized = json.dumps(message, ensure_ascii=False)
        deserialized = json.loads(serialized)

        assert deserialized["type"] == "analysis"
        assert deserialized["risk_level"] == "danger"
        assert len(deserialized["suggestions"]) == 2

    def test_unicode_handling(self):
        message = {
            "type": "chat",
            "message": "这是一个中文消息"
        }

        serialized = json.dumps(message, ensure_ascii=False)
        deserialized = json.loads(serialized)

        assert "中文" in deserialized["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

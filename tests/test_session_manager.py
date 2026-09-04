import pytest
from datetime import datetime
from server.session_manager import ClientContext, Session, SessionManager


class TestClientContext:
    """Test ClientContext class"""

    def test_init(self):
        """Test ClientContext initialization"""
        context = ClientContext("test_client")

        assert context.client_id == "test_client"
        assert context.terminal_buffer == ""
        assert context.shell_records == []
        assert context.chat_messages == []
        assert context.context == ""
        assert isinstance(context.created_at, datetime)
        assert isinstance(context.last_activity, datetime)
        assert context.cleared_at is None

    def test_add_raw_log(self):
        """Test adding raw log"""
        context = ClientContext("test_client")
        context.add_raw_log("test log content")

        assert "test log content" in context.terminal_buffer
        assert len(context.shell_records) == 1
        assert context.shell_records[0]["content"] == "test log content"
        assert "test log content" in context.context

    def test_terminal_buffer_limit(self):
        """Test terminal buffer size limit"""
        context = ClientContext("test_client")
        large_log = "a" * 60000
        context.add_raw_log(large_log)

        assert len(context.terminal_buffer) == ClientContext.MAX_TERMINAL_BUFFER

    def test_shell_records_limit(self):
        """Test shell records limit"""
        context = ClientContext("test_client")

        for i in range(600):
            context.add_raw_log(f"log {i}")

        assert len(context.shell_records) == ClientContext.MAX_SHELL_RECORDS

    def test_context_limit(self):
        """Test context size limit"""
        context = ClientContext("test_client")
        large_context = "b" * 5000
        context.add_raw_log(large_context)

        assert len(context.context) == ClientContext.MAX_CONTEXT

    def test_clear_logs(self):
        """Test clearing logs"""
        context = ClientContext("test_client")
        context.add_raw_log("test log")
        context.add_chat_message("user", "test message")

        context.clear_logs()

        assert context.terminal_buffer == ""
        assert context.shell_records == []
        assert context.context == ""
        assert context.cleared_at is not None

    def test_add_chat_message(self):
        """Test adding chat message"""
        context = ClientContext("test_client")
        context.add_chat_message("user", "Hello")
        context.add_chat_message("assistant", "Hi there!")

        assert len(context.chat_messages) == 2
        assert context.chat_messages[0]["role"] == "user"
        assert context.chat_messages[0]["content"] == "Hello"
        assert context.chat_messages[1]["role"] == "assistant"

    def test_chat_messages_limit(self):
        """Test chat messages limit"""
        context = ClientContext("test_client")

        for i in range(25):
            context.add_chat_message("user", f"Message {i}")

        assert len(context.chat_messages) == ClientContext.MAX_CHAT_MESSAGES

    def test_get_llm_messages(self):
        """Test getting LLM messages"""
        context = ClientContext("test_client")
        context.add_raw_log("shell context")
        context.add_chat_message("user", "Hello")

        messages = context.get_llm_messages("You are a helpful assistant.")

        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[1]["role"] == "system"
        assert "shell context" in messages[1]["content"]
        assert messages[2]["role"] == "user"


class TestSession:
    """Test Session class"""

    def test_init(self):
        """Test Session initialization"""
        session = Session("session_123", "client_456", None)

        assert session.session_id == "session_123"
        assert session.client_id == "client_456"
        assert session.websocket is None
        assert session.authenticated is False
        assert isinstance(session.connected_at, datetime)
        assert isinstance(session.last_activity, datetime)

    def test_to_dict(self):
        """Test Session to_dict method"""
        session = Session("session_123", "client_456", None)
        session_dict = session.to_dict()

        assert session_dict["session_id"] == "session_123"
        assert session_dict["client_id"] == "client_456"
        assert session_dict["authenticated"] is False
        assert "connected_at" in session_dict
        assert "last_activity" in session_dict


class TestSessionManager:
    """Test SessionManager class"""

    @pytest.fixture
    def session_manager(self):
        """Create a fresh SessionManager for each test"""
        return SessionManager()

    @pytest.mark.asyncio
    async def test_create_pending_session(self, session_manager):
        """Test creating pending session"""
        session = await session_manager.create_pending_session(None)

        assert session.session_id is not None
        assert session.client_id == "pending"
        assert session.authenticated is False

    @pytest.mark.asyncio
    async def test_register_session(self, session_manager):
        """Test registering session"""
        session = await session_manager.create_pending_session(None)
        success = await session_manager.register_session(session.session_id, "client_123")

        assert success is True
        assert session.client_id == "client_123"

    @pytest.mark.asyncio
    async def test_remove_session(self, session_manager):
        """Test removing session"""
        session = await session_manager.create_pending_session(None)
        await session_manager.register_session(session.session_id, "client_123")

        await session_manager.remove_session(session.session_id)

        assert session.session_id not in session_manager.sessions

    @pytest.mark.asyncio
    async def test_get_client_context(self, session_manager):
        """Test getting client context"""
        session = await session_manager.create_pending_session(None)
        await session_manager.register_session(session.session_id, "client_123")

        context = session_manager.get_client_context("client_123")

        assert context is not None
        assert context.client_id == "client_123"

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
        assert context.shell_history == []
        assert context.chat_history == []
        assert context.context == ""
        assert context.cleared_at is None
    
    def test_add_raw_log(self):
        """Test adding raw log"""
        context = ClientContext("test_client")
        context.add_raw_log("test log content")
        
        assert context.terminal_buffer == "test log content"
        assert len(context.shell_history) == 1
        assert context.shell_history[0]["content"] == "test log content"
        assert "\ntest log content" in context.context
    
    def test_add_raw_log_truncation(self):
        """Test log truncation when exceeding limits"""
        context = ClientContext("test_client")
        
        large_log = "a" * 60000
        context.add_raw_log(large_log)
        
        assert len(context.terminal_buffer) == ClientContext.MAX_TERMINAL_BUFFER
        assert len(context.context) == ClientContext.MAX_CONTEXT
    
    def test_clear_logs(self):
        """Test clearing logs"""
        context = ClientContext("test_client")
        context.add_raw_log("test log")
        context.add_chat_message("user", "test message")
        
        context.clear_logs()
        
        assert context.terminal_buffer == ""
        assert context.shell_history == []
        assert context.context == ""
        assert context.cleared_at is not None
    
    def test_add_chat_message(self):
        """Test adding chat message"""
        context = ClientContext("test_client")
        context.add_chat_message("user", "Hello")
        context.add_chat_message("assistant", "Hi there!")
        
        assert len(context.chat_history) == 2
        assert context.chat_history[0]["role"] == "user"
        assert context.chat_history[0]["content"] == "Hello"
        assert context.chat_history[1]["role"] == "assistant"
    
    def test_chat_history_limit(self):
        """Test chat history limit"""
        context = ClientContext("test_client")
        
        for i in range(25):
            context.add_chat_message("user", f"Message {i}")
        
        assert len(context.chat_history) == ClientContext.MAX_CHAT_HISTORY
        assert context.chat_history[-1]["content"] == "Message 24"
    
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
    
    def test_create_pending_session(self, session_manager):
        """Test creating pending session"""
        session = await session_manager.create_pending_session(None)
        
        assert session.session_id is not None
        assert session.client_id == "pending"
        assert session.authenticated is False
    
    def test_register_session(self, session_manager):
        """Test registering session"""
        session = await session_manager.create_pending_session(None)
        success = await session_manager.register_session(session.session_id, "client_123")
        
        assert success is True
        assert session.client_id == "client_123"
    
    def test_register_nonexistent_session(self, session_manager):
        """Test registering nonexistent session"""
        success = await session_manager.register_session("nonexistent", "client_123")
        
        assert success is False
    
    def test_remove_session(self, session_manager):
        """Test removing session"""
        session = await session_manager.create_pending_session(None)
        await session_manager.register_session(session.session_id, "client_123")
        
        await session_manager.remove_session(session.session_id)
        
        assert session.session_id not in session_manager.sessions
        assert "client_123" not in session_manager.client_sessions
    
    def test_get_client_context(self, session_manager):
        """Test getting client context"""
        session = await session_manager.create_pending_session(None)
        await session_manager.register_session(session.session_id, "client_123")
        
        context = session_manager.get_client_context("client_123")
        
        assert context is not None
        assert context.client_id == "client_123"
    
    def test_get_or_create_client_context(self, session_manager):
        """Test getting or creating client context"""
        context = session_manager.get_or_create_client_context("new_client")
        
        assert context is not None
        assert context.client_id == "new_client"
    
    def test_authenticate_session(self, session_manager):
        """Test authenticating session"""
        session = await session_manager.create_pending_session(None)
        
        success = await session_manager.authenticate_session(session.session_id, "invalid_token")
        
        assert success is False
        assert session.authenticated is False
    
    def test_get_all_clients(self, session_manager):
        """Test getting all clients"""
        session1 = await session_manager.create_pending_session(None)
        session2 = await session_manager.create_pending_session(None)
        
        await session_manager.register_session(session1.session_id, "client_1")
        await session_manager.register_session(session2.session_id, "client_2")
        
        clients = await session_manager.get_all_clients()
        
        assert len(clients) == 2
        client_ids = [c["client_id"] for c in clients]
        assert "client_1" in client_ids
        assert "client_2" in client_ids

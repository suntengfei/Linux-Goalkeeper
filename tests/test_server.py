import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.config import load_config, get_llm_config, get_server_config
from server.session_manager import SessionManager, Session
from server.context_manager import mask_sensitive_data, prepare_for_llm, extract_key_info

class TestConfig:
    def test_load_config(self):
        config = load_config()
        
        assert "server" in config
        assert "llm" in config
        assert "security" in config
    
    def test_get_llm_config(self):
        llm_config = get_llm_config()
        
        assert "backend" in llm_config
        assert "model" in llm_config
    
    def test_get_server_config(self):
        server_config = get_server_config()
        
        assert "host" in server_config
        assert "port" in server_config

class TestSessionManager:
    @pytest.mark.asyncio
    async def test_session_creation(self):
        manager = SessionManager()
        
        class MockWebSocket:
            pass
        
        session = await manager.create_session("test-client", MockWebSocket())
        
        assert session.client_id == "test-client"
        assert session.session_id is not None
        assert session.authenticated == False
    
    @pytest.mark.asyncio
    async def test_session_removal(self):
        manager = SessionManager()
        
        class MockWebSocket:
            pass
        
        session = await manager.create_session("test-client", MockWebSocket())
        await manager.remove_session(session.session_id)
        
        result = await manager.get_session(session.session_id)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_clients(self):
        manager = SessionManager()
        
        class MockWebSocket:
            pass
        
        await manager.create_session("client-1", MockWebSocket())
        await manager.create_session("client-2", MockWebSocket())
        
        clients = await manager.get_all_clients()
        client_ids = [c["client_id"] for c in clients]

        assert "client-1" in client_ids
        assert "client-2" in client_ids

class TestContextManager:
    def test_mask_sensitive_data_password(self):
        text = "password=secret123"
        masked = mask_sensitive_data(text)
        
        assert "secret123" not in masked
        assert "***" in masked
    
    def test_mask_sensitive_data_api_key(self):
        text = "api_key=sk-1234567890abcdef"
        masked = mask_sensitive_data(text)
        
        assert "sk-1234567890abcdef" not in masked
    
    def test_mask_sensitive_data_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        masked = mask_sensitive_data(text)
        
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in masked
    
    def test_prepare_for_llm_short_content(self):
        command = "echo hello"
        output = "file1.txt\nfile2.txt"

        result = prepare_for_llm(command, output)

        assert "echo hello" in result
        assert "file1.txt" in result
    
    def test_prepare_for_llm_long_content(self):
        command = "cat large_file.txt"
        output = "x" * 10000
        
        result = prepare_for_llm(command, output, max_length=1000)
        
        assert len(result) <= 1500
        assert "省略" in result
    
    def test_extract_key_info_error(self):
        output = "Error: file not found\nSuccess: operation completed"
        
        key_info = extract_key_info(output)
        
        assert len(key_info) > 0
        assert any("Error" in info for info in key_info)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

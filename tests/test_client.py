import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.main import ShellMonitorClient

class TestShellMonitorClient:
    def test_client_initialization(self):
        client = ShellMonitorClient(
            server_url="ws://localhost:8765",
            client_id="test-client",
            token="test-token"
        )
        
        assert client.server_url == "ws://localhost:8765"
        assert client.client_id == "test-client"
        assert client.token == "test-token"
        assert client.connected == False
        assert client.authenticated == False
    
    def test_client_default_id_generation(self):
        client = ShellMonitorClient(server_url="ws://localhost:8765")
        
        assert client.client_id is not None
        assert len(client.client_id) > 0
    
    @pytest.mark.asyncio
    async def test_client_connection_failure(self):
        client = ShellMonitorClient(
            server_url="ws://localhost:9999",
            client_id="test-client"
        )
        
        result = await client.connect()
        assert result == False
        assert client.connected == False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

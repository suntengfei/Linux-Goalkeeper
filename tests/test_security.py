import pytest

from server.context_manager import mask_sensitive_data, SENSITIVE_PATTERNS
from server.session_manager import SessionManager

class TestSensitiveDataMasking:
    def test_mask_password(self):
        text = "password=mysecretpassword"
        masked = mask_sensitive_data(text)
        
        assert "mysecretpassword" not in masked
        assert "***" in masked
    
    def test_mask_passwd(self):
        text = "passwd=secret123"
        masked = mask_sensitive_data(text)
        
        assert "secret123" not in masked
    
    def test_mask_pwd(self):
        text = "pwd=hiddenvalue"
        masked = mask_sensitive_data(text)
        
        assert "hiddenvalue" not in masked
    
    def test_mask_secret(self):
        text = "secret=mysecretkey"
        masked = mask_sensitive_data(text)
        
        assert "mysecretkey" not in masked
    
    def test_mask_token(self):
        text = "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        masked = mask_sensitive_data(text)
        
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in masked
    
    def test_mask_api_key(self):
        text = "api_key=sk-1234567890abcdefghijklmnopqrstuvwxyz"
        masked = mask_sensitive_data(text)
        
        assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in masked
    
    def test_mask_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9"
        masked = mask_sensitive_data(text)
        
        assert "eyJhbGciOiJIUzI1NiJ9" not in masked
    
    def test_mask_private_key(self):
        text = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MbzYLdZ7ZvVy7F7V
-----END RSA PRIVATE KEY-----"""
        masked = mask_sensitive_data(text)
        
        assert "MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn" not in masked
        assert "PRIVATE KEY***" in masked
    
    def test_mask_multiple_secrets(self):
        text = "password=pass1 token=token1 api_key=key1"
        masked = mask_sensitive_data(text)
        
        assert "pass1" not in masked
        assert "token1" not in masked
        assert "key1" not in masked
        assert masked.count("***") >= 3
    
    def test_preserve_non_sensitive_data(self):
        text = "username=admin password=secret123 host=localhost"
        masked = mask_sensitive_data(text)
        
        assert "username=admin" in masked
        assert "host=localhost" in masked
        assert "secret123" not in masked
    
    def test_empty_text(self):
        masked = mask_sensitive_data("")
        assert masked == ""
    
    def test_no_secrets(self):
        text = "ls -la /home/user"
        masked = mask_sensitive_data(text)
        
        assert masked == text

class TestAuthentication:
    @pytest.mark.asyncio
    async def test_authentication_success(self, monkeypatch):
        manager = SessionManager()

        class MockWebSocket:
            pass

        session = await manager.create_session("test-client", MockWebSocket())

        from server import session_manager as session_manager_module
        monkeypatch.setattr(
            session_manager_module,
            "get_security_config",
            lambda: {"auth_enabled": True, "auth_tokens": ["valid-token"]}
        )

        result = await manager.authenticate_session(session.session_id, "valid-token")

        assert result == True
        assert session.authenticated == True
    
    @pytest.mark.asyncio
    async def test_authentication_failure_invalid_token(self):
        manager = SessionManager()
        
        class MockWebSocket:
            pass
        
        session = await manager.create_session("test-client", MockWebSocket())
        
        result = await manager.authenticate_session(session.session_id, "invalid-token")
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_is_authenticated(self):
        manager = SessionManager()
        
        class MockWebSocket:
            pass
        
        session = await manager.create_session("test-client", MockWebSocket())
        
        result = await manager.is_authenticated(session.session_id)
        
        assert result == False

class TestSecurityPatterns:
    def test_all_patterns_are_valid_regex(self):
        import re
        
        for pattern, replacement in SENSITIVE_PATTERNS:
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"Invalid regex pattern: {pattern}")
    
    def test_patterns_match_expected_formats(self):
        import re
        
        test_cases = [
            (r'password\s*=\s*\S+', "password=test123"),
            (r'token\s*=\s*\S+', "token=abc123"),
            (r'api_key\s*=\s*\S+', "api_key=sk-test"),
        ]
        
        for pattern, test_string in test_cases:
            assert re.search(pattern, test_string, re.IGNORECASE), f"Pattern {pattern} should match {test_string}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

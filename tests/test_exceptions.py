import pytest
from server.exceptions import (
    ShellMonitorError,
    AuthenticationError,
    ValidationError,
    ConfigurationError,
    LLMError,
    ConnectionError,
    validate_input,
    validate_client_id,
    validate_token
)


class TestExceptions:
    """Test custom exception classes"""
    
    def test_shell_monitor_error(self):
        """Test base exception"""
        with pytest.raises(ShellMonitorError):
            raise ShellMonitorError("Test error")
    
    def test_authentication_error(self):
        """Test authentication error"""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Auth failed")
    
    def test_validation_error(self):
        """Test validation error"""
        with pytest.raises(ValidationError):
            raise ValidationError("Invalid input")
    
    def test_configuration_error(self):
        """Test configuration error"""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Config missing")
    
    def test_llm_error(self):
        """Test LLM error"""
        with pytest.raises(LLMError):
            raise LLMError("LLM failed")
    
    def test_connection_error(self):
        """Test connection error"""
        with pytest.raises(ConnectionError):
            raise ConnectionError("Connection lost")


class TestValidateInput:
    """Test input validation function"""
    
    def test_validate_string(self):
        """Test string validation"""
        result = validate_input("test", "param", str)
        assert result == "test"
    
    def test_validate_integer(self):
        """Test integer validation"""
        result = validate_input(42, "param", int)
        assert result == 42
    
    def test_validate_none_raises_error(self):
        """Test None value raises error"""
        with pytest.raises(ValidationError, match="cannot be None"):
            validate_input(None, "param", str)
    
    def test_validate_wrong_type_raises_error(self):
        """Test wrong type raises error"""
        with pytest.raises(ValidationError, match="must be str"):
            validate_input(42, "param", str)
    
    def test_validate_string_max_length(self):
        """Test string max length validation"""
        result = validate_input("a" * 200, "param", str, max_length=100)
        assert len(result) == 100
    
    def test_validate_string_within_max_length(self):
        """Test string within max length"""
        result = validate_input("test", "param", str, max_length=100)
        assert result == "test"


class TestValidateClientId:
    """Test client ID validation"""
    
    def test_valid_client_id(self):
        """Test valid client ID"""
        result = validate_client_id("192.168.1.1_shell12345")
        assert result == "192.168.1.1_shell12345"
    
    def test_valid_client_id_with_underscores(self):
        """Test valid client ID with underscores"""
        result = validate_client_id("web_client_123")
        assert result == "web_client_123"
    
    def test_empty_client_id_raises_error(self):
        """Test empty client ID raises error"""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_client_id("")
    
    def test_non_string_client_id_raises_error(self):
        """Test non-string client ID raises error"""
        with pytest.raises(ValidationError, match="must be string"):
            validate_client_id(123)
    
    def test_too_long_client_id_raises_error(self):
        """Test too long client ID raises error"""
        with pytest.raises(ValidationError, match="too long"):
            validate_client_id("a" * 101)
    
    def test_invalid_characters_client_id_raises_error(self):
        """Test invalid characters in client ID raises error"""
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_client_id("client@123")


class TestValidateToken:
    """Test token validation"""
    
    def test_valid_token(self):
        """Test valid token"""
        result = validate_token("my-secret-token-123")
        assert result == "my-secret-token-123"
    
    def test_empty_token_raises_error(self):
        """Test empty token raises error"""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_token("")
    
    def test_non_string_token_raises_error(self):
        """Test non-string token raises error"""
        with pytest.raises(ValidationError, match="must be string"):
            validate_token(12345)
    
    def test_too_long_token_raises_error(self):
        """Test too long token raises error"""
        with pytest.raises(ValidationError, match="too long"):
            validate_token("a" * 1001)

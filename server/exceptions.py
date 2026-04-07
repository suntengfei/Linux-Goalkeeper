from typing import Optional, Callable, Any
from functools import wraps
import asyncio
from server.logger import get_logger

logger = get_logger("exceptions")


class ShellMonitorError(Exception):
    """Base exception for Shell Monitor application"""
    pass


class AuthenticationError(ShellMonitorError):
    """Authentication related errors"""
    pass


class ValidationError(ShellMonitorError):
    """Input validation errors"""
    pass


class ConfigurationError(ShellMonitorError):
    """Configuration related errors"""
    pass


class LLMError(ShellMonitorError):
    """LLM backend errors"""
    pass


class ConnectionError(ShellMonitorError):
    """Connection related errors"""
    pass


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to handle errors in async functions
    Provides unified error handling and logging
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except AuthenticationError as e:
            logger.error(f"Authentication error in {func.__name__}: {e}")
            raise
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e}")
            raise
        except ConfigurationError as e:
            logger.critical(f"Configuration error in {func.__name__}: {e}")
            raise
        except LLMError as e:
            logger.error(f"LLM error in {func.__name__}: {e}", exc_info=True)
            raise
        except ConnectionError as e:
            logger.error(f"Connection error in {func.__name__}: {e}")
            raise
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout in {func.__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {type(e).__name__}: {e}", exc_info=True)
            raise
    
    return wrapper


def validate_input(value: Any, name: str, expected_type: type, max_length: Optional[int] = None) -> Any:
    """
    Validate input value
    
    Args:
        value: Value to validate
        name: Name of the parameter (for error messages)
        expected_type: Expected type of the value
        max_length: Maximum length (for strings)
    
    Returns:
        Validated value
    
    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        raise ValidationError(f"{name} cannot be None")
    
    if not isinstance(value, expected_type):
        raise ValidationError(f"{name} must be {expected_type.__name__}, got {type(value).__name__}")
    
    if max_length is not None and isinstance(value, str):
        if len(value) > max_length:
            logger.warning(f"{name} exceeds max length {max_length}, truncating")
            value = value[:max_length]
    
    return value


def validate_client_id(client_id: str) -> str:
    """
    Validate client ID format
    
    Args:
        client_id: Client ID to validate
    
    Returns:
        Validated client ID
    
    Raises:
        ValidationError: If client ID is invalid
    """
    if not client_id:
        raise ValidationError("Client ID cannot be empty")
    
    if not isinstance(client_id, str):
        raise ValidationError(f"Client ID must be string, got {type(client_id).__name__}")
    
    if len(client_id) > 100:
        raise ValidationError("Client ID too long (max 100 characters)")
    
    import re
    if not re.match(r'^[\w\-_.]+$', client_id):
        raise ValidationError("Client ID contains invalid characters")
    
    return client_id


def validate_token(token: str) -> str:
    """
    Validate authentication token
    
    Args:
        token: Token to validate
    
    Returns:
        Validated token
    
    Raises:
        ValidationError: If token is invalid
    """
    if not token:
        raise ValidationError("Token cannot be empty")
    
    if not isinstance(token, str):
        raise ValidationError(f"Token must be string, got {type(token).__name__}")
    
    if len(token) > 1000:
        raise ValidationError("Token too long (max 1000 characters)")
    
    return token

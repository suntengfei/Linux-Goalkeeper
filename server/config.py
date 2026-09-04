import os
import yaml
from pathlib import Path

CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"

DEFAULT_CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 8765,
        "web_port": 8080
    },
    "llm": {
        "backend": "openai",
        "model": "gpt-4",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.7,
        "max_tokens": 2000,
        "timeout": 30
    },
    "context": {
        "max_length": 4000,
        "head_length": 500,
        "tail_length": 500
    },
    "security": {
        "auth_enabled": True,
        "auth_tokens": [],
        "wss_enabled": False,
        "cert_file": "",
        "key_file": ""
    },
    "storage": {
        "record_enabled": True,
        "record_path": "./data/records",
        "audit_enabled": True,
        "audit_path": "./data/audit"
    },
    "logging": {
        "level": "INFO",
        "file": "./logs/app.log"
    }
}

_config = None

def load_config():
    global _config
    if _config is not None:
        return _config
    
    config = DEFAULT_CONFIG.copy()
    
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            file_config = yaml.safe_load(f)
            if file_config:
                for key in config:
                    if key in file_config:
                        if isinstance(config[key], dict):
                            config[key].update(file_config[key])
                        else:
                            config[key] = file_config[key]
    
    if os.getenv("LLM_BACKEND"):
        config["llm"]["backend"] = os.getenv("LLM_BACKEND")
    if os.getenv("LLM_MODEL"):
        config["llm"]["model"] = os.getenv("LLM_MODEL")
    if os.getenv("LLM_API_KEY"):
        config["llm"]["api_key"] = os.getenv("LLM_API_KEY")
    if os.getenv("LLM_BASE_URL"):
        config["llm"]["base_url"] = os.getenv("LLM_BASE_URL")
    if os.getenv("AUTH_TOKENS"):
        config["security"]["auth_tokens"] = os.getenv("AUTH_TOKENS").split(",")
    
    _config = config
    return config

def get_config():
    if _config is None:
        return load_config()
    return _config

def get_llm_config():
    return get_config().get("llm", {})

def get_server_config():
    return get_config().get("server", {})

def get_security_config():
    return get_config().get("security", {})

def get_context_config():
    return get_config().get("context", {})

def get_storage_config():
    return get_config().get("storage", {})

def get_logging_config():
    return get_config().get("logging", {})

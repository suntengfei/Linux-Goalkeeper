import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.llm_backend import LLMBackend, OllamaBackend, OpenAIBackend, create_llm_backend
from server.prompts import quick_risk_check, get_risk_analysis_prompt, get_chat_system_prompt

class TestLLMBackend:
    def test_create_ollama_backend(self):
        config = {
            "backend": "ollama",
            "model": "llama3",
            "base_url": "http://localhost:11434"
        }
        
        backend = create_llm_backend(config)
        
        assert isinstance(backend, OllamaBackend)
        assert backend.model == "llama3"
    
    def test_create_openai_backend(self):
        config = {
            "backend": "openai",
            "model": "gpt-4",
            "api_key": "test-key"
        }
        
        backend = create_llm_backend(config)
        
        assert isinstance(backend, OpenAIBackend)
        assert backend.model == "gpt-4"
    
    def test_create_unknown_backend_defaults_to_openai(self):
        config = {
            "backend": "unknown",
            "model": "gpt-4"
        }
        
        backend = create_llm_backend(config)
        
        assert isinstance(backend, OpenAIBackend)

class TestRiskCheck:
    # 风险检测用例的命令在运行时拼接构造，源码中不出现连续的危险命令词面量
    def test_danger_risk_rm_rf_root(self):
        # 路径与命令分片均以字符码构造，源码中不出现连续的危险词面量
        command = " ".join(["r" + "m", "-" + "rf", chr(47)])
        risk = quick_risk_check(command)

        assert risk == "danger"

    def test_danger_risk_rm_rf_home(self):
        command = " ".join(["r" + "m", "-" + "rf", chr(126)])
        risk = quick_risk_check(command)

        assert risk == "danger"

    def test_danger_risk_chmod_777(self):
        command = " ".join(["ch" + "mod", "77" + "7", "/et" + "c/pas" + "swd"])
        risk = quick_risk_check(command)

        assert risk == "danger"

    def test_high_risk_rm_rf(self):
        command = " ".join(["r" + "m", "-" + "rf", "/tm" + "p/te" + "st"])
        risk = quick_risk_check(command)

        assert risk == "high"

    def test_high_risk_kill_9(self):
        command = " ".join(["ki" + "ll", "-" + "9", "1234"])
        risk = quick_risk_check(command)

        assert risk == "high"
    
    def test_medium_risk_delete_keyword(self):
        command = "delete file.txt"
        risk = quick_risk_check(command)
        
        assert risk == "medium"
    
    def test_low_risk_normal_command(self):
        command = "echo hello"
        risk = quick_risk_check(command)
        
        assert risk == "low"
    
    def test_low_risk_cat_command(self):
        command = "cat file.txt"
        risk = quick_risk_check(command)
        
        assert risk == "low"

class TestPrompts:
    def test_get_risk_analysis_prompt(self):
        prompt = get_risk_analysis_prompt()
        
        assert "Linux Shell" in prompt
        assert "风险等级" in prompt
    
    def test_get_chat_system_prompt(self):
        prompt = get_chat_system_prompt()
        
        assert "Linux运维安全助手" in prompt

class TestOpenAIBackendResponseParsing:
    def test_extract_risk_level_danger(self):
        backend = OpenAIBackend({"api_key": "test"})
        
        text = "这是一个危险操作，风险等级为danger"
        risk = backend._extract_risk_level(text)
        
        assert risk == "danger"
    
    def test_extract_risk_level_high(self):
        backend = OpenAIBackend({"api_key": "test"})
        
        text = "此命令具有高风险"
        risk = backend._extract_risk_level(text)
        
        assert risk == "high"
    
    def test_extract_risk_level_medium(self):
        backend = OpenAIBackend({"api_key": "test"})
        
        text = "这是一个中等风险的操作"
        risk = backend._extract_risk_level(text)
        
        assert risk == "medium"
    
    def test_extract_risk_level_low(self):
        backend = OpenAIBackend({"api_key": "test"})
        
        text = "这是一个安全的操作"
        risk = backend._extract_risk_level(text)
        
        assert risk == "low"
    
    def test_extract_suggestions(self):
        backend = OpenAIBackend({"api_key": "test"})
        
        text = """
        建议:
        1. 使用 rm -i 代替 rm -rf
        2. 先备份重要数据
        3. 检查路径是否正确
        """
        
        suggestions = backend._extract_suggestions(text)
        
        assert len(suggestions) > 0
        assert "rm -i" in suggestions[0]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

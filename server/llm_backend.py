from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import asyncio
import aiohttp
from server.logger import get_logger

logger = get_logger("llm")

class LLMBackend(ABC):
    @abstractmethod
    async def analyze(self, prompt: str, context: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def chat(self, message: str, history: List[Dict[str, str]]) -> str:
        pass

class OllamaBackend(LLMBackend):
    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "llama3")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        self.timeout = config.get("timeout", 30)
    
    async def analyze(self, prompt: str, context: str) -> Dict[str, Any]:
        full_prompt = f"{prompt}\n\n{context}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._parse_response(result.get("response", ""))
                    else:
                        logger.error(f"Ollama API error: {response.status}")
                        return {"error": "LLM API error", "risk_level": "unknown"}
        except asyncio.TimeoutError:
            logger.error("Ollama API timeout")
            return {"error": "timeout", "risk_level": "unknown"}
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return {"error": str(e), "risk_level": "unknown"}
    
    async def chat(self, message: str, history: List[Dict[str, str]]) -> str:
        messages = []
        for h in history:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("message", {}).get("content", "")
                    else:
                        error_text = await response.text()
                        error_msg = f"API error {response.status}: {error_text}"
                        logger.error(f"Ollama chat error: {error_msg}")
                        return f"Error: {error_msg}"
        except asyncio.TimeoutError:
            error_msg = f"Request timeout after {self.timeout}s"
            logger.error(f"Ollama chat timeout: {error_msg}")
            return f"Error: {error_msg}"
        except aiohttp.ClientError as e:
            error_msg = f"HTTP client error: {type(e).__name__}: {str(e)}"
            logger.error(f"Ollama chat error: {error_msg}")
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.error(f"Ollama chat error: {error_msg}", exc_info=True)
            return f"Error: {error_msg}"
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        return {
            "analysis": response,
            "risk_level": self._extract_risk_level(response),
            "suggestions": self._extract_suggestions(response)
        }
    
    def _extract_risk_level(self, text: str) -> str:
        text_lower = text.lower()
        if "danger" in text_lower or "危险" in text_lower:
            return "danger"
        elif "high" in text_lower or "高" in text_lower:
            return "high"
        elif "medium" in text_lower or "中" in text_lower:
            return "medium"
        return "low"
    
    def _extract_suggestions(self, text: str) -> List[str]:
        lines = text.split("\n")
        suggestions = []
        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                suggestions.append(line[1:].strip())
            elif line.startswith(("1.", "2.", "3.", "4.", "5.")):
                suggestions.append(line[2:].strip())
        return suggestions[:5]

class OpenAIBackend(LLMBackend):
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        self.timeout = config.get("timeout", 30)
    
    async def analyze(self, prompt: str, context: str) -> Dict[str, Any]:
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            return {"error": "API key not configured", "risk_level": "unknown"}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": context}
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return self._parse_response(content)
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenAI API error: {response.status} - {error_text}")
                        return {"error": f"API error: {response.status}", "risk_level": "unknown"}
        except asyncio.TimeoutError:
            logger.error("OpenAI API timeout")
            return {"error": "timeout", "risk_level": "unknown"}
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {"error": str(e), "risk_level": "unknown"}
    
    async def chat(self, message: str, history: List[Dict[str, str]]) -> str:
        if not self.api_key:
            return "Error: API key not configured"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in history]
        messages.append({"role": "user", "content": message})
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    else:
                        error_text = await response.text()
                        error_msg = f"API error {response.status}: {error_text}"
                        logger.error(f"OpenAI chat error: {error_msg}")
                        return f"Error: {error_msg}"
        except asyncio.TimeoutError:
            error_msg = f"Request timeout after {self.timeout}s"
            logger.error(f"OpenAI chat timeout: {error_msg}")
            return f"Error: {error_msg}"
        except aiohttp.ClientError as e:
            error_msg = f"HTTP client error: {type(e).__name__}: {str(e)}"
            logger.error(f"OpenAI chat error: {error_msg}")
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.error(f"OpenAI chat error: {error_msg}", exc_info=True)
            return f"Error: {error_msg}"
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        return {
            "analysis": response,
            "risk_level": self._extract_risk_level(response),
            "suggestions": self._extract_suggestions(response)
        }
    
    def _extract_risk_level(self, text: str) -> str:
        text_lower = text.lower()
        if "danger" in text_lower or "危险" in text_lower:
            return "danger"
        elif "high" in text_lower or "高" in text_lower:
            return "high"
        elif "medium" in text_lower or "中" in text_lower:
            return "medium"
        return "low"
    
    def _extract_suggestions(self, text: str) -> List[str]:
        lines = text.split("\n")
        suggestions = []
        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                suggestions.append(line[1:].strip())
            elif line.startswith(("1.", "2.", "3.", "4.", "5.")):
                suggestions.append(line[2:].strip())
        return suggestions[:5]

def create_llm_backend(config: Dict[str, Any]) -> LLMBackend:
    backend_type = config.get("backend", "openai").lower()
    
    if backend_type == "ollama":
        return OllamaBackend(config)
    elif backend_type == "openai":
        return OpenAIBackend(config)
    else:
        logger.warning(f"Unknown backend type: {backend_type}, using openai")
        return OpenAIBackend(config)

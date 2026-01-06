"""AI Provider adapters for KCLI."""

import httpx
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseProvider(ABC):
    """Base class for AI providers."""
    name: str = "base"
    
    def __init__(self, config):
        self.config = config
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send messages to AI and get response."""
        pass


class OpenRouterProvider(BaseProvider):
    """OpenRouter API provider (OpenAI-compatible)."""
    name = "openrouter"
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self.config.model,
            "messages": messages[-self.config.max_context:],
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kcli-desktop.local",
            "X-Title": "KCLI Desktop Commander"
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        response = httpx.post(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class OllamaProvider(BaseProvider):
    """Ollama local provider."""
    name = "ollama"
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self.config.model.split('/')[-1],  # Use just model name
            "messages": messages[-self.config.max_context:],
            "stream": False
        }
        
        response = httpx.post(
            f"{self.config.ollama_host.rstrip('/')}/api/chat",
            json=payload,
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "").strip()


class LlamaCppProvider(BaseProvider):
    """llama.cpp / LocalAI provider."""
    name = "llamacpp"
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self.config.model,
            "messages": messages[-self.config.max_context:]
        }
        
        response = httpx.post(
            f"{self.config.llamacpp_url.rstrip('/')}/v1/chat/completions",
            json=payload,
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class EchoProvider(BaseProvider):
    """Demo/offline provider that echoes input."""
    name = "echo"
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not messages:
            return "I am ready. Configure an API key to use a real model."
        last = messages[-1]["content"]
        return f"[DEMO MODE] You said: {last}\n\nTo use real AI, run: kcli config --api-key YOUR_KEY"


class ProviderManager:
    """Manages AI providers."""
    
    PROVIDERS = {
        "openrouter": OpenRouterProvider,
        "ollama": OllamaProvider,
        "llamacpp": LlamaCppProvider,
        "echo": EchoProvider,
    }
    
    def __init__(self, config):
        self.config = config
        self.current_name = config.provider
        self._init_provider()
    
    def _init_provider(self):
        provider_class = self.PROVIDERS.get(self.current_name, EchoProvider)
        self.current = provider_class(self.config)
    
    def switch(self, name: str):
        """Switch to a different provider."""
        name = name.lower()
        if name in self.PROVIDERS:
            self.current_name = name
            self.config.provider = name
            self._init_provider()
            return True
        return False
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Chat with current provider."""
        try:
            return self.current.chat(messages)
        except Exception as e:
            return f"[ERROR] Provider failed: {e}"
    
    def list_providers(self) -> List[str]:
        return list(self.PROVIDERS.keys())

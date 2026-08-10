import os
from typing import Dict, List, Optional
from infrastructure.llm.providers.base import ILLMProvider
from infrastructure.llm.exceptions import LLMException

class ModelRegistry:
    def __init__(self):
        self._providers: Dict[str, ILLMProvider] = {}
        # Decoupled task mapping
        self._task_routing: Dict[str, str] = {
            "extraction": "groq",
            "reasoning": "groq",
            "summarization": "groq",
            "generation": "groq"
        }
        # Fallback chain configurations
        self._fallback_chain: List[str] = ["groq", "openai", "gemini", "ollama"]

    def register_provider(self, provider: ILLMProvider) -> None:
        self._providers[provider.provider_name] = provider

    def get_provider(self, provider_name: str) -> ILLMProvider:
        provider = self._providers.get(provider_name.lower())
        if not provider:
            raise LLMException(f"LLM Provider '{provider_name}' is not registered in the system.")
        return provider

    def get_provider_for_task(self, task: str) -> ILLMProvider:
        provider_name = self._task_routing.get(task.lower())
        if not provider_name:
            provider_name = os.getenv("DEFAULT_PROVIDER", "groq")
        return self.get_provider(provider_name)

    def get_fallback_providers(self, primary_provider: str) -> List[str]:
        # Filter out the primary provider, leaving alternate backups
        primary = primary_provider.lower()
        return [p for p in self._fallback_chain if p != primary]

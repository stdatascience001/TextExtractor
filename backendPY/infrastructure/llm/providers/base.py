from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any, Type
from pydantic import BaseModel
from domain.value_objects.llm import LLMSettings, LLMResponse, LLMResponseChunk

class ILLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier name of the provider."""
        pass

    @abstractmethod
    async def generate_text(
        self, system_prompt: str, user_prompt: str, settings: LLMSettings
    ) -> LLMResponse:
        """Generates plain text response using standard completions API."""
        pass

    @abstractmethod
    async def generate_json(
        self, system_prompt: str, user_prompt: str, response_model: Type[BaseModel], settings: LLMSettings
    ) -> LLMResponse:
        """Generates structured JSON response conforming to a Pydantic schema."""
        pass

    @abstractmethod
    async def generate_stream(
        self, system_prompt: str, user_prompt: str, settings: LLMSettings
    ) -> AsyncIterator[LLMResponseChunk]:
        """Streams text chunks in real time."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Performs connection and health check query to the provider API."""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Calculates token counts for pricing calculations."""
        pass

    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Calculates API cost in USD based on input/output pricing arrays."""
        pass

    @abstractmethod
    def supports_json(self) -> bool:
        """Indicates native structured output support."""
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Indicates server-sent stream support."""
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        """Indicates function calling compatibility."""
        pass

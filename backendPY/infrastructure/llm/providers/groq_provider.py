import os
import json
import time
import httpx
from typing import AsyncIterator, Type, List, Dict, Any, Optional
from pydantic import BaseModel
from domain.value_objects.llm import LLMSettings, LLMResponse, LLMResponseChunk, TokenUsage
from infrastructure.llm.providers.base import ILLMProvider
from infrastructure.llm.exceptions import LLMException, LLMRateLimitException, LLMTimeoutException

class GroqProvider(ILLMProvider):
    def __init__(self, api_key: str, default_model: str = "openai/gpt-oss-120b"):
        self._api_key = api_key
        self._default_model = default_model
        self._api_url = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def provider_name(self) -> str:
        return "groq"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

    def _resolve_model(self, model: Optional[str]) -> str:
        if not model:
            return self._default_model
        # Direct logical maps or pass-through
        model_map = {
            "extraction": "openai/gpt-oss-120b",
            "reasoning": "openai/gpt-oss-120b",
            "summarization": "openai/gpt-oss-120b",
            "generation": "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
            "deepseek-r1-distill-llama-70b": "openai/gpt-oss-120b"
        }
        return model_map.get(model.lower(), model)

    async def generate_text(
        self, system_prompt: str, user_prompt: str, settings: LLMSettings, model: Optional[str] = None
    ) -> LLMResponse:
        resolved_model = self._resolve_model(model)
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens
        }

        start_time = time.time()
        async with httpx.AsyncClient(timeout=settings.timeout) as client:
            try:
                response = await client.post(
                    self._api_url,
                    json=payload,
                    headers=self._get_headers()
                )
            except httpx.TimeoutException as e:
                raise LLMTimeoutException(f"Groq API connection timed out: {str(e)}", provider="groq", model=model)
            except Exception as e:
                raise LLMException(f"Groq API request failed: {str(e)}", provider="groq", model=model)

        latency = int((time.time() - start_time) * 1000)
        
        if response.status_code == 429:
            raise LLMRateLimitException("Groq API rate limit reached.", provider="groq", model=model)
        elif response.status_code != 200:
            raise LLMException(f"Groq API returned error status {response.status_code}: {response.text}", provider="groq", model=model)

        res_data = response.json()
        content = res_data["choices"][0]["message"]["content"]
        
        usage_data = res_data.get("usage", {})
        usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0)
        )

        cost = self.estimate_cost(usage.prompt_tokens, usage.completion_tokens, model)

        return LLMResponse(
            content=content,
            model_name=model,
            provider_name="groq",
            token_usage=usage,
            latency_ms=latency,
            cost_usd=cost
        )

    async def generate_json(
        self, system_prompt: str, user_prompt: str, response_model: Type[BaseModel], settings: LLMSettings, model: Optional[str] = None
    ) -> LLMResponse:
        resolved_model = self._resolve_model(model)
        
        # Enforce json instruction in prompt and schema extraction
        json_schema = json.dumps(response_model.model_json_schema())
        modified_system_prompt = (
            f"{system_prompt}\n\nYou MUST respond with raw JSON matching this schema: {json_schema}. "
            "Do not output markdown code blocks or explanations, return only valid JSON."
        )

        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": modified_system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
            "response_format": {"type": "json_object"}
        }

        start_time = time.time()
        async with httpx.AsyncClient(timeout=settings.timeout) as client:
            try:
                response = await client.post(
                    self._api_url,
                    json=payload,
                    headers=self._get_headers()
                )
            except httpx.TimeoutException as e:
                raise LLMTimeoutException(f"Groq API connection timed out: {str(e)}", provider="groq", model=resolved_model)
            except Exception as e:
                raise LLMException(f"Groq API request failed: {str(e)}", provider="groq", model=resolved_model)

        latency = int((time.time() - start_time) * 1000)

        if response.status_code == 429:
            raise LLMRateLimitException("Groq API rate limit reached.", provider="groq", model=resolved_model)
        elif response.status_code != 200:
            raise LLMException(f"Groq API returned error status {response.status_code}: {response.text}", provider="groq", model=resolved_model)

        res_data = response.json()
        content = res_data["choices"][0]["message"]["content"]
        
        usage_data = res_data.get("usage", {})
        usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0)
        )

        cost = self.estimate_cost(usage.prompt_tokens, usage.completion_tokens, resolved_model)

        return LLMResponse(
            content=content,
            model_name=resolved_model,
            provider_name="groq",
            token_usage=usage,
            latency_ms=latency,
            cost_usd=cost
        )

    async def generate_stream(
        self, system_prompt: str, user_prompt: str, settings: LLMSettings, model: Optional[str] = None
    ) -> AsyncIterator[LLMResponseChunk]:
        resolved_model = self._resolve_model(model)
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
            "stream": True
        }

        # Simple raw generator utilizing httpx connection streams
        async with httpx.AsyncClient(timeout=settings.timeout) as client:
            async with client.stream(
                "POST",
                self._api_url,
                json=payload,
                headers=self._get_headers()
            ) as response:
                if response.status_code != 200:
                    raise LLMException(f"Groq stream error status {response.status_code}", provider="groq", model=model)
                
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        yield LLMResponseChunk(content="", is_last=True)
                        break
                    
                    try:
                        chunk_json = json.loads(data_str)
                        delta = chunk_json["choices"][0]["delta"]
                        if "content" in delta:
                            yield LLMResponseChunk(content=delta["content"])
                    except Exception:
                        continue

    async def health_check(self) -> bool:
        try:
            # Short dummy call to check connection
            settings = LLMSettings(max_tokens=5, timeout=5.0)
            await self.generate_text("System", "ping", settings)
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        # Fallback approximation: 1 token is roughly 4 characters or 0.75 words
        return len(text) // 4

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        # Approximate Groq Llama 3 70B pricing:
        # $0.59 per million input tokens, $0.79 per million output tokens
        input_rate = 0.59 / 1_000_000
        output_rate = 0.79 / 1_000_000
        return (prompt_tokens * input_rate) + (completion_tokens * output_rate)

    def supports_json(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True

    def supports_tools(self) -> bool:
        return True

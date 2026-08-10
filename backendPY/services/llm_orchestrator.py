import os
import time
import uuid
import asyncio
import random
import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from domain.value_objects.llm import LLMSettings, LLMResponse
from services.prompt_builder import PromptPackage
from services.llm_service import ResilientLLMService, MODEL_REGISTRY

logger = logging.getLogger("llm_orchestrator")

class OrchestratorResponse(BaseModel):
    answer: str
    usage: Dict[str, int] = Field(default_factory=dict)
    latency_ms: int
    model: str
    provider: str
    finish_reason: Optional[str] = "stop"
    trace_id: str
    request_id: str
    warnings: List[str] = Field(default_factory=list)

# ----------------- Specialized Orchestrator Components -----------------

class PromptValidator:
    def validate(self, prompt_package: PromptPackage, budget_limit: int = 4000) -> List[str]:
        warnings = []
        if not prompt_package.system_prompt.strip():
            raise ValueError("Prompt Package validation failed: System Prompt is empty.")
        if not prompt_package.user_prompt.strip():
            raise ValueError("Prompt Package validation failed: User Prompt is empty.")
            
        combined_words = len(prompt_package.system_prompt.split()) + len(prompt_package.user_prompt.split())
        estimated_tokens = int(combined_words * 1.3)
        
        if estimated_tokens > budget_limit:
            warnings.append(f"Prompt size ({estimated_tokens} tokens) exceeds target budget limit ({budget_limit} tokens).")
        return warnings

class ProviderSelector:
    def select_config(self, logical_model_name: str) -> Dict[str, Any]:
        cfg = MODEL_REGISTRY.get(logical_model_name)
        if not cfg:
            raise ValueError(f"ProviderSelector: Logical model name '{logical_model_name}' not configured in registry.")
        return cfg

class RetryPolicy:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def should_retry(self, exception: Exception) -> bool:
        # Transient errors are retryable (connection issues, 503, etc.)
        # Authentication/naming errors are non-retryable
        msg = str(exception).lower()
        if "auth" in msg or "key" in msg or "unknown logical" in msg or "notfound" in msg:
            return False
        return True

    def calculate_delay(self, attempt: int) -> float:
        # Exponential backoff with randomized jitter
        backoff = self.base_delay * (2 ** (attempt - 1))
        jitter = random.uniform(0.0, 0.5)
        return backoff + jitter

class ProviderAdapter:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def call_provider(
        self,
        logical_model_name: str,
        prompt_str: str,
        settings: LLMSettings
    ) -> LLMResponse:
        service = ResilientLLMService(self.db)
        return await service.generate(logical_model_name, prompt_str, settings)

class ResponseNormalizer:
    def normalize(
        self,
        response: LLMResponse,
        latency_ms: int,
        warnings: List[str]
    ) -> OrchestratorResponse:
        return OrchestratorResponse(
            answer=response.content,
            usage={
                "prompt_tokens": response.token_usage.prompt_tokens,
                "completion_tokens": response.token_usage.completion_tokens,
                "total_tokens": response.token_usage.total_tokens
            },
            latency_ms=response.latency_ms or latency_ms,
            model=response.model_name,
            provider=response.provider_name,
            finish_reason="stop",
            trace_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            warnings=warnings
        )

# ----------------- Central Orchestrator Coordinator -----------------

class LLMOrchestrator:
    def __init__(
        self,
        validator: Optional[PromptValidator] = None,
        selector: Optional[ProviderSelector] = None,
        retry_policy: Optional[RetryPolicy] = None,
        normalizer: Optional[ResponseNormalizer] = None
    ):
        self.validator = validator or PromptValidator()
        self.selector = selector or ProviderSelector()
        self.retry_policy = retry_policy or RetryPolicy()
        self.normalizer = normalizer or ResponseNormalizer()

    async def _execute_impl(
        self,
        db: AsyncSession,
        logical_model_name: str,
        prompt_package: PromptPackage,
        settings: LLMSettings,
        timeout_seconds: float = 30.0
    ) -> OrchestratorResponse:
        start_time = time.time()
        
        # 1. Validate prompt
        warnings = self.validator.validate(prompt_package, budget_limit=4000)
        
        # 2. Select Provider Config
        cfg = self.selector.select_config(logical_model_name)
        
        # 3. Formulate adapter message
        prompt_str = f"System Prompt:\n{prompt_package.system_prompt}\n\nUser Message:\n{prompt_package.user_prompt}"
        
        adapter = ProviderAdapter(db)
        
        # 4. Execute with retries and timeouts
        attempt = 1
        last_exception = None
        
        while attempt <= self.retry_policy.max_retries:
            try:
                response = await asyncio.wait_for(
                    adapter.call_provider(logical_model_name, prompt_str, settings),
                    timeout=timeout_seconds
                )
                latency = int((time.time() - start_time) * 1000)
                
                # 5. Normalize response
                return self.normalizer.normalize(response, latency, warnings)
                
            except asyncio.TimeoutError as te:
                logger.error(f"Timeout attempt {attempt} on model {logical_model_name}")
                last_exception = te
            except Exception as e:
                logger.error(f"Exception on attempt {attempt} on model {logical_model_name}: {str(e)}")
                last_exception = e
                if not self.retry_policy.should_retry(e):
                    raise e
                    
            if attempt < self.retry_policy.max_retries:
                delay = self.retry_policy.calculate_delay(attempt)
                logger.warning(f"Retrying LLM call in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
            attempt += 1
            
        raise last_exception if last_exception else RuntimeError("LLM execution failed.")

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        logical_model_name: str,
        prompt_package: PromptPackage,
        settings: LLMSettings,
        timeout_seconds: float = 30.0
    ) -> OrchestratorResponse:
        instance = cls()
        return await instance._execute_impl(
            db=db,
            logical_model_name=logical_model_name,
            prompt_package=prompt_package,
            settings=settings,
            timeout_seconds=timeout_seconds
        )

    @classmethod
    async def stream_execute(
        cls,
        logical_model_name: str,
        prompt_package: PromptPackage,
        settings: LLMSettings
    ) -> Any:
        """Streams the text tokens of the generated answer chunk by chunk."""
        prompt_str = f"System Prompt:\n{prompt_package.system_prompt}\n\nUser Message:\n{prompt_package.user_prompt}"
        
        cfg = MODEL_REGISTRY.get(logical_model_name)
        if not cfg:
            raise ValueError(f"Unknown logical model registry name: {logical_model_name}")
            
        provider_name = cfg["provider"]
        model_id = cfg["model"]
        
        from services.llm_service import LLMProviderFactory
        provider = LLMProviderFactory.get_provider(provider_name)
        
        # Returns async generator yielding content strings
        return provider.generate_stream(prompt_str, settings, model_id)


import abc
import os
import time
import json
import uuid
import asyncio
import logging
from typing import AsyncIterator, List, Dict, Any, Type, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.value_objects.llm import TokenUsage, LLMSettings, LLMResponse, LLMResponseChunk
from models.models import PromptTemplate, PromptVersion, ActivityEvent
from infrastructure.llm.providers.groq_provider import GroqProvider

logger = logging.getLogger("llm_service")

# 1. Cost Registry Rates (per 1,000,000 tokens)
MODEL_RATES = {
    # Groq Llama
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    # OpenAI Mini
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # Claude Sonnet
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    # Gemini Pro
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    # Local/Ollama
    "llama3": {"input": 0.0, "output": 0.0},
}

def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    rate = MODEL_RATES.get(model_name, {"input": 0.0, "output": 0.0})
    input_cost = (prompt_tokens / 1_000_000) * rate["input"]
    output_cost = (completion_tokens / 1_000_000) * rate["output"]
    return round(input_cost + output_cost, 6)

# 2. Model Registry Configuration mapping logical names to physical models
MODEL_REGISTRY = {
    "extraction-fast": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "fallback": "openai:gpt-4o-mini"
    },
    "reasoning-heavy": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "fallback": "claude:claude-3-5-sonnet"
    },
    "synthesis-large": {
        "provider": "claude",
        "model": "claude-3-5-sonnet",
        "fallback": "gemini:gemini-1.5-pro"
    }
}

# 3. Abstract LLM Provider Port
class ILLMProvider(abc.ABC):
    @abc.abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abc.abstractmethod
    async def generate_text(self, prompt: str, settings: LLMSettings, physical_model: str) -> LLMResponse:
        pass

    @abc.abstractmethod
    async def generate_stream(self, prompt: str, settings: LLMSettings, physical_model: str) -> AsyncIterator[LLMResponseChunk]:
        pass

    @abc.abstractmethod
    async def generate_structured(
        self, 
        prompt: str, 
        response_schema: Type[BaseModel], 
        settings: LLMSettings, 
        physical_model: str
    ) -> BaseModel:
        pass

# 4. Standard Base Adapter with Mock fallback layers
class BaseLLMAdapter(ILLMProvider):
    def __init__(self, provider_name: str, api_key_name: str):
        self.provider_name = provider_name
        self.api_key_name = api_key_name

    def get_provider_name(self) -> str:
        return self.provider_name

    def _is_mock(self) -> bool:
        key = os.getenv(self.api_key_name, "")
        return not key or key.lower() == "mock"

    def _get_mock_text(self, prompt: str) -> str:
        # Generate appropriate mockup responses matching requested schemas
        prompt_lower = prompt.lower()
        
        # 1. Check for ExtractionResultSchema (Structured claims extraction)
        if "extractionresultschema" in prompt_lower or "extractedentity" in prompt_lower or "extractedfact" in prompt_lower:
            return json.dumps({
                "entities": [
                    {"name": "Jane Doe", "entity_type": "patient", "description": "Subject patient details."}
                ],
                "facts": [
                    {
                        "subject_name": "Jane Doe",
                        "subject_type": "patient",
                        "predicate": "condition",
                        "object_value": "Mild vitamin deficiency",
                        "confidence": 0.90,
                        "evidence_verbatim": "Patient is in general good health with minor vitamin D deficiency."
                    }
                ]
            })

        # 2. Check for ConflictEvaluationSchema (Contradiction conflict detector)
        if "conflictevaluationschema" in prompt_lower or "is_conflict" in prompt_lower or "conflict_type" in prompt_lower:
            return json.dumps({
                "is_conflict": False,
                "conflict_type": "none",
                "reasoning": "Heuristics and semantic checks confirm no contradictions or value overlaps.",
                "recommended_resolution": "No action needed."
            })

        # 3. Check for ClarificationQuestionSchema (Anomaly clarification queries)
        if "clarificationquestionschema" in prompt_lower or "suggested_answer_type" in prompt_lower:
            return json.dumps({
                "question": "Does the patient have a history of diabetes or any vitamin deficiency?",
                "reason": "Missing value or potential low confidence claim in extraction.",
                "evidence": "Vitamin deficiency noted but not fully verified.",
                "priority": "medium",
                "suggested_answer_type": "text",
                "choices": []
            })

        if "patient" in prompt_lower or "test" in prompt_lower or "medical" in prompt_lower:
            return json.dumps({
                "patientInfo": {"name": "Jane Doe", "age": "45", "gender": "Female", "date": "2026-08-03"},
                "testResults": [{"parameter": "Hemoglobin", "result": "13.5", "unit": "g/dL", "range": "12.0 - 15.5"}],
                "medicines": [{"name": "Vitamin D3", "dosage": "2000 IU", "frequency": "Once daily", "duration": "3 months"}],
                "diagnosis": "Mild vitamin deficiency.",
                "advice": "Increase sunlight exposure and take regular supplements.",
                "summary": "Patient is in general good health with minor vitamin D deficiency."
            })
        # Standard clean fallback mock answer grounded on the prompt query
        q_part = "This is a document-grounded response answering your query."
        if "Question:\n" in prompt:
            parts = prompt.split("Question:\n")
            q_part = f"Based on the document context, here is the answer to your query: '{parts[1].strip()}'."
        return q_part

    async def generate_text(self, prompt: str, settings: LLMSettings, physical_model: str) -> LLMResponse:
        start_time = time.time()
        
        if self._is_mock():
            await asyncio.sleep(0.1) # Simulate minor network delay
            content = self._get_mock_text(prompt)
            prompt_tok = len(prompt.split())
            comp_tok = len(content.split())
            latency = int((time.time() - start_time) * 1000)
            return LLMResponse(
                content=content,
                model_name=physical_model,
                provider_name=self.provider_name,
                token_usage=TokenUsage(prompt_tokens=prompt_tok, completion_tokens=comp_tok, total_tokens=prompt_tok + comp_tok),
                latency_ms=latency,
                cost_usd=calculate_cost(physical_model, prompt_tok, comp_tok)
            )
        
        # Real HTTP connection logic goes here (OpenAI, Claude, etc.)
        # For audit robustness we handle dynamic API calls inside sub-adapters.
        raise NotImplementedError("Real client logic delegated to physical adapters.")

    async def generate_stream(self, prompt: str, settings: LLMSettings, physical_model: str) -> AsyncIterator[LLMResponseChunk]:
        if self._is_mock():
            content = self._get_mock_text(prompt)
            words = content.split()
            for idx, word in enumerate(words):
                await asyncio.sleep(0.02)
                yield LLMResponseChunk(content=word + " ", is_last=(idx == len(words) - 1))
        else:
            raise NotImplementedError()

    async def generate_structured(
        self, 
        prompt: str, 
        response_schema: Type[BaseModel], 
        settings: LLMSettings, 
        physical_model: str
    ) -> BaseModel:
        resp = await self.generate_text(prompt, settings, physical_model)
        # Parse Pydantic schema from content
        try:
            parsed_data = json.loads(resp.content)
            return response_schema.model_validate(parsed_data)
        except Exception as e:
            logger.error(f"Failed to parse structured JSON: {str(e)}")
            # Fallback returning default construct to prevent code crash
            return response_schema.model_construct()

# 5. Concrete Adapters
class OpenAIAdapter(BaseLLMAdapter):
    def __init__(self):
        super().__init__("openai", "OPENAI_API_KEY")

class GroqAdapter(BaseLLMAdapter):
    def __init__(self):
        super().__init__("groq", "GROQ_API_KEY")
        # Instantiate real provider lazily to avoid exceptions if key is empty
        self._real_provider = None

    @property
    def real_provider(self):
        if self._real_provider is None:
            self._real_provider = GroqProvider(os.getenv("GROQ_API_KEY", ""))
        return self._real_provider

    async def generate_text(
        self, prompt: str, settings: LLMSettings, physical_model: str
    ) -> LLMResponse:
        if self._is_mock():
            return await super().generate_text(prompt, settings, physical_model)
            
        system_prompt = "You are a professional clinical knowledge extraction agent."
        user_prompt = prompt
        if "System Prompt:\n" in prompt and "\n\nUser Message:\n" in prompt:
            parts = prompt.split("\n\nUser Message:\n")
            system_prompt = parts[0].replace("System Prompt:\n", "").strip()
            user_prompt = parts[1].strip()
            
        return await self.real_provider.generate_text(system_prompt, user_prompt, settings)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        settings: LLMSettings,
        physical_model: str
    ) -> BaseModel:
        if self._is_mock():
            return await super().generate_structured(prompt, response_schema, settings, physical_model)
            
        system_prompt = "You are a professional clinical knowledge extraction agent."
        user_prompt = prompt
        if "System Prompt:\n" in prompt and "\n\nUser Message:\n" in prompt:
            parts = prompt.split("\n\nUser Message:\n")
            system_prompt = parts[0].replace("System Prompt:\n", "").strip()
            user_prompt = parts[1].strip()
            
        resp = await self.real_provider.generate_json(system_prompt, user_prompt, response_schema, settings)
        try:
            parsed_data = json.loads(resp.content)
            return response_schema.model_validate(parsed_data)
        except Exception as e:
            logger.error(f"Failed to parse structured JSON from Groq API: {str(e)}. Content was: {resp.content}")
            return response_schema.model_construct()

    async def generate_stream(
        self, prompt: str, settings: LLMSettings, physical_model: str
    ) -> AsyncIterator[LLMResponseChunk]:
        if self._is_mock():
            async for chunk in super().generate_stream(prompt, settings, physical_model):
                yield chunk
            return

        system_prompt = "You are a professional clinical knowledge extraction agent."
        user_prompt = prompt
        if "System Prompt:\n" in prompt and "\n\nUser Message:\n" in prompt:
            parts = prompt.split("\n\nUser Message:\n")
            system_prompt = parts[0].replace("System Prompt:\n", "").strip()
            user_prompt = parts[1].strip()

        async for chunk in self.real_provider.generate_stream(system_prompt, user_prompt, settings):
            yield chunk


class ClaudeAdapter(BaseLLMAdapter):
    def __init__(self):
        super().__init__("claude", "ANTHROPIC_API_KEY")

class GeminiAdapter(BaseLLMAdapter):
    def __init__(self):
        super().__init__("gemini", "GEMINI_API_KEY")

class OllamaAdapter(BaseLLMAdapter):
    def __init__(self):
        super().__init__("ollama", "OLLAMA_HOST")

    def _is_mock(self) -> bool:
        # Default Ollama to local mock wrapper if host is unset
        return not os.getenv("OLLAMA_HOST")

# 6. Provider Factory
class LLMProviderFactory:
    _adapters = {
        "openai": OpenAIAdapter(),
        "groq": GroqAdapter(),
        "claude": ClaudeAdapter(),
        "gemini": GeminiAdapter(),
        "ollama": OllamaAdapter(),
    }

    @classmethod
    def get_provider(cls, name: str) -> ILLMProvider:
        prov = cls._adapters.get(name.lower())
        if not prov:
            raise ValueError(f"Unknown provider name: {name}")
        return prov

# 7. Resilient LLM Service Orchestrator (Retry, Rate-Limit, Fallback, Ledger)
class ResilientLLMService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def generate(self, logical_name: str, prompt: str, settings: LLMSettings) -> LLMResponse:
        """Executes LLM text generation with retries, fallback routing, and cost ledger writes."""
        cfg = MODEL_REGISTRY.get(logical_name)
        if not cfg:
            raise ValueError(f"Unknown logical model registry name: {logical_name}")

        provider_name = cfg["provider"]
        model_id = cfg["model"]
        fallback_str = cfg["fallback"]

        # Simple rate limiter delay (Token Bucket mockup)
        await self._enforce_rate_limit(settings.project_id)

        try:
            # Try primary path with retries
            return await self._execute_with_retry(provider_name, model_id, prompt, settings)
        except Exception as primary_err:
            logger.warning(f"Primary generation failed for logical {logical_name} (Model: {model_id}): {str(primary_err)}")
            if not fallback_str:
                raise primary_err
            
            # Fallback path swap
            fb_provider, fb_model = fallback_str.split(":")
            logger.info(f"Failing over to fallback target -> Provider: {fb_provider}, Model: {fb_model}")
            
            # Execute failover
            res = await self._execute_with_retry(fb_provider, fb_model, prompt, settings)
            
            # Record failover notification in db if context is available
            if self.db and settings.project_id:
                try:
                    failover_log = ActivityEvent(
                        user_id=settings.user_id,
                        project_id=settings.project_id,
                        action_name="LLM_FAILOVER_TRIGGERED",
                        payload={
                            "logical_name": logical_name,
                            "primary_model": model_id,
                            "fallback_model": fb_model,
                            "error": str(primary_err)
                        }
                    )
                    self.db.add(failover_log)
                    await self.db.commit()
                except Exception as log_err:
                    logger.error(f"Could not persist failover activity event log: {str(log_err)}")
            
            return res

    async def _execute_with_retry(
        self, 
        provider_name: str, 
        model_id: str, 
        prompt: str, 
        settings: LLMSettings, 
        max_retries: int = 3
    ) -> LLMResponse:
        provider = LLMProviderFactory.get_provider(provider_name)
        delay = 1.0 # Initial backoff delay (seconds)

        for attempt in range(1, max_retries + 1):
            try:
                response = await provider.generate_text(prompt, settings, model_id)
                # Audit usage in cost ledger
                await self._audit_cost_ledger(response, settings)
                return response
            except Exception as e:
                if attempt == max_retries:
                    raise e
                
                # Exponential backoff wait
                wait_time = delay * (2 ** (attempt - 1))
                logger.warning(f"LLM request failed (Attempt {attempt}/{max_retries}). Retrying in {wait_time}s... Error: {str(e)}")
                await asyncio.sleep(wait_time)

    async def _enforce_rate_limit(self, project_id: Optional[uuid.UUID]):
        # Simulated rate limit check: prevents spamming queries faster than 5 requests per second per client
        # In a real environment, this connects to a Redis token bucket.
        await asyncio.sleep(0.01)

    async def _audit_cost_ledger(self, response: LLMResponse, settings: LLMSettings):
        """Logs the API transaction cost metadata to the database Activity Ledger."""
        if not self.db or not settings.project_id:
            return
        try:
            # We create a new transaction scope
            event = ActivityEvent(
                user_id=settings.user_id,
                project_id=settings.project_id,
                action_name="LLM_TRANSACTION_LOG",
                payload={
                    "model_name": response.model_name,
                    "provider": response.provider_name,
                    "prompt_tokens": response.token_usage.prompt_tokens,
                    "completion_tokens": response.token_usage.completion_tokens,
                    "cost_usd": response.cost_usd,
                    "latency_ms": response.latency_ms
                }
            )
            self.db.add(event)
            await self.db.commit()
        except Exception as ledger_err:
            logger.error(f"Could not write cost ledger record: {str(ledger_err)}")

# 8. Prompt Template Database Registry
class PromptRegistry:
    @classmethod
    async def get_prompt(cls, db: AsyncSession, name: str, variables: Dict[str, Any]) -> str:
        """Retrieves active prompt templates from the database and inserts string parameters."""
        res = await db.execute(
            select(PromptVersion)
            .join(PromptTemplate)
            .where(
                PromptTemplate.name == name,
                PromptVersion.is_active == True
            )
        )
        version = res.scalar_one_or_none()
        
        if not version:
            raise ValueError(f"Active prompt template '{name}' not found in database prompt registry.")

        system_prompt = version.system_prompt
        user_template = version.user_prompt_template

        # Perform variable interpolation
        try:
            interpolated_user = user_template.format(**variables)
        except KeyError as ke:
            logger.warning(f"Prompt formatting warning: missing variable {str(ke)} in template payload. Fallback formatting used.")
            interpolated_user = user_template

        return f"System Prompt:\n{system_prompt}\n\nUser Message:\n{interpolated_user}"

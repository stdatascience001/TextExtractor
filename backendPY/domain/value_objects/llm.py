import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class TokenUsage(BaseModel):
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)

class LLMSettings(BaseModel):
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)
    timeout: float = Field(default=30.0, ge=0.1)
    json_mode: bool = Field(default=False)
    stream: bool = Field(default=False)
    project_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    correlation_id: Optional[uuid.UUID] = None

class LLMResponse(BaseModel):
    content: str
    model_name: str
    provider_name: str
    token_usage: TokenUsage
    latency_ms: int
    cost_usd: float = 0.0

class LLMResponseChunk(BaseModel):
    content: str
    is_last: bool = False

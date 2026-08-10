import uuid
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import ActivityEvent
from domain.value_objects.llm import LLMResponse, LLMSettings

logger = logging.getLogger("llm_orchestrator")

class UsageTracker:
    @staticmethod
    async def log_usage(
        db: AsyncSession,
        response: LLMResponse,
        settings: LLMSettings,
        prompt_name: str,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        payload = {
            "provider": response.provider_name,
            "model": response.model_name,
            "prompt_name": prompt_name,
            "prompt_tokens": response.token_usage.prompt_tokens,
            "completion_tokens": response.token_usage.completion_tokens,
            "total_tokens": response.token_usage.total_tokens,
            "latency_ms": response.latency_ms,
            "cost_usd": response.cost_usd,
            "success": success,
            "error": error_message,
            "correlation_id": str(settings.correlation_id) if settings.correlation_id else None
        }

        # Log structure as JSON for external observers
        logger.info(f"LLM Usage Audit: {payload}")

        # Write to ActivityEvents table for relational compliance
        event = ActivityEvent(
            user_id=settings.user_id,
            project_id=settings.project_id,
            action_name="LLM_USAGE",
            payload=payload
        )
        try:
            db.add(event)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to write usage audit event: {str(e)}")

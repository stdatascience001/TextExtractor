import asyncio
import logging
from typing import Callable, Any, Coroutine
from infrastructure.llm.exceptions import LLMRateLimitException, LLMTimeoutException, LLMException

logger = logging.getLogger("llm_orchestrator")

class RetryHandler:
    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor

    async def execute(self, func: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
        delay = self.initial_delay
        last_exception = None

        for attempt in range(1, self.max_retries + 2):
            try:
                return await func()
            except (LLMRateLimitException, LLMTimeoutException) as e:
                last_exception = e
                if attempt > self.max_retries:
                    logger.error(f"LLM request failed after {attempt - 1} retries: {str(e)}")
                    raise e
                
                logger.warning(
                    f"LLM temporary failure: {str(e)}. "
                    f"Attempt {attempt}/{self.max_retries}. Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= self.backoff_factor
            except Exception as e:
                # Direct crash on non-temporary exceptions
                logger.exception("LLM encountered fatal execution error")
                raise e

        raise last_exception if last_exception else LLMException("Retry failed unexpectedly")

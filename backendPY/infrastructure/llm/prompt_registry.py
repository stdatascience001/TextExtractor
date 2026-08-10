import logging
from typing import Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.models import PromptTemplate, PromptVersion

logger = logging.getLogger("llm_orchestrator")

class PromptRegistry:
    # Fail-safe hardcoded templates
    DEFAULT_PROMPTS: Dict[str, Tuple[str, str]] = {
        "extraction": (
            "You are an expert medical data extractor.",
            "Analyze the text: {text_input}"
        ),
        "reasoning": (
            "You are a clinical reasoning assistant. Verify the correctness of these facts.",
            "Verify: {text_input}"
        ),
        "summarization": (
            "Summarize the following findings in plain language.",
            "Text: {text_input}"
        ),
        "generation": (
            "Compile the verified medical history into a formal consultation letter.",
            "Data: {text_input}"
        )
    }

    @staticmethod
    async def get_active_prompt(db: AsyncSession, name: str) -> Tuple[str, str]:
        """
        Retrieves the active prompt templates (system and user) from the database.
        Falls back to hardcoded defaults if not found.
        """
        try:
            stmt = (
                select(PromptVersion)
                .join(PromptTemplate)
                .where(PromptTemplate.name == name, PromptVersion.is_active == True)
            )
            result = await db.execute(stmt)
            version = result.scalar_one_or_none()
            
            if version:
                return version.system_prompt, version.user_prompt_template
        except Exception as e:
            logger.error(f"Error querying prompt registry for '{name}': {str(e)}")

        # Fallback to predefined safe defaults
        logger.warning(f"Prompt '{name}' not found in DB. Falling back to default.")
        fallback = PromptRegistry.DEFAULT_PROMPTS.get(name.lower())
        if not fallback:
            return "You are an assistant.", "{text_input}"
        return fallback[0], fallback[1]

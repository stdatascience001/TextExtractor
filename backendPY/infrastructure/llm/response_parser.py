import json
import logging
from typing import Type, Any
from pydantic import BaseModel, ValidationError
from infrastructure.llm.exceptions import LLMValidationException

logger = logging.getLogger("llm_orchestrator")

class ResponseParser:
    @staticmethod
    def parse_and_validate(raw_content: str, response_model: Type[BaseModel]) -> BaseModel:
        # Strip markdown syntax if LLM returned block wraps
        cleaned_content = raw_content.strip()
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
        cleaned_content = cleaned_content.strip()

        try:
            parsed_json = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode response content as JSON: {raw_content}")
            raise LLMValidationException(f"Invalid JSON string returned from LLM: {str(e)}")

        try:
            validated_object = response_model.model_validate(parsed_json)
            return validated_object
        except ValidationError as e:
            logger.error(f"Response validation failed against schema {response_model.__name__}: {str(e)}")
            raise LLMValidationException(f"LLM output violated response schema: {str(e)}")

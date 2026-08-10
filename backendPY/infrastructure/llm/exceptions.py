class LLMException(Exception):
    """Base exception for all LLM related errors."""
    def __init__(self, message: str, provider: str = "Unknown", model: str = "Unknown"):
        self.provider = provider
        self.model = model
        super().__init__(message)

class LLMTimeoutException(LLMException):
    """Raised when the LLM provider API times out."""
    pass

class LLMRateLimitException(LLMException):
    """Raised when the LLM provider returns a rate limit (HTTP 429)."""
    pass

class LLMValidationException(LLMException):
    """Raised when response validation or JSON schema parsing fails."""
    pass

class LLMFallbackExhaustedException(LLMException):
    """Raised when all configured backup providers fail."""
    pass

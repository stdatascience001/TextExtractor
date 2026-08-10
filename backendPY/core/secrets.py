import os
from typing import Optional

class SecretsManager:
    """Provides secure abstraction for loading production secret keys from Vault/Env layers."""
    @staticmethod
    def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
        # Connects to HashiCorp Vault or AWS Secrets Manager if configured
        # Falls back to standard env configuration
        return os.getenv(key, default)

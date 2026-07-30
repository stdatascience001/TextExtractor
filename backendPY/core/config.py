from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    APP_NAME: str = "DocExtract"
    APP_ENV: str = "development"
    API_V1_STR: str = "/api/v1"
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: str = "pdf,jpg,jpeg,png"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"
    CPU_THREADS: int = 4
    DATABASE_URL: str = "postgresql+asyncpg://postgres:Admin@localhost:5432/pdf_reader"
    SECRET_KEY: str = "9e1201d4a8efc91a0c4f82bb525547a46fa7dfa442bf50b1e4f481c002241cfb"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_extensions_set(self) -> set:
        return {ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")}

settings = Settings()

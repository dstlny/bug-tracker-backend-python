import os
from pathlib import Path
from pydantic import BaseSettings
import typing
from functools import lru_cache

class Settings(BaseSettings):

    DATABASE_NAME: str
    DATABASE_TORTOISE_BACKEND: str
    DATABASE_HOST: str
    DATABASE_PASSWORD: str
    DATABASE_PORT: int | None = 5432
    DATABASE_USER: str
    DATABASE_URL: str | None = None
    FRONTEND_ADDRESS: str | None = '127.0.0.1'
    ENV_ORIGINS: str | None = "127.0.0.1"
    REDIS_URL: str | None = 'redis://localhost'
    REDIS_ENABLED: bool = False
    STORAGE_ENABLED: bool = True
    DOCUMENT_DIRECTORY: Path = Path('documents')

    class Config:
        env_prefix = ""
        case_sentive = False
        env_file = '.env'
        secrets_dir = "../"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings():
    return Settings()

settings: Settings = get_settings()

if not settings.DOCUMENT_DIRECTORY.exists():
    settings.DOCUMENT_DIRECTORY.mkdir()
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "LearnMate"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/learnmate.log"
    LOG_MAX_BYTES: int = 5 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 3

    LLM_PROVIDER: str = Field(default="openai", alias="LLM_PROVIDER")
    LLM_MODEL: str = Field(default="gpt-5.4-mini", alias="LLM_MODEL")
    OPENAI_API_KEY: str | None = Field(default=None, alias="OPENAI_API_KEY")

    S3_ACCESS_KEY_ID: str | None = Field(default=None, alias="S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY: str | None = Field(default=None, alias="S3_SECRET_ACCESS_KEY")
    S3_ENDPOINT_URL: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    STORAGE_BUCKET_NAME: str | None = Field(default=None, alias="STORAGE_BUCKET_NAME")
    QUERYSTRING_EXPIRE: int = Field(default=3600, alias="QUERYSTRING_EXPIRE")
    S3_USE_PATH_STYLE: bool = Field(default=True, alias="S3_USE_PATH_STYLE")

    DB_NAME: str = Field(default="learnmate", alias="DB_NAME")
    DB_USER: str = Field(default="learnmate", alias="DB_USER")
    DB_PASSWORD: str = Field(default="learnmate", alias="DB_PASSWORD")
    DB_HOST: str = Field(default="localhost", alias="DB_HOST")
    DB_PORT: int = Field(default=5432, alias="DB_PORT")

    @property
    def database_url(self) -> str:
        return str(
            URL.create(
                drivername="postgresql+asyncpg",
                username=self.DB_USER,
                password=self.DB_PASSWORD,
                host=self.DB_HOST,
                port=self.DB_PORT,
                database=self.DB_NAME,
            )
        )

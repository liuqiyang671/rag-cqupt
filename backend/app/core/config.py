from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:password@localhost:5432/campus_qa",
        alias="DATABASE_URL",
    )

    model_provider: str = Field(default="local", alias="MODEL_PROVIDER")
    local_llm_base_url: str = Field(default="http://localhost:11434", alias="LOCAL_LLM_BASE_URL")
    local_llm_model: str = Field(default="qwen2.5:7b", alias="LOCAL_LLM_MODEL")

    siliconflow_api_key: str = Field(default="", alias="SILICONFLOW_API_KEY")
    siliconflow_base_url: str = Field(default="https://api.siliconflow.cn/v1", alias="SILICONFLOW_BASE_URL")
    siliconflow_chat_model: str = Field(default="Qwen/Qwen2.5-7B-Instruct", alias="SILICONFLOW_CHAT_MODEL")
    siliconflow_embedding_model: str = Field(default="BAAI/bge-m3", alias="SILICONFLOW_EMBEDDING_MODEL")

    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")
    local_embedding_base_url: str = Field(default="http://localhost:11434", alias="LOCAL_EMBEDDING_BASE_URL")
    local_embedding_model: str = Field(default="qwen3-embedding:8b-fp16", alias="LOCAL_EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=4096, alias="EMBEDDING_DIMENSION")
    top_k: int = Field(default=5, alias="TOP_K")
    upload_dir: str = Field(default="", alias="UPLOAD_DIR")

    secret_key: str = Field(default="campus-qa-secret-change-in-production", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    frontend_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="FRONTEND_ORIGINS",
    )

    # 问题重写配置
    enable_query_rewriting: bool = Field(default=True, alias="ENABLE_QUERY_REWRITING")
    query_rewriting_max_queries: int = Field(default=3, alias="QUERY_REWRITING_MAX_QUERIES")

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def upload_dir_path(self) -> Path:
        if self.upload_dir:
            configured = Path(self.upload_dir)
            return configured if configured.is_absolute() else (Path.cwd() / configured).resolve()
        return Path(__file__).resolve().parents[2] / "uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()

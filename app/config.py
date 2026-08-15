from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CHROMA_DIR = str(Path(__file__).resolve().parent.parent / "chroma_data")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    openai_api_key: str
    chroma_persist_dir: str = DEFAULT_CHROMA_DIR
    test_database_url: str | None = None

    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "ledger-task-api"


settings = Settings()

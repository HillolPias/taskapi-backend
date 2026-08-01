from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    openai_api_key: str

    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "ledger-task-api"


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Competa"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite+aiosqlite:///./competa.db"
    LLM_MODE: str = "auto"  # "mock", "real", or "auto" (real if API key present)
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_RETRIES: int = 2

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Competa"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite+aiosqlite:///./competa.db"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

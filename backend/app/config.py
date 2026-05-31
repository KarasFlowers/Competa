from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Competa"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite+aiosqlite:///./competa.db"
    LLM_API_KEY: str = ""
    LLM_API_KEY_2: str = ""
    LLM_API_KEY_3: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""
    LLM_MOCK: bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Search provider: "tavily" | "ddgs" | "none"
    SEARCH_PROVIDER: str = "none"
    TAVILY_API_KEY: str = ""
    SEARCH_MAX_RESULTS: int = 10
    SEARCH_FETCH_CONTENT: bool = True

    @property
    def llm_api_keys(self) -> list[str]:
        """Return all non-empty API keys in priority order."""
        keys = [self.LLM_API_KEY, self.LLM_API_KEY_2, self.LLM_API_KEY_3]
        return [k for k in keys if k.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

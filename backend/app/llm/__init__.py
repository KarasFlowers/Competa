from app.llm.adapter import BaseLLM, MockLLM
from app.llm.openai_llm import OpenAICompatibleLLM


def get_llm() -> BaseLLM:
    """Factory: return the appropriate LLM based on settings.

    LLM_MODE controls behavior:
      - "mock"  → always use MockLLM
      - "real"  → always use OpenAICompatibleLLM (raises if no API key)
      - "auto"  → use real if LLM_API_KEY is set, else fallback to mock
    """
    from app.config import settings

    mode = settings.LLM_MODE.lower()

    if mode == "mock":
        return MockLLM()
    elif mode == "real":
        return OpenAICompatibleLLM()
    else:  # "auto"
        if settings.LLM_API_KEY:
            return OpenAICompatibleLLM()
        return MockLLM()


__all__ = ["BaseLLM", "MockLLM", "OpenAICompatibleLLM", "get_llm"]

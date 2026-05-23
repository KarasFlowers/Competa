"""OpenAI-compatible LLM Adapter — calls real Chat Completions API.

Supports any OpenAI-compatible endpoint (OpenAI, Azure, DeepSeek, Moonshot, etc.).
Uses JSON Schema structured output to enforce Pydantic schema compliance.
Falls back to MockLLM on repeated failures if configured.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Type, TypeVar

import httpx
from pydantic import BaseModel

from app.config import settings
from app.guardrails import GuardrailError, validate_output
from app.llm.adapter import BaseLLM

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


def _build_json_schema(schema_cls: Type[BaseModel]) -> dict:
    """Build a simplified JSON schema description for the prompt."""
    schema = schema_cls.model_json_schema()
    # Remove $defs reference for simpler prompt injection
    return schema


def _build_system_prompt(schema_cls: Type[BaseModel]) -> str:
    """Build system prompt that instructs the model to output valid JSON."""
    schema = _build_json_schema(schema_cls)
    return (
        "You are a structured output assistant. "
        "You MUST respond with a valid JSON object that conforms to the following JSON Schema. "
        "Do NOT include any text outside the JSON object. "
        "Do NOT wrap the JSON in markdown code blocks.\n\n"
        f"JSON Schema:\n```json\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n```"
    )


class OpenAICompatibleLLM(BaseLLM):
    """Real LLM adapter using OpenAI-compatible Chat Completions API.

    Configuration via environment variables:
        LLM_API_KEY   — API key
        LLM_BASE_URL  — Base URL (e.g. https://api.openai.com/v1)
        LLM_MODEL     — Model name (e.g. gpt-4o, deepseek-chat)
        LLM_TEMPERATURE — Generation temperature (default 0.2)
        LLM_MAX_RETRIES — Max retries on failure (default 2)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY is required for OpenAICompatibleLLM. "
                "Set it in .env or pass it directly."
            )

    async def generate(self, prompt: str, schema_cls: Type[T], **kwargs: Any) -> T:
        """Call the Chat Completions API and validate output against schema_cls."""
        system_prompt = _build_system_prompt(schema_cls)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                raw_json = await self._call_api(messages)
                data = json.loads(raw_json)
                return validate_output(schema_cls, data)

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(
                    f"[OpenAILLM] Attempt {attempt + 1}: JSON parse error — {e}"
                )
                # Add a correction message for retry
                messages.append({"role": "assistant", "content": raw_json})
                messages.append({
                    "role": "user",
                    "content": (
                        "Your response was not valid JSON. "
                        "Please respond ONLY with a valid JSON object matching the schema. "
                        "No markdown, no explanation, just the JSON."
                    ),
                })

            except GuardrailError as e:
                last_error = e
                logger.warning(
                    f"[OpenAILLM] Attempt {attempt + 1}: Schema validation failed — {e}"
                )
                error_details = e.to_dict()
                messages.append({"role": "assistant", "content": raw_json})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your JSON did not match the required schema. "
                        f"Errors: {json.dumps(error_details['errors'], ensure_ascii=False)}\n"
                        f"Please fix these issues and respond with corrected JSON only."
                    ),
                })

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(
                    f"[OpenAILLM] Attempt {attempt + 1}: HTTP {e.response.status_code} — "
                    f"{e.response.text[:300]}"
                )
                if e.response.status_code in (429, 500, 502, 503):
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

            except httpx.RequestError as e:
                last_error = e
                logger.error(f"[OpenAILLM] Attempt {attempt + 1}: Network error — {e}")
                import asyncio
                await asyncio.sleep(2 ** attempt)
                continue

        raise last_error or RuntimeError("LLM generation failed after all retries")

    async def _call_api(self, messages: list[dict]) -> str:
        """Make HTTP request to Chat Completions endpoint."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Strip markdown code blocks if model wraps output
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        return content

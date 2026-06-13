"""Base class for all Agents — handles LLM call, JSON parse, Guardrail validation, and retry."""

from __future__ import annotations

import json
import logging
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from app.guardrails.validator import GuardrailError, validate_output
from app.llm.client import LLMContentFilterError, LLMResponse, call_llm
from app.llm.prompts import language_directive
from app.schemas.trace import EventType, TraceEvent

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class BaseAgent:
    """Abstract base for all pipeline agents."""

    name: str = "base"
    system_prompt: str = ""
    max_retries: int = 3

    async def run(self, input_data: Any) -> dict:
        """Override in subclass. Should return a dict to merge into PipelineState."""
        raise NotImplementedError

    async def call_and_validate(
        self,
        user_prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        output_language: str = "zh",
    ) -> tuple[T, LLMResponse, list[TraceEvent]]:
        """Call LLM, parse JSON, validate against schema, retry on failure.

        Returns:
            (validated_output, llm_response, trace_events)
        """
        sys_prompt = system_prompt or self.system_prompt
        sys_prompt = f"{sys_prompt}\n\n{language_directive(output_language)}"
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]

        traces: list[TraceEvent] = []
        last_error: Exception | None = None
        attempts_used = 0
        current_max_tokens = max_tokens

        for attempt in range(1, self.max_retries + 1):
            attempts_used = attempt
            llm_resp = None
            traces.append(TraceEvent(
                agent_name=self.name,
                event_type=EventType.START,
                input_summary=f"attempt {attempt}/{self.max_retries}",
                prompt=user_prompt,
                retry_attempt=attempt,
            ))

            try:
                llm_resp = await call_llm(messages, max_tokens=current_max_tokens)

                # Parse JSON from LLM response
                content = llm_resp.content.strip()
                # Handle markdown code blocks (```json ... ``` or ``` ... ```)
                if content.startswith("```"):
                    first_newline = content.index("\n") if "\n" in content else len(content)
                    content = content[first_newline + 1:]
                    if content.rstrip().endswith("```"):
                        content = content.rstrip()[:-3]

                parsed = json.loads(content)
                validated = validate_output(output_schema, parsed)

                traces.append(TraceEvent(
                    agent_name=self.name,
                    event_type=EventType.OUTPUT,
                    output_summary=f"validated {output_schema.__name__}",
                    token_count=llm_resp.input_tokens + llm_resp.output_tokens,
                    duration=llm_resp.duration,
                    output_data={"schema": output_schema.__name__, "keys": list(parsed.keys()) if isinstance(parsed, dict) else []},
                    retry_attempt=attempt,
                ))

                return validated, llm_resp, traces

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(
                    "%s: JSON parse failed (attempt %d, max_tokens=%d): %s",
                    self.name, attempt, current_max_tokens, e,
                )
                traces.append(TraceEvent(
                    agent_name=self.name,
                    event_type=EventType.ERROR,
                    error_message=f"JSON parse error: {e}",
                    duration=llm_resp.duration if llm_resp else None,
                    retry_attempt=attempt,
                ))
                # Detect truncation: if output tokens hit the limit or the
                # error looks like an unterminated string, bump max_tokens.
                is_truncated = (
                    ("Unterminated string" in str(e))
                    or (llm_resp is not None and llm_resp.output_tokens >= current_max_tokens * 0.9)
                )
                if is_truncated and current_max_tokens < 32768:
                    current_max_tokens = min(current_max_tokens * 2, 65536)
                    logger.info(
                        "%s: output appears truncated, increasing max_tokens to %d for retry",
                        self.name, current_max_tokens,
                    )
                # Keep conversation lean: only include a short excerpt of the
                # failed response so retries don't bloat the input context.
                failed_content = llm_resp.content if llm_resp else ""

                excerpt = (failed_content[:200] + "\n...\n[truncated — JSON parse error]") if len(failed_content) > 300 else failed_content
                messages.append({"role": "assistant", "content": excerpt})
                hint = (
                    "Your response was not valid JSON. Error: {e}. "
                    "Please output valid JSON. If the output is very large, "
                    "prioritise conciseness — shorten descriptions and keep only "
                    "the most important data."
                ).format(e=e)
                messages.append({"role": "user", "content": hint})

            except GuardrailError as e:
                last_error = e
                logger.warning(
                    "%s: Guardrail failed (attempt %d): %s", self.name, attempt, e
                )
                traces.append(TraceEvent(
                    agent_name=self.name,
                    event_type=EventType.ERROR,
                    error_message=f"Guardrail: {e}",
                    duration=llm_resp.duration,
                    retry_attempt=attempt,
                ))
                error_details = e.to_dict()
                messages.append({"role": "assistant", "content": llm_resp.content})
                messages.append({
                    "role": "user",
                    "content": f"Your output failed schema validation:\n"
                    f"{json.dumps(error_details, indent=2)}\n"
                    f"Please fix the issues and output valid JSON.",
                })

            except LLMContentFilterError as e:
                last_error = e
                logger.warning(
                    "%s: Request blocked by provider safety policy (attempt %d): %s",
                    self.name,
                    attempt,
                    e,
                )
                traces.append(TraceEvent(
                    agent_name=self.name,
                    event_type=EventType.ERROR,
                    error_message=f"Provider blocked request: {e}",
                    retry_attempt=attempt,
                ))
                break

            except Exception as e:
                last_error = e
                logger.error("%s: Unexpected error (attempt %d): %s", self.name, attempt, e)
                traces.append(TraceEvent(
                    agent_name=self.name,
                    event_type=EventType.ERROR,
                    error_message=str(e),
                    retry_attempt=attempt,
                ))
                # Non-retryable: break instead of retrying with same input
                break

        if isinstance(last_error, LLMContentFilterError):
            failure_message = (
                f"Request blocked by the model provider after {attempts_used} "
                f"attempt(s). Last error: {last_error}"
            )
        elif attempts_used >= self.max_retries:
            failure_message = (
                f"All {self.max_retries} attempts failed. Last error: {last_error}"
            )
        else:
            failure_message = (
                f"Stopped after {attempts_used} attempt(s). Last error: {last_error}"
            )

        traces.append(TraceEvent(
            agent_name=self.name,
            event_type=EventType.END,
            error_message=failure_message,
        ))
        raise RuntimeError(f"{self.name}: {failure_message}") from last_error

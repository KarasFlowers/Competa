"""Base class for all Agents — handles LLM call, JSON parse, Guardrail validation, and retry."""

from __future__ import annotations

import json
import logging
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from app.guardrails.validator import GuardrailError, validate_output
from app.llm.client import LLMContentFilterError, LLMResponse, call_llm
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
    ) -> tuple[T, LLMResponse, list[TraceEvent]]:
        """Call LLM, parse JSON, validate against schema, retry on failure.

        Returns:
            (validated_output, llm_response, trace_events)
        """
        sys_prompt = system_prompt or self.system_prompt
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]

        traces: list[TraceEvent] = []
        last_error: Exception | None = None
        attempts_used = 0

        for attempt in range(1, self.max_retries + 1):
            attempts_used = attempt
            traces.append(TraceEvent(
                agent_name=self.name,
                event_type=EventType.START,
                input_summary=f"attempt {attempt}/{self.max_retries}",
                prompt=user_prompt,
                retry_attempt=attempt,
            ))

            try:
                llm_resp = await call_llm(messages)

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
                    "%s: JSON parse failed (attempt %d): %s", self.name, attempt, e
                )
                traces.append(TraceEvent(
                    agent_name=self.name,
                    event_type=EventType.ERROR,
                    error_message=f"JSON parse error: {e}",
                    duration=llm_resp.duration,
                    retry_attempt=attempt,
                ))
                # Add error feedback to messages for retry
                messages.append({"role": "assistant", "content": llm_resp.content})
                messages.append({
                    "role": "user",
                    "content": f"Your response was not valid JSON. Error: {e}. "
                    f"Please output valid JSON matching the required schema.",
                })

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

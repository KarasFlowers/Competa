"""Agent base class — inspired by CrewAI Agent(role, goal, backstory)
and OpenAI Agents SDK Tracing.

Template method pattern: run() orchestrates prompt building, LLM call,
guardrails validation, and automatic trace recording.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from app.llm.adapter import BaseLLM
from app.schemas.trace import AgentTrace, TraceEvent, EventType, TraceStatus

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """Base class for all Competa agents.

    Attributes:
        name: unique agent identifier (e.g. "collector")
        role: agent's role title (参考 CrewAI)
        goal: what this agent aims to achieve
        backstory: additional context injected into prompts
        llm: the LLM adapter to use for generation
    """

    name: str = ""
    role: str = ""
    goal: str = ""
    backstory: str = ""

    def __init__(self, llm: BaseLLM) -> None:
        self.llm = llm

    @abstractmethod
    def _get_output_schema(self) -> Type[BaseModel]:
        """Return the Pydantic schema class for this agent's output."""

    @abstractmethod
    def _build_prompt(self, state: dict[str, Any]) -> str:
        """Build the prompt string from current graph state."""

    @abstractmethod
    def _extract_state_updates(self, output: BaseModel, state: dict[str, Any]) -> dict[str, Any]:
        """Extract state update dict from the validated output."""

    def _get_llm_kwargs(self, state: dict[str, Any]) -> dict[str, Any]:
        """Extra kwargs passed to llm.generate(). Override in subclasses."""
        return {}

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Template method — orchestrates prompt → LLM → guardrails → trace.

        Returns a dict of state field updates to merge into GraphState.
        """
        trace = AgentTrace(agent_name=self.name, task_id=state.get("task_id", ""))
        trace.events.append(TraceEvent(
            agent_name=self.name,
            event_type=EventType.START,
            input_summary=self._summarize_input(state),
        ))

        t0 = time.monotonic()
        try:
            prompt = self._build_prompt(state)
            schema_cls = self._get_output_schema()
            llm_kwargs = self._get_llm_kwargs(state)
            output = await self.llm.generate(prompt, schema_cls, **llm_kwargs)

            elapsed = time.monotonic() - t0
            trace.events.append(TraceEvent(
                agent_name=self.name,
                event_type=EventType.OUTPUT,
                output_summary=str(output.model_dump())[:500],
                token_count=self._estimate_tokens(prompt),
            ))
            trace.events.append(TraceEvent(
                agent_name=self.name,
                event_type=EventType.END,
            ))
            trace.total_duration = round(elapsed, 4)
            trace.total_tokens = self._estimate_tokens(prompt)
            trace.status = TraceStatus.COMPLETED

            updates = self._extract_state_updates(output, state)
            updates["traces"] = state.get("traces", []) + [trace]
            return updates

        except Exception as exc:
            elapsed = time.monotonic() - t0
            trace.events.append(TraceEvent(
                agent_name=self.name,
                event_type=EventType.ERROR,
                error_message=str(exc)[:300],
            ))
            trace.total_duration = round(elapsed, 4)
            trace.status = TraceStatus.FAILED

            return {
                "traces": state.get("traces", []) + [trace],
            }

    def _build_role_context(self) -> str:
        """Build role context string for prompt injection."""
        parts = []
        if self.role:
            parts.append(f"Role: {self.role}")
        if self.goal:
            parts.append(f"Goal: {self.goal}")
        if self.backstory:
            parts.append(f"Background: {self.backstory}")
        return "\n".join(parts)

    def _build_constraints_context(self, state: dict[str, Any]) -> str:
        """Build constraints context from accumulated ratchet rules.

        Produces actionable natural language instructions that downstream
        agents can directly follow.
        """
        constraints = state.get("constraints", [])
        if not constraints:
            return ""

        # Filter constraints relevant to this agent
        relevant = []
        for c in constraints:
            if isinstance(c, dict):
                applied_to = c.get("applied_to", "")
                constraint_value = c.get("constraint_value", "")
                constraint_type = c.get("constraint_type", "")
            elif hasattr(c, "applied_to"):
                applied_to = c.applied_to
                constraint_value = c.constraint_value
                constraint_type = c.constraint_type
            else:
                continue

            # Include if targeted at this agent or at all agents
            if applied_to in (self.name, "all", ""):
                relevant.append((constraint_type, constraint_value))

        if not relevant:
            # Show all constraints if none specifically targeted
            for c in constraints:
                if isinstance(c, dict):
                    relevant.append((c.get("constraint_type", ""), c.get("constraint_value", "")))
                elif hasattr(c, "constraint_type"):
                    relevant.append((c.constraint_type, c.constraint_value))

        if not relevant:
            return ""

        lines = [
            "⚠️ 上次提交被 QA 打回，你必须修正以下问题：",
            "",
        ]
        for i, (ctype, cvalue) in enumerate(relevant, 1):
            lines.append(f"  {i}. [{ctype}] {cvalue}")

        lines.append("")
        lines.append("请确保本次输出已解决以上所有问题。")

        return "\n".join(lines)

    def _summarize_input(self, state: dict[str, Any]) -> str:
        """Create a short summary of the input state for tracing."""
        keys = [k for k in state if state[k] is not None and k != "traces"]
        return f"state keys: {', '.join(keys)}"

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate (~4 chars per token)."""
        return len(text) // 4

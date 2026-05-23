from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RoleType(str, Enum):
    COLLECTOR = "collector"
    ANALYST = "analyst"
    WRITER = "writer"
    QA = "qa"


class AgentRole(BaseModel):
    name: str
    role_type: RoleType
    description: str = ""
    input_schema: str = ""
    output_schema: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    max_retries: int = 3


class AgentRegistry(BaseModel):
    roles: dict[str, AgentRole] = Field(default_factory=dict)

    def register(self, role: AgentRole) -> None:
        self.roles[role.name] = role

    def lookup(self, name: str) -> AgentRole | None:
        return self.roles.get(name)

    def validate_name(self, name: str) -> bool:
        return name in self.roles


# Default registry with the 4 core agents
default_registry = AgentRegistry()
default_registry.register(
    AgentRole(
        name="collector",
        role_type=RoleType.COLLECTOR,
        description="Gathers competitive intelligence from public sources, surveys, and interviews.",
        input_schema="CollectRequest",
        output_schema="CollectResult",
    )
)
default_registry.register(
    AgentRole(
        name="analyst",
        role_type=RoleType.ANALYST,
        description="Extracts feature trees, pricing models, personas, and SWOT from collected data.",
        input_schema="AnalyzeRequest",
        output_schema="AnalyzeResult",
    )
)
default_registry.register(
    AgentRole(
        name="writer",
        role_type=RoleType.WRITER,
        description="Generates structured competitive analysis reports with citations.",
        input_schema="WriteRequest",
        output_schema="WriteResult",
    )
)
default_registry.register(
    AgentRole(
        name="qa",
        role_type=RoleType.QA,
        description="Validates report completeness, evidence coverage, and schema compliance.",
        input_schema="Report",
        output_schema="QAFeedback",
    )
)

from __future__ import annotations

import logging
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class FieldError(BaseModel):
    field_path: str
    error_type: str
    message: str
    suggestion: str = ""


class GuardrailError(Exception):
    """Raised when Agent output fails Schema validation."""

    def __init__(self, schema_name: str, errors: list[FieldError]):
        self.schema_name = schema_name
        self.errors = errors
        msg = f"Guardrail validation failed for {schema_name}: {len(errors)} error(s)"
        super().__init__(msg)

    def to_dict(self) -> dict:
        return {
            "schema_name": self.schema_name,
            "error_count": len(self.errors),
            "errors": [e.model_dump() for e in self.errors],
        }


def _parse_validation_error(ve: ValidationError) -> list[FieldError]:
    """Convert Pydantic ValidationError to structured FieldError list."""
    field_errors: list[FieldError] = []
    for err in ve.errors():
        loc_parts = [str(p) for p in err.get("loc", [])]
        field_path = ".".join(loc_parts) if loc_parts else "<root>"
        error_type = err.get("type", "unknown")
        message = err.get("msg", "")

        suggestion = ""
        if "missing" in error_type:
            suggestion = f"Provide a value for '{field_path}'."
        elif "type" in error_type:
            suggestion = f"Check the type of '{field_path}' — expected type indicated in error."
        elif "value" in error_type:
            suggestion = f"Adjust the value of '{field_path}' to meet the constraint."

        field_errors.append(
            FieldError(
                field_path=field_path,
                error_type=error_type,
                message=message,
                suggestion=suggestion,
            )
        )
    return field_errors


def validate_output(schema_cls: Type[T], data: Any) -> T:
    """Validate data against a Pydantic schema.

    Returns the validated model instance on success.
    Raises GuardrailError with structured field errors on failure.
    """
    try:
        if isinstance(data, dict):
            return schema_cls.model_validate(data)
        elif isinstance(data, str):
            return schema_cls.model_validate_json(data)
        elif isinstance(data, schema_cls):
            return data
        else:
            return schema_cls.model_validate(data)
    except ValidationError as ve:
        errors = _parse_validation_error(ve)
        for e in errors:
            logger.warning(
                "Guardrail failed: schema=%s field=%s type=%s msg=%s",
                schema_cls.__name__, e.field_path, e.error_type, e.message,
            )
        raise GuardrailError(schema_name=schema_cls.__name__, errors=errors) from ve

"""L4 Governance — Schema validation, audit logging, permission guard, and secret redaction.

Re-exports:
  - validate_output, GuardrailError, FieldError: Pydantic schema validation
  - validate_report_completeness: Report completeness hard validation
  - redact_secrets, safe_error_message: Secret redaction for logs/errors
"""
from app.guardrails.validator import validate_output, GuardrailError, FieldError
from app.guardrails.report_validator import validate_report_completeness
from app.guardrails.redact import redact_secrets, safe_error_message

__all__ = [
    "validate_output",
    "GuardrailError",
    "FieldError",
    "validate_report_completeness",
    "redact_secrets",
    "safe_error_message",
]

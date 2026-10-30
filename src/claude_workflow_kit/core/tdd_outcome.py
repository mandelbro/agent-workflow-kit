"""Outcome contract for headless `/tdd-pair auto --headless` runs.

The skill ends a headless run with a fenced JSON block. The model that wrote it is not a
trusted authority: consumers must treat the outcome as advisory, validate it against this
schema, fail closed on anything invalid, and take state transitions from deterministic checks.
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SCHEMA_VERSION = 1

ShortText = Annotated[str, Field(max_length=200)]
LongText = Annotated[str, Field(max_length=2000)]

_FENCED_JSON = re.compile(r"```json[ \t]*\n(.*?)\n[ \t]*```", re.DOTALL)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BatchOutcome(_Strict):
    """Final state of one test batch."""

    id: Annotated[int, Field(ge=1)]
    name: ShortText
    status: Literal["pending", "in_progress", "completed", "blocked"]
    phase: Literal["red", "green", "refactor", "done"]
    review_rounds: Annotated[int, Field(ge=0, le=10)]
    tests: Annotated[int, Field(ge=0)]


class FailingCheck(_Strict):
    """A deterministic check (test, lint, typecheck) that was failing when the run stopped."""

    name: ShortText
    command: ShortText
    summary: LongText


class OpenFinding(_Strict):
    """An unresolved reviewer finding or non-blocking concern."""

    batch_id: Annotated[int, Field(ge=1)] | None = None
    phase: Literal["plan", "red", "green", "refactor"]
    severity: Literal["critical", "major", "minor", "nit", "concern"]
    summary: LongText


class TddOutcome(_Strict):
    """Structured result of a headless tdd-pair run."""

    schema_version: Literal[1] = SCHEMA_VERSION
    status: Literal["done", "blocked", "needs_info"]
    spec_path: ShortText
    base_branch: ShortText | None = None
    base_warning: LongText | None = None
    batches: list[BatchOutcome] = Field(default_factory=lambda: [], max_length=200)
    failing_checks: list[FailingCheck] = Field(default_factory=lambda: [], max_length=50)
    open_findings: list[OpenFinding] = Field(default_factory=lambda: [], max_length=200)
    blocked_reason: LongText | None = None
    spec_gaps: list[LongText] = Field(default_factory=lambda: [], max_length=50)

    @model_validator(mode="after")
    def _check_status_consistency(self) -> TddOutcome:
        if self.status == "done":
            if not self.batches:
                raise ValueError("status 'done' requires at least one entry in batches")
            if any(b.status != "completed" for b in self.batches):
                raise ValueError("status 'done' requires every batch to be completed")
            if self.failing_checks:
                raise ValueError("status 'done' cannot report failing_checks")
        elif self.status == "blocked" and not self.blocked_reason:
            raise ValueError("status 'blocked' requires blocked_reason")
        elif self.status == "needs_info" and not self.spec_gaps:
            raise ValueError("status 'needs_info' requires spec_gaps")
        return self


class OutcomeParseError(ValueError):
    """The run's final message did not contain a valid outcome. Treat the run as failed."""


def parse_outcome(text: str) -> TddOutcome:
    """Extract and validate the last fenced JSON block in a run's final message."""
    blocks = _FENCED_JSON.findall(text)
    if not blocks:
        raise OutcomeParseError("no fenced ```json outcome block found")
    try:
        payload = json.loads(blocks[-1])
    except json.JSONDecodeError as exc:
        raise OutcomeParseError(f"outcome block is not valid JSON: {exc}") from exc
    try:
        return TddOutcome.model_validate(payload)
    except ValidationError as exc:
        raise OutcomeParseError(f"outcome block violates the schema: {exc}") from exc

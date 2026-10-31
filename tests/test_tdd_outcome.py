"""Tests for the tdd-pair headless outcome contract (advisory, schema-validated)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from claude_workflow_kit.core.registry import get_assets_dir
from claude_workflow_kit.core.tdd_outcome import (
    OutcomeParseError,
    TddOutcome,
    parse_outcome,
)


def _batch(**overrides: Any) -> dict[str, Any]:
    batch: dict[str, Any] = {
        "id": 1,
        "name": "Capacity and consumption",
        "status": "completed",
        "phase": "done",
        "review_rounds": 1,
        "tests": 3,
    }
    return {**batch, **overrides}


def _outcome(**overrides: Any) -> dict[str, Any]:
    outcome: dict[str, Any] = {
        "schema_version": 1,
        "status": "done",
        "spec_path": "specs/rate-limiter.md",
        "batches": [_batch()],
    }
    return {**outcome, **overrides}


def _fenced(payload: dict[str, Any]) -> str:
    return f"Summary of the run.\n\n```json\n{json.dumps(payload)}\n```\n"


class TestShape:
    def test_minimal_done_outcome_validates(self) -> None:
        outcome = TddOutcome.model_validate(_outcome())
        assert outcome.status == "done"
        assert outcome.failing_checks == []
        assert outcome.open_findings == []

    def test_unknown_field_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TddOutcome.model_validate(_outcome(committed=True))

    def test_unknown_status_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TddOutcome.model_validate(_outcome(status="rate_limited"))

    def test_wrong_schema_version_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TddOutcome.model_validate(_outcome(schema_version=2))

    def test_unknown_batch_phase_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TddOutcome.model_validate(_outcome(batches=[_batch(phase="deploy")]))

    def test_oversized_text_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TddOutcome.model_validate(_outcome(status="blocked", blocked_reason="x" * 5000))

    def test_too_many_batches_is_rejected(self) -> None:
        batches = [_batch(id=i) for i in range(1, 202)]
        with pytest.raises(ValidationError):
            TddOutcome.model_validate(_outcome(batches=batches))


class TestInternalConsistency:
    """A self-contradictory outcome must not validate, even though it is only advisory."""

    def test_done_with_incomplete_batch_is_rejected(self) -> None:
        batches = [_batch(), _batch(id=2, status="pending", phase="red")]
        with pytest.raises(ValidationError, match="done"):
            TddOutcome.model_validate(_outcome(batches=batches))

    def test_done_with_failing_checks_is_rejected(self) -> None:
        failing = [{"name": "pytest", "command": "just test", "summary": "2 failed"}]
        with pytest.raises(ValidationError, match="failing"):
            TddOutcome.model_validate(_outcome(failing_checks=failing))

    def test_done_with_no_batches_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="batches"):
            TddOutcome.model_validate(_outcome(batches=[]))

    def test_blocked_requires_reason(self) -> None:
        batches = [_batch(status="blocked", phase="red", review_rounds=3)]
        with pytest.raises(ValidationError, match="blocked_reason"):
            TddOutcome.model_validate(_outcome(status="blocked", batches=batches))

    def test_blocked_with_reason_and_findings_validates(self) -> None:
        batches = [_batch(status="blocked", phase="red", review_rounds=3)]
        finding = {
            "batch_id": 1,
            "phase": "red",
            "severity": "major",
            "summary": "Spec does not say whether refill is continuous.",
        }
        outcome = TddOutcome.model_validate(
            _outcome(
                status="blocked",
                batches=batches,
                blocked_reason="Three review rounds exhausted on batch 1.",
                open_findings=[finding],
            )
        )
        assert outcome.open_findings[0].severity == "major"

    def test_needs_info_requires_spec_gaps(self) -> None:
        with pytest.raises(ValidationError, match="spec_gaps"):
            TddOutcome.model_validate(_outcome(status="needs_info", batches=[]))

    def test_needs_info_with_gaps_and_no_batches_validates(self) -> None:
        outcome = TddOutcome.model_validate(
            _outcome(status="needs_info", batches=[], spec_gaps=["No Test Plan section."])
        )
        assert outcome.spec_gaps == ["No Test Plan section."]


class TestParseOutcome:
    def test_extracts_the_last_fenced_json_block(self) -> None:
        first = _outcome(spec_path="specs/old.md")
        text = _fenced(first) + "\nCorrection:\n" + _fenced(_outcome())
        assert parse_outcome(text).spec_path == "specs/rate-limiter.md"

    def test_missing_block_fails_closed(self) -> None:
        with pytest.raises(OutcomeParseError, match="no fenced"):
            parse_outcome("All done, everything passed!")

    def test_malformed_json_fails_closed(self) -> None:
        with pytest.raises(OutcomeParseError, match="JSON"):
            parse_outcome('```json\n{"status": "done",}\n```')

    def test_schema_violation_fails_closed(self) -> None:
        with pytest.raises(OutcomeParseError, match="schema"):
            parse_outcome(_fenced(_outcome(status="victory")))


class TestShippedSchema:
    def test_packaged_schema_matches_the_model(self) -> None:
        packaged = get_assets_dir() / "skills" / "tdd-pair" / "outcome.schema.json"
        assert json.loads(packaged.read_text()) == TddOutcome.model_json_schema()

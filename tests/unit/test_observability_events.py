"""Testes dos contratos de eventos operacionais."""

import json
import math
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from credit_risk_monitoring.observability.events import (
    finish_event,
    start_event,
)


def completed_event(**overrides):
    initial = start_event(
        batch_id="test-control",
        pipeline="monitoring",
        scenario_id="control",
    )

    values = {
        "finished_at": initial.started_at + timedelta(seconds=2),
        "duration_seconds": 2.0,
        "execution_status": "completed",
        "quality_status": "approved",
        "drift_status": "not_detected",
        "exit_code": 0,
        "total_rows": 100,
        "scored_rows": 100,
        "features_analyzed": 16,
        "features_drifted": 0,
        "drift_share": 0.0,
        "quality_violations": 0,
    }
    values.update(overrides)
    return finish_event(initial, **values)


def test_initial_event_is_running():
    event = start_event("batch-001", "monitoring", "control")

    assert event.execution_status == "running"
    assert event.exit_code is None
    assert event.finished_at is None
    assert event.started_at.tzinfo == timezone.utc


def test_successful_monitoring_event():
    event = completed_event()

    assert event.execution_status == "completed"
    assert event.quality_status == "approved"
    assert event.drift_status == "not_detected"
    assert event.exit_code == 0


def test_strong_drift_is_not_operational_failure():
    event = completed_event(
        drift_status="detected",
        features_drifted=2,
        drift_share=0.125,
    )

    assert event.exit_code == 0
    assert event.execution_status == "completed"
    assert event.drift_status == "detected"


def test_quality_rejection_does_not_score():
    event = completed_event(
        quality_status="rejected",
        drift_status="not_evaluated",
        exit_code=2,
        scored_rows=0,
        features_analyzed=None,
        features_drifted=None,
        drift_share=None,
        quality_violations=3,
    )

    assert event.exit_code == 2
    assert event.scored_rows == 0
    assert event.drift_status == "not_evaluated"


def test_operational_failure_before_data_read():
    initial = start_event("batch-error", "monitoring", "external")

    event = finish_event(
        initial,
        finished_at=initial.started_at + timedelta(seconds=1),
        duration_seconds=1.0,
        execution_status="failed",
        quality_status="not_evaluated",
        exit_code=1,
        error_type="FileNotFoundError",
    )

    assert event.total_rows is None
    assert event.error_type == "FileNotFoundError"
    assert event.exit_code == 1


def test_scoring_pipeline_does_not_evaluate_drift():
    initial = start_event("scoring-001", "scoring", "not_applicable")

    event = finish_event(
        initial,
        finished_at=initial.started_at + timedelta(seconds=1),
        duration_seconds=1.0,
        execution_status="completed",
        quality_status="approved",
        exit_code=0,
        total_rows=5,
        scored_rows=5,
    )

    assert event.drift_status == "not_evaluated"


def test_event_is_immutable():
    event = start_event("batch-001", "monitoring", "control")

    with pytest.raises(FrozenInstanceError):
        event.batch_id = "altered"


def test_finish_preserves_identity():
    initial = start_event("batch-001", "monitoring", "control")
    terminal = completed_event()

    # Testa uma transicao real do mesmo objeto inicial.
    final = finish_event(
        initial,
        finished_at=initial.started_at + timedelta(seconds=1),
        duration_seconds=1.0,
        execution_status="completed",
        quality_status="approved",
        drift_status="not_detected",
        exit_code=0,
        total_rows=5,
        scored_rows=5,
        features_analyzed=16,
        features_drifted=0,
        drift_share=0.0,
    )

    assert final.execution_id == initial.execution_id
    assert initial.execution_status == "running"
    assert final.execution_id != terminal.execution_id


def test_serialization_is_json_safe():
    event = completed_event()
    payload = event.to_dict()

    serialized = json.dumps(payload, allow_nan=False)

    assert "execution_id" in payload
    assert "started_at" in payload
    assert "probabilities" not in payload
    assert "predictions" not in payload
    assert "SK_ID_CURR" not in serialized


@pytest.mark.parametrize(
    ("changes", "expected_message"),
    [
        ({"duration_seconds": -1}, "Duracao"),
        ({"duration_seconds": math.nan}, "Duracao"),
        ({"scored_rows": 101}, "Scoring excede"),
        ({"drift_share": 0.5}, "Proporcao de drift"),
        ({"exit_code": 2}, "Aprovacao exige"),
        ({"features_drifted": 17}, "Contagem de drift"),
        ({"quality_violations": -1}, "Contagem invalida"),
    ],
)
def test_invalid_terminal_values(changes, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        completed_event(**changes)


def test_rejected_batch_cannot_have_scores():
    with pytest.raises(ValueError, match="Rejeicao exige zero"):
        completed_event(
            quality_status="rejected",
            drift_status="not_evaluated",
            exit_code=2,
            scored_rows=1,
            features_analyzed=None,
            features_drifted=None,
            drift_share=None,
        )


def test_naive_datetime_is_rejected():
    event = start_event("batch-001", "monitoring", "control")

    with pytest.raises(ValueError, match="timezone"):
        replace(event, started_at=datetime(2026, 11, 14))


def test_invalid_batch_id_is_rejected():
    with pytest.raises(ValueError, match="batch_id"):
        start_event("../private/data", "monitoring", "external")


def test_terminal_event_cannot_be_finalized_again():
    event = completed_event()

    with pytest.raises(ValueError, match="Somente execucao inicial"):
        finish_event(
            event,
            finished_at=event.finished_at,
            duration_seconds=2.0,
            execution_status="completed",
            quality_status="approved",
            drift_status="not_detected",
            exit_code=0,
            total_rows=100,
            scored_rows=100,
            features_analyzed=16,
            features_drifted=0,
            drift_share=0.0,
        )


def test_failure_without_quality_cannot_have_scoring():
    initial = start_event("batch-error", "monitoring", "external")

    with pytest.raises(ValueError, match="Qualidade nao avaliada"):
        finish_event(
            initial,
            finished_at=initial.started_at + timedelta(seconds=1),
            duration_seconds=1.0,
            execution_status="failed",
            quality_status="not_evaluated",
            exit_code=1,
            scored_rows=100,
            error_type="RuntimeError",
        )


def test_failure_after_quality_can_preserve_partial_results():
    initial = start_event("batch-partial", "monitoring", "strong")

    event = finish_event(
        initial,
        finished_at=initial.started_at + timedelta(seconds=2),
        duration_seconds=2.0,
        execution_status="failed",
        quality_status="approved",
        exit_code=1,
        total_rows=100,
        scored_rows=100,
        quality_violations=0,
        error_type="OSError",
    )

    assert event.execution_status == "failed"
    assert event.quality_status == "approved"
    assert event.scored_rows == 100
    assert event.drift_status == "not_evaluated"

"""Testes do ciclo de vida da execucao observavel."""

import pytest

from credit_risk_monitoring.drift.monitoring import MonitoringResult
from credit_risk_monitoring.drift.results import DriftSummary
from credit_risk_monitoring.modeling.inference import InferenceResult
from credit_risk_monitoring.observability.adapters import (
    build_monitoring_event,
    build_scoring_event,
)
from credit_risk_monitoring.observability.events import start_event
from credit_risk_monitoring.observability.execution import execute_observed
from credit_risk_monitoring.observability.store import SQLiteEventStore


@pytest.fixture
def store(tmp_path):
    return SQLiteEventStore(tmp_path / "events.sqlite3")


def make_inference(*, approved=True, batch_id="batch-a"):
    return InferenceResult(
        batch_id=batch_id,
        status="approved" if approved else "rejected",
        total_rows=5,
        validations=(),
        threshold=0.14 if approved else None,
        probabilities=(0.2,) * 5 if approved else (),
        predictions=(1,) * 5 if approved else (),
    )


def make_monitoring(*, drifted=False):
    drift = DriftSummary(
        batch_id="batch-a",
        scenario_id="strong" if drifted else "control",
        reference_rows=10,
        production_rows=5,
        features_analyzed=16,
        features_drifted=2 if drifted else 0,
        drift_share=0.125 if drifted else 0.0,
        drift_detected=drifted,
        feature_results=(),
    )

    return MonitoringResult(
        batch_id="batch-a",
        scenario_id="strong" if drifted else "control",
        inference=make_inference(),
        drift=drift,
    )


def test_scoring_success_is_persisted(store):
    initial = start_event("batch-a", "scoring", "not_applicable")

    result, event = execute_observed(
        store=store,
        initial=initial,
        operation=lambda: make_inference(),
        build_event=build_scoring_event,
    )

    assert result.approved
    assert event.exit_code == 0
    assert event.duration_seconds >= 0
    assert store.get(initial.execution_id) == event


def test_scoring_rejection_is_persisted(store):
    initial = start_event("batch-a", "scoring", "not_applicable")

    _, event = execute_observed(
        store=store,
        initial=initial,
        operation=lambda: make_inference(approved=False),
        build_event=build_scoring_event,
    )

    assert event.exit_code == 2
    assert event.quality_status == "rejected"
    assert event.scored_rows == 0
    assert store.count() == 1


def test_monitoring_with_drift_is_successful(store):
    initial = start_event("batch-a", "monitoring", "strong")

    _, event = execute_observed(
        store=store,
        initial=initial,
        operation=lambda: make_monitoring(drifted=True),
        build_event=build_monitoring_event,
    )

    assert event.execution_status == "completed"
    assert event.exit_code == 0
    assert event.drift_status == "detected"
    assert store.get(initial.execution_id) == event


def test_operational_exception_is_recorded(store):
    initial = start_event("batch-a", "scoring", "not_applicable")

    def failing_operation():
        raise FileNotFoundError("/private/customer-data.csv")

    with pytest.raises(FileNotFoundError):
        execute_observed(
            store=store,
            initial=initial,
            operation=failing_operation,
            build_event=build_scoring_event,
        )

    event = store.get(initial.execution_id)

    assert event.execution_status == "failed"
    assert event.exit_code == 1
    assert event.quality_status == "not_evaluated"
    assert event.error_type == "FileNotFoundError"
    assert "/private/" not in str(event.to_dict())


def test_postprocessing_failure_preserves_partial_result(store):
    initial = start_event("batch-a", "monitoring", "control")

    def failing_export(_result):
        raise OSError("Erro ao salvar HTML com dados sensiveis")

    with pytest.raises(OSError):
        execute_observed(
            store=store,
            initial=initial,
            operation=make_monitoring,
            build_event=build_monitoring_event,
            postprocess=failing_export,
        )

    event = store.get(initial.execution_id)

    assert event.execution_status == "failed"
    assert event.exit_code == 1
    assert event.quality_status == "approved"
    assert event.scored_rows == 5
    assert event.drift_status == "not_detected"
    assert event.error_type == "OSError"
    assert "dados sensiveis" not in str(event.to_dict())


def test_postprocessing_runs_before_success_persistence(store):
    initial = start_event("batch-a", "scoring", "not_applicable")
    observed_statuses = []

    def inspect_during_postprocess(_result):
        current = store.get(initial.execution_id)
        observed_statuses.append(current.execution_status)

    _, event = execute_observed(
        store=store,
        initial=initial,
        operation=make_inference,
        build_event=build_scoring_event,
        postprocess=inspect_during_postprocess,
    )

    assert observed_statuses == ["running"]
    assert event.execution_status == "completed"
    assert store.count() == 1


def test_start_failure_prevents_pipeline_execution(store, monkeypatch):
    initial = start_event("batch-a", "scoring", "not_applicable")
    called = []

    def broken_start(_event):
        raise OSError("SQLite indisponivel")

    def operation():
        called.append(True)
        return make_inference()

    monkeypatch.setattr(store, "start", broken_start)

    with pytest.raises(OSError, match="SQLite indisponivel"):
        execute_observed(
            store=store,
            initial=initial,
            operation=operation,
            build_event=build_scoring_event,
        )

    assert called == []
    assert store.count() == 0


def test_terminal_persistence_failure_is_not_hidden(store, monkeypatch):
    initial = start_event("batch-a", "scoring", "not_applicable")

    def broken_finish(_event):
        raise OSError("SQLite indisponivel")

    monkeypatch.setattr(store, "finish", broken_finish)

    with pytest.raises(OSError, match="SQLite indisponivel"):
        execute_observed(
            store=store,
            initial=initial,
            operation=make_inference,
            build_event=build_scoring_event,
        )

    # A tentativa foi iniciada, mas nao concluida no banco.
    persisted = store.get(initial.execution_id)

    assert persisted.execution_status == "running"


def test_unsupported_initial_state_is_rejected(store):
    initial = start_event("batch-a", "scoring", "not_applicable")

    # Primeiro concluimos a tentativa.
    _, terminal = execute_observed(
        store=store,
        initial=initial,
        operation=make_inference,
        build_event=build_scoring_event,
    )

    with pytest.raises(ValueError, match="running"):
        execute_observed(
            store=store,
            initial=terminal,
            operation=make_inference,
            build_event=build_scoring_event,
        )


def test_execution_survives_store_reopening(store):
    initial = start_event("batch-a", "scoring", "not_applicable")

    _, event = execute_observed(
        store=store,
        initial=initial,
        operation=make_inference,
        build_event=build_scoring_event,
    )

    reopened = SQLiteEventStore(store.path)

    assert reopened.get(initial.execution_id) == event

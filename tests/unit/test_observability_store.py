"""Testes da persistencia de eventos operacionais."""

from dataclasses import replace
from datetime import timedelta

import pytest

from credit_risk_monitoring.observability.events import (
    finish_event,
    start_event,
)
from credit_risk_monitoring.observability.store import (
    EventStoreError,
    SQLiteEventStore,
)


@pytest.fixture
def store(tmp_path):
    return SQLiteEventStore(tmp_path / "events.sqlite3")


def make_terminal(initial, *, rejected=False):
    return finish_event(
        initial,
        finished_at=initial.started_at + timedelta(seconds=2),
        duration_seconds=2.0,
        execution_status="completed",
        quality_status="rejected" if rejected else "approved",
        drift_status=("not_evaluated" if rejected else "not_detected"),
        exit_code=2 if rejected else 0,
        total_rows=10,
        scored_rows=0 if rejected else 10,
        features_analyzed=None if rejected else 16,
        features_drifted=None if rejected else 0,
        drift_share=None if rejected else 0.0,
        quality_violations=1 if rejected else 0,
    )


def test_database_is_initialized(store):
    assert store.path.is_file()
    assert store.count() == 0
    assert store.list_events() == []


def test_start_and_get_event(store):
    initial = start_event("batch-a", "monitoring", "control")

    store.start(initial)

    assert store.get(initial.execution_id) == initial
    assert store.count() == 1


def test_start_is_idempotent(store):
    initial = start_event("batch-a", "monitoring", "control")

    store.start(initial)
    store.start(initial)

    assert store.count() == 1


def test_conflicting_start_is_rejected(store):
    initial = start_event("batch-a", "monitoring", "control")
    store.start(initial)

    conflicting = replace(initial, batch_id="batch-b")

    with pytest.raises(EventStoreError, match="ja utilizado"):
        store.start(conflicting)

    assert store.get(initial.execution_id) == initial


def test_finish_updates_existing_attempt(store):
    initial = start_event("batch-a", "monitoring", "control")
    terminal = make_terminal(initial)

    store.start(initial)
    store.finish(terminal)

    assert store.count() == 1
    assert store.get(initial.execution_id) == terminal


def test_finish_is_idempotent(store):
    initial = start_event("batch-a", "monitoring", "control")
    terminal = make_terminal(initial)

    store.start(initial)
    store.finish(terminal)
    store.finish(terminal)

    assert store.count() == 1


def test_terminal_cannot_be_changed(store):
    initial = start_event("batch-a", "monitoring", "control")
    terminal = make_terminal(initial)

    store.start(initial)
    store.finish(terminal)

    changed = replace(
        terminal,
        duration_seconds=3.0,
    )

    with pytest.raises(EventStoreError, match="terminal"):
        store.finish(changed)

    assert store.get(initial.execution_id) == terminal


def test_finish_requires_existing_start(store):
    initial = start_event("batch-a", "monitoring", "control")
    terminal = make_terminal(initial)

    with pytest.raises(EventStoreError, match="nao iniciada"):
        store.finish(terminal)


def test_rejected_event_is_persisted(store):
    initial = start_event("batch-rejected", "monitoring", "external")
    terminal = make_terminal(initial, rejected=True)

    store.start(initial)
    store.finish(terminal)

    recovered = store.get(initial.execution_id)

    assert recovered.quality_status == "rejected"
    assert recovered.scored_rows == 0
    assert recovered.drift_status == "not_evaluated"


def test_events_survive_store_reinitialization(store):
    initial = start_event("batch-a", "monitoring", "strong")
    terminal = make_terminal(initial)

    store.start(initial)
    store.finish(terminal)

    reopened = SQLiteEventStore(store.path)

    assert reopened.count() == 1
    assert reopened.get(initial.execution_id) == terminal


def test_same_batch_can_have_multiple_attempts(store):
    first = start_event("batch-a", "monitoring", "control")
    second = start_event("batch-a", "monitoring", "control")

    store.start(first)
    store.start(second)

    assert first.execution_id != second.execution_id
    assert store.count() == 2
    assert len(store.list_events(batch_id="batch-a")) == 2


def test_list_events_filters_by_batch(store):
    first = start_event("batch-a", "monitoring", "control")
    second = start_event("batch-b", "monitoring", "strong")

    store.start(first)
    store.start(second)

    events = store.list_events(batch_id="batch-a")

    assert len(events) == 1
    assert events[0].batch_id == "batch-a"


def test_invalid_limit_is_rejected(store):
    with pytest.raises(ValueError, match="limit"):
        store.list_events(limit=0)


def test_terminal_event_cannot_be_started(store):
    initial = start_event("batch-a", "monitoring", "control")
    terminal = make_terminal(initial)

    with pytest.raises(ValueError, match="running"):
        store.start(terminal)


def test_running_event_cannot_be_finished(store):
    initial = start_event("batch-a", "monitoring", "control")

    store.start(initial)

    with pytest.raises(ValueError, match="terminal"):
        store.finish(initial)


def test_missing_parent_directory_is_rejected(tmp_path):
    path = tmp_path / "nonexistent" / "events.sqlite3"

    with pytest.raises(ValueError, match="Diretorio"):
        SQLiteEventStore(path)


def test_failed_execution_is_persisted(store):
    initial = start_event("batch-error", "monitoring", "external")

    failed = finish_event(
        initial,
        finished_at=initial.started_at + timedelta(seconds=1),
        duration_seconds=1.0,
        execution_status="failed",
        quality_status="not_evaluated",
        exit_code=1,
        error_type="FileNotFoundError",
    )

    store.start(initial)
    store.finish(failed)

    recovered = store.get(initial.execution_id)

    assert recovered.execution_status == "failed"
    assert recovered.exit_code == 1
    assert recovered.error_type == "FileNotFoundError"

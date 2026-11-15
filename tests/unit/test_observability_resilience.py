"""Testes de concorrencia, integridade e recuperacao do SQLite."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
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


def make_completed(initial):
    return finish_event(
        initial,
        finished_at=initial.started_at + timedelta(seconds=1),
        duration_seconds=1.0,
        execution_status="completed",
        quality_status="approved",
        drift_status="not_evaluated",
        exit_code=0,
        total_rows=5,
        scored_rows=5,
        quality_violations=0,
    )


def test_concurrent_distinct_executions(store):
    """Execucoes concorrentes nao devem perder registros."""

    def worker(index):
        initial = start_event(
            f"concurrent-{index}",
            "scoring",
            "not_applicable",
        )
        terminal = make_completed(initial)

        store.start(initial)
        store.finish(terminal)

        return initial.execution_id

    with ThreadPoolExecutor(max_workers=4) as pool:
        identifiers = list(pool.map(worker, range(12)))

    assert len(set(identifiers)) == 12
    assert store.count() == 12

    for identifier in identifiers:
        event = store.get(identifier)
        assert event is not None
        assert event.execution_status == "completed"


def test_concurrent_duplicate_start_is_idempotent(store):
    """Mesmo execution_id nao pode gerar varias tentativas."""
    initial = start_event(
        "same-execution",
        "scoring",
        "not_applicable",
    )

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(store.start, [initial] * 8))

    assert store.count() == 1
    assert store.get(initial.execution_id) == initial


def test_concurrent_conflicting_finalization(store):
    """Somente uma finalizacao diferente pode prevalecer."""
    initial = start_event(
        "conflicting-finalization",
        "scoring",
        "not_applicable",
    )

    first = make_completed(initial)

    second = finish_event(
        initial,
        finished_at=initial.started_at + timedelta(seconds=2),
        duration_seconds=2.0,
        execution_status="failed",
        quality_status="not_evaluated",
        exit_code=1,
        error_type="RuntimeError",
    )

    store.start(initial)

    def finalize(event):
        try:
            store.finish(event)
            return "accepted"
        except EventStoreError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(finalize, (first, second)))

    assert sorted(results) == ["accepted", "rejected"]
    assert store.count() == 1

    persisted = store.get(initial.execution_id)
    assert persisted in (first, second)


def test_running_event_survives_restart(store):
    """Execucao sem finalizacao continua visivel apos reabertura."""
    initial = start_event(
        "interrupted-attempt",
        "monitoring",
        "external",
    )

    store.start(initial)

    reopened = SQLiteEventStore(store.path)
    recovered = reopened.get(initial.execution_id)

    assert recovered == initial
    assert recovered.execution_status == "running"
    assert recovered.finished_at is None
    assert recovered.exit_code is None


def test_corrupted_payload_is_rejected(store):
    """Dados persistidos adulterados nao podem ser aceitos."""
    initial = start_event(
        "corrupted-payload",
        "scoring",
        "not_applicable",
    )

    store.start(initial)

    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            """
            SELECT payload FROM operational_events
            WHERE execution_id = ?
            """,
            (initial.execution_id,),
        ).fetchone()

        payload = json.loads(row[0])
        payload["batch_id"] = "different-batch"

        connection.execute(
            """
            UPDATE operational_events
            SET payload = ?
            WHERE execution_id = ?
            """,
            (
                json.dumps(payload),
                initial.execution_id,
            ),
        )

    with pytest.raises(
        EventStoreError,
        match="divergentes",
    ):
        store.get(initial.execution_id)


def test_failed_terminal_transaction_preserves_running(store):
    """Rollback impede finalizacao parcialmente persistida."""
    initial = start_event("rollback-test", "scoring", "not_applicable")
    terminal = make_completed(initial)
    store.start(initial)

    with sqlite3.connect(store.path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_terminal_update
            BEFORE UPDATE ON operational_events
            BEGIN
                SELECT RAISE(ABORT, 'simulated transaction failure');
            END
            """
        )

    with pytest.raises(
        sqlite3.DatabaseError,
        match="simulated transaction failure",
    ):
        store.finish(terminal)

    recovered = store.get(initial.execution_id)

    assert recovered == initial
    assert recovered.execution_status == "running"
    assert store.count() == 1


def test_invalid_json_payload_is_rejected(store):
    """JSON malformado nao pode ser retornado como evento valido."""
    initial = start_event("invalid-json", "scoring", "not_applicable")
    store.start(initial)

    with sqlite3.connect(store.path) as connection:
        connection.execute(
            """
            UPDATE operational_events
            SET payload = ?
            WHERE execution_id = ?
            """,
            ("{invalid-json", initial.execution_id),
        )

    with pytest.raises(EventStoreError, match="invalido"):
        store.get(initial.execution_id)


def test_failure_does_not_change_previous_history(store):
    """Nova tentativa falha nao modifica execucoes anteriores."""
    previous = start_event("shared-batch", "scoring", "not_applicable")
    previous_terminal = make_completed(previous)

    store.start(previous)
    store.finish(previous_terminal)

    retry = start_event("shared-batch", "scoring", "not_applicable")
    store.start(retry)

    failure = finish_event(
        retry,
        finished_at=retry.started_at + timedelta(seconds=1),
        duration_seconds=1.0,
        execution_status="failed",
        quality_status="not_evaluated",
        exit_code=1,
        error_type="RuntimeError",
    )

    store.finish(failure)

    assert store.count() == 2
    assert store.get(previous.execution_id) == previous_terminal
    assert store.get(retry.execution_id) == failure

    history = store.list_events(batch_id="shared-batch")
    assert {item.execution_status for item in history} == {
        "completed",
        "failed",
    }

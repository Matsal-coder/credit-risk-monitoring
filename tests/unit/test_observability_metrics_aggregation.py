"""Testes da agregacao completa do historico operacional."""

import json
import sqlite3
from datetime import timedelta

import pytest

from credit_risk_monitoring.observability.events import (
    finish_event,
    start_event,
)
from credit_risk_monitoring.observability.metrics_aggregation import (
    aggregate_metrics,
)
from credit_risk_monitoring.observability.store import (
    EventStoreError,
    SQLiteEventStore,
)


@pytest.fixture
def store(tmp_path):
    return SQLiteEventStore(tmp_path / "metrics.sqlite3")


def value(samples, name, **labels):
    matches = [
        sample.value
        for sample in samples
        if sample.name == name and dict(sample.labels) == labels
    ]

    assert len(matches) == 1
    return matches[0]


def test_empty_database_has_zero_counts_and_no_success(store):
    samples = aggregate_metrics(store)

    assert (
        value(
            samples,
            "credit_risk_executions_count",
            pipeline="scoring",
            execution_status="completed",
        )
        == 0
    )

    assert (
        value(
            samples,
            "credit_risk_running_executions",
            pipeline="monitoring",
        )
        == 0
    )

    assert not any(
        sample.name == "credit_risk_last_success_timestamp_seconds"
        for sample in samples
    )


def test_scoring_aggregates_success_rejection_and_failure(store):
    approved = start_event("approved-1", "scoring", "not_applicable")
    rejected = start_event("rejected-1", "scoring", "not_applicable")
    failed = start_event("failed-1", "scoring", "not_applicable")

    for event in (approved, rejected, failed):
        store.start(event)

    store.finish(
        finish_event(
            approved,
            finished_at=approved.started_at + timedelta(seconds=2),
            duration_seconds=2.0,
            execution_status="completed",
            quality_status="approved",
            drift_status="not_evaluated",
            exit_code=0,
            total_rows=5,
            scored_rows=5,
            quality_violations=0,
        )
    )

    store.finish(
        finish_event(
            rejected,
            finished_at=rejected.started_at + timedelta(seconds=3),
            duration_seconds=3.0,
            execution_status="completed",
            quality_status="rejected",
            drift_status="not_evaluated",
            exit_code=2,
            total_rows=5,
            scored_rows=0,
            quality_violations=2,
        )
    )

    store.finish(
        finish_event(
            failed,
            finished_at=failed.started_at + timedelta(seconds=1),
            duration_seconds=1.0,
            execution_status="failed",
            quality_status="not_evaluated",
            drift_status="not_evaluated",
            exit_code=1,
            error_type="FileNotFoundError",
        )
    )

    samples = aggregate_metrics(store)

    assert (
        value(
            samples,
            "credit_risk_executions_count",
            pipeline="scoring",
            execution_status="completed",
        )
        == 2
    )

    assert (
        value(
            samples,
            "credit_risk_executions_count",
            pipeline="scoring",
            execution_status="failed",
        )
        == 1
    )

    assert (
        value(
            samples,
            "credit_risk_quality_violations_count",
            pipeline="scoring",
        )
        == 2
    )

    assert (
        value(
            samples,
            "credit_risk_execution_duration_seconds_sum",
            pipeline="scoring",
        )
        == 6
    )

    assert (
        value(
            samples,
            "credit_risk_execution_duration_seconds_count",
            pipeline="scoring",
        )
        == 3
    )

    assert value(
        samples,
        "credit_risk_last_success_timestamp_seconds",
        pipeline="scoring",
    ) == pytest.approx((approved.started_at + timedelta(seconds=2)).timestamp())


def test_running_is_excluded_from_duration(store):
    initial = start_event("running-1", "monitoring", "external")
    store.start(initial)

    samples = aggregate_metrics(store)

    assert (
        value(
            samples,
            "credit_risk_running_executions",
            pipeline="monitoring",
        )
        == 1
    )

    assert (
        value(
            samples,
            "credit_risk_execution_duration_seconds_count",
            pipeline="monitoring",
        )
        == 0
    )


def test_detected_drift_is_not_operational_failure(store):
    initial = start_event("strong-1", "monitoring", "strong")
    store.start(initial)

    store.finish(
        finish_event(
            initial,
            finished_at=initial.started_at + timedelta(seconds=4),
            duration_seconds=4.0,
            execution_status="completed",
            quality_status="approved",
            drift_status="detected",
            exit_code=0,
            total_rows=100,
            scored_rows=100,
            quality_violations=0,
            features_analyzed=16,
            features_drifted=2,
            drift_share=0.125,
        )
    )

    samples = aggregate_metrics(store)

    assert (
        value(
            samples,
            "credit_risk_drift_detected_count",
            pipeline="monitoring",
        )
        == 1
    )

    assert (
        value(
            samples,
            "credit_risk_executions_count",
            pipeline="monitoring",
            execution_status="completed",
        )
        == 1
    )

    assert (
        value(
            samples,
            "credit_risk_executions_count",
            pipeline="monitoring",
            execution_status="failed",
        )
        == 0
    )


def test_iteration_reads_more_than_list_limit(store):
    for index in range(1001):
        event = start_event(
            f"history-{index}",
            "scoring",
            "not_applicable",
        )
        store.start(event)

    assert len(store.list_events(limit=1000)) == 1000
    assert sum(1 for _ in store.iter_events(chunk_size=73)) == 1001

    samples = aggregate_metrics(store)

    assert (
        value(
            samples,
            "credit_risk_executions_count",
            pipeline="scoring",
            execution_status="running",
        )
        == 1001
    )


def test_corrupted_event_aborts_aggregation(store):
    event = start_event("corrupted", "scoring", "not_applicable")
    store.start(event)

    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            """
            SELECT payload FROM operational_events
            WHERE execution_id = ?
            """,
            (event.execution_id,),
        ).fetchone()

        payload = json.loads(row[0])
        payload["batch_id"] = "tampered"

        connection.execute(
            """
            UPDATE operational_events
            SET payload = ?
            WHERE execution_id = ?
            """,
            (json.dumps(payload), event.execution_id),
        )

    with pytest.raises(EventStoreError):
        aggregate_metrics(store)

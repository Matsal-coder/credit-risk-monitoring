"""Testes HTTP da exposicao das metricas operacionais."""

import json
import sqlite3
from datetime import timedelta

from litestar.testing import TestClient

from credit_risk_monitoring.observability.events import (
    finish_event,
    start_event,
)
from credit_risk_monitoring.observability.metrics_http import create_app
from credit_risk_monitoring.observability.store import SQLiteEventStore


def test_metrics_endpoint_empty_database(tmp_path):
    database = tmp_path / "empty.sqlite3"
    SQLiteEventStore(database)

    with TestClient(app=create_app(database)) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# TYPE credit_risk_executions_count gauge" in response.text
    assert 'credit_risk_running_executions{pipeline="scoring"} 0.0' in response.text


def test_metrics_endpoint_reads_real_events(tmp_path):
    database = tmp_path / "events.sqlite3"
    store = SQLiteEventStore(database)

    initial = start_event(
        "http-success",
        "scoring",
        "not_applicable",
    )
    store.start(initial)

    terminal = finish_event(
        initial,
        finished_at=initial.started_at + timedelta(seconds=2),
        duration_seconds=2.0,
        execution_status="completed",
        quality_status="approved",
        drift_status="not_evaluated",
        exit_code=0,
        total_rows=5,
        scored_rows=5,
        quality_violations=0,
    )
    store.finish(terminal)

    with TestClient(app=create_app(database)) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert (
        "credit_risk_executions_count"
        '{pipeline="scoring",execution_status="completed"} 1.0' in response.text
    )
    assert (
        "credit_risk_execution_duration_seconds_sum"
        '{pipeline="scoring"} 2.0' in response.text
    )
    assert "http-success" not in response.text


def test_missing_database_returns_error(tmp_path):
    database = tmp_path / "missing.sqlite3"

    with TestClient(
        app=create_app(database),
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/metrics")

    assert response.status_code == 500
    assert not database.exists()
    assert "# TYPE credit_risk_" not in response.text


def test_corrupted_database_returns_error(tmp_path):
    database = tmp_path / "corrupted.sqlite3"
    store = SQLiteEventStore(database)

    event = start_event(
        "corrupted-event",
        "scoring",
        "not_applicable",
    )
    store.start(event)

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT payload
            FROM operational_events
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

    with TestClient(
        app=create_app(database),
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/metrics")

    assert response.status_code == 500
    assert "# TYPE credit_risk_" not in response.text


def test_unsupported_route_returns_404(tmp_path):
    database = tmp_path / "events.sqlite3"
    SQLiteEventStore(database)

    with TestClient(app=create_app(database)) as client:
        response = client.get("/events")

    assert response.status_code == 404


def test_metrics_refresh_between_requests(tmp_path):
    """Nova execucao deve aparecer no proximo scrape."""
    database = tmp_path / "refresh.sqlite3"
    store = SQLiteEventStore(database)

    initial = start_event(
        "refresh-test",
        "scoring",
        "not_applicable",
    )

    with TestClient(app=create_app(database)) as client:
        first = client.get("/metrics")

        assert first.status_code == 200
        assert 'credit_risk_running_executions{pipeline="scoring"} 0.0' in first.text

        store.start(initial)

        second = client.get("/metrics")

        assert second.status_code == 200
        assert 'credit_risk_running_executions{pipeline="scoring"} 1.0' in second.text

        terminal = finish_event(
            initial,
            finished_at=initial.started_at + timedelta(seconds=2),
            duration_seconds=2.0,
            execution_status="completed",
            quality_status="approved",
            drift_status="not_evaluated",
            exit_code=0,
            total_rows=5,
            scored_rows=5,
            quality_violations=0,
        )
        store.finish(terminal)

        third = client.get("/metrics")

        assert third.status_code == 200
        assert 'credit_risk_running_executions{pipeline="scoring"} 0.0' in third.text
        assert (
            "credit_risk_executions_count"
            '{pipeline="scoring",execution_status="completed"} 1.0' in third.text
        )
        assert "refresh-test" not in third.text


def test_database_removed_after_start_returns_500(tmp_path):
    """Exporter nao deve publicar zeros se o banco desaparecer."""
    database = tmp_path / "disappearing.sqlite3"
    SQLiteEventStore(database)

    with TestClient(
        app=create_app(database),
        raise_server_exceptions=False,
    ) as client:
        first = client.get("/metrics")
        assert first.status_code == 200

        database.unlink()

        second = client.get("/metrics")

        assert second.status_code == 500
        assert "# TYPE credit_risk_" not in second.text

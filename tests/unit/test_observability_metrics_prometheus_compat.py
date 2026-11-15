"""Compatibilidade com o parser independente do Prometheus."""

from datetime import timedelta

from prometheus_client.parser import text_string_to_metric_families

from credit_risk_monitoring.observability.events import (
    finish_event,
    start_event,
)
from credit_risk_monitoring.observability.metrics_aggregation import (
    aggregate_metrics,
)
from credit_risk_monitoring.observability.metrics_catalog import (
    METRIC_DEFINITIONS,
)
from credit_risk_monitoring.observability.metrics_exposition import (
    render_metrics,
)
from credit_risk_monitoring.observability.store import SQLiteEventStore


def test_prometheus_parser_accepts_all_metric_families(tmp_path):
    database = tmp_path / "prometheus-compat.sqlite3"
    store = SQLiteEventStore(database)

    initial = start_event(
        "parser-test",
        "monitoring",
        "strong",
    )
    store.start(initial)

    store.finish(
        finish_event(
            initial,
            finished_at=initial.started_at + timedelta(seconds=3),
            duration_seconds=3.0,
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

    payload = render_metrics(aggregate_metrics(store))
    families = list(text_string_to_metric_families(payload))

    expected_names = {definition.name for definition in METRIC_DEFINITIONS}
    observed_names = {family.name for family in families}

    assert observed_names == expected_names
    assert len(families) == 7
    assert all(family.type == "gauge" for family in families)

    samples = [sample for family in families for sample in family.samples]

    assert len(samples) == 17
    assert all(sample.name in expected_names for sample in samples)

    # O batch_id permanece ausente das labels.
    assert all("batch_id" not in sample.labels for sample in samples)
    assert all("execution_id" not in sample.labels for sample in samples)

    drift = next(
        sample
        for sample in samples
        if sample.name == "credit_risk_drift_detected_count"
        and sample.labels["pipeline"] == "monitoring"
    )

    assert drift.value == 1.0

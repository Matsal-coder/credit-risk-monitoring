"""Testes do catalogo de metricas Prometheus."""

import pytest

from credit_risk_monitoring.observability.metrics_catalog import (
    METRIC_DEFINITIONS,
    get_metric_definition,
)


def test_metric_names_are_unique():
    names = [item.name for item in METRIC_DEFINITIONS]

    assert len(names) == len(set(names))


def test_all_metrics_have_valid_contracts():
    assert len(METRIC_DEFINITIONS) == 7

    for definition in METRIC_DEFINITIONS:
        assert definition.name.startswith("credit_risk_")
        assert definition.description.strip()
        assert definition.metric_type == "gauge"
        assert len(definition.labels) == len(set(definition.labels))


def test_no_high_cardinality_labels():
    forbidden = {
        "batch_id",
        "execution_id",
        "sk_id_curr",
        "customer_id",
        "error_message",
        "file_path",
    }

    for definition in METRIC_DEFINITIONS:
        assert not forbidden.intersection(definition.labels)


def test_only_approved_label_dimensions():
    approved = {
        "pipeline",
        "execution_status",
    }

    for definition in METRIC_DEFINITIONS:
        assert set(definition.labels).issubset(approved)


def test_durations_have_sum_and_count():
    names = {item.name for item in METRIC_DEFINITIONS}

    assert "credit_risk_execution_duration_seconds_sum" in names
    assert "credit_risk_execution_duration_seconds_count" in names


def test_definition_lookup():
    definition = get_metric_definition("credit_risk_running_executions")

    assert definition.metric_type == "gauge"
    assert definition.labels == ("pipeline",)


def test_unknown_metric_is_rejected():
    with pytest.raises(KeyError, match="Unknown metric"):
        get_metric_definition("unknown_metric")

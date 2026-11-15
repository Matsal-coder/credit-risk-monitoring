"""Catalogo estatico das metricas operacionais Prometheus."""

from dataclasses import dataclass
from typing import Literal

MetricType = Literal["gauge"]


@dataclass(frozen=True)
class MetricDefinition:
    """Contrato publico de uma metrica operacional."""

    name: str
    description: str
    metric_type: MetricType
    labels: tuple[str, ...]


PIPELINE_LABELS = ("pipeline",)

METRIC_DEFINITIONS = (
    MetricDefinition(
        name="credit_risk_executions_count",
        description="Number of recorded operational executions.",
        metric_type="gauge",
        labels=("pipeline", "execution_status"),
    ),
    MetricDefinition(
        name="credit_risk_quality_violations_count",
        description="Recorded data quality violation occurrences.",
        metric_type="gauge",
        labels=PIPELINE_LABELS,
    ),
    MetricDefinition(
        name="credit_risk_drift_detected_count",
        description="Executions with detected data drift.",
        metric_type="gauge",
        labels=PIPELINE_LABELS,
    ),
    MetricDefinition(
        name="credit_risk_execution_duration_seconds_sum",
        description="Sum of completed execution durations in seconds.",
        metric_type="gauge",
        labels=PIPELINE_LABELS,
    ),
    MetricDefinition(
        name="credit_risk_execution_duration_seconds_count",
        description="Number of recorded execution durations.",
        metric_type="gauge",
        labels=PIPELINE_LABELS,
    ),
    MetricDefinition(
        name="credit_risk_running_executions",
        description="Executions still marked as running.",
        metric_type="gauge",
        labels=PIPELINE_LABELS,
    ),
    MetricDefinition(
        name="credit_risk_last_success_timestamp_seconds",
        description="Unix timestamp of the latest successful execution.",
        metric_type="gauge",
        labels=PIPELINE_LABELS,
    ),
)


def get_metric_definition(name: str) -> MetricDefinition:
    """Consulta um contrato pelo nome publico."""
    for definition in METRIC_DEFINITIONS:
        if definition.name == name:
            return definition

    raise KeyError(f"Unknown metric: {name}")

"""Agregacao de eventos SQLite em amostras de metricas operacionais."""

from collections import defaultdict
from dataclasses import dataclass

from credit_risk_monitoring.observability.metrics_catalog import (
    get_metric_definition,
)
from credit_risk_monitoring.observability.store import SQLiteEventStore

PIPELINES = ("scoring", "monitoring")
EXECUTION_STATUSES = ("running", "completed", "failed")


@dataclass(frozen=True)
class MetricSample:
    """Uma amostra numerica com labels de cardinalidade controlada."""

    name: str
    labels: tuple[tuple[str, str], ...]
    value: float


def _sample(
    name: str,
    labels: dict[str, str],
    value: int | float,
) -> MetricSample:
    """Aplica a ordem e as dimensoes do catalogo publico."""
    definition = get_metric_definition(name)

    if set(labels) != set(definition.labels):
        raise ValueError("Dimensoes incompatíveis com o catalogo.")

    return MetricSample(
        name=name,
        labels=tuple((label, labels[label]) for label in definition.labels),
        value=float(value),
    )


def aggregate_metrics(
    store: SQLiteEventStore,
) -> tuple[MetricSample, ...]:
    """Reconstroi indicadores a partir do historico completo."""
    executions: dict[tuple[str, str], int] = defaultdict(int)
    violations: dict[str, int] = defaultdict(int)
    drift_detected: dict[str, int] = defaultdict(int)
    duration_sum: dict[str, float] = defaultdict(float)
    duration_count: dict[str, int] = defaultdict(int)
    running: dict[str, int] = defaultdict(int)
    last_success: dict[str, float] = {}

    for event in store.iter_events():
        pipeline = event.pipeline

        executions[(pipeline, event.execution_status)] += 1

        if event.execution_status == "running":
            running[pipeline] += 1

        if event.quality_violations is not None:
            violations[pipeline] += event.quality_violations

        if event.drift_status == "detected":
            drift_detected[pipeline] += 1

        if event.duration_seconds is not None:
            duration_sum[pipeline] += event.duration_seconds
            duration_count[pipeline] += 1

        if (
            event.execution_status == "completed"
            and event.exit_code == 0
            and event.finished_at is not None
        ):
            timestamp = event.finished_at.timestamp()
            previous = last_success.get(pipeline)

            if previous is None or timestamp > previous:
                last_success[pipeline] = timestamp

    samples: list[MetricSample] = []

    for pipeline in PIPELINES:
        for status in EXECUTION_STATUSES:
            samples.append(
                _sample(
                    "credit_risk_executions_count",
                    {
                        "pipeline": pipeline,
                        "execution_status": status,
                    },
                    executions[(pipeline, status)],
                )
            )

        values = (
            (
                "credit_risk_quality_violations_count",
                violations[pipeline],
            ),
            (
                "credit_risk_drift_detected_count",
                drift_detected[pipeline],
            ),
            (
                "credit_risk_execution_duration_seconds_sum",
                duration_sum[pipeline],
            ),
            (
                "credit_risk_execution_duration_seconds_count",
                duration_count[pipeline],
            ),
            (
                "credit_risk_running_executions",
                running[pipeline],
            ),
        )

        for name, value in values:
            samples.append(
                _sample(
                    name,
                    {"pipeline": pipeline},
                    value,
                )
            )

        if pipeline in last_success:
            samples.append(
                _sample(
                    "credit_risk_last_success_timestamp_seconds",
                    {"pipeline": pipeline},
                    last_success[pipeline],
                )
            )

    return tuple(samples)

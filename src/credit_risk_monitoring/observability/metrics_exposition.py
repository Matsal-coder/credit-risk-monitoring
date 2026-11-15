"""Serializacao de metricas no formato textual Prometheus."""

import math

from credit_risk_monitoring.observability.metrics_aggregation import (
    MetricSample,
)
from credit_risk_monitoring.observability.metrics_catalog import (
    METRIC_DEFINITIONS,
)


def _escape_label(value: str) -> str:
    """Escapa caracteres especiais em valores de labels."""
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _escape_help(value: str) -> str:
    """Escapa caracteres especiais da descricao da metrica."""
    return value.replace("\\", "\\\\").replace("\n", "\\n")


def render_metrics(samples: tuple[MetricSample, ...]) -> str:
    """Gera exposicao Prometheus com contratos e valores validados."""
    by_name: dict[str, list[MetricSample]] = {
        definition.name: [] for definition in METRIC_DEFINITIONS
    }

    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()

    definitions = {definition.name: definition for definition in METRIC_DEFINITIONS}

    for sample in samples:
        definition = definitions.get(sample.name)

        if definition is None:
            raise ValueError("Metrica desconhecida.")

        expected_labels = definition.labels
        actual_labels = tuple(name for name, _ in sample.labels)

        if actual_labels != expected_labels:
            raise ValueError("Labels incompatíveis com o catalogo.")

        if not all(isinstance(value, str) for _, value in sample.labels):
            raise ValueError("Valor de label deve ser texto.")

        if not math.isfinite(sample.value) or sample.value < 0:
            raise ValueError("Valor numerico invalido.")

        identity = (sample.name, sample.labels)

        if identity in seen:
            raise ValueError("Amostra duplicada.")

        seen.add(identity)
        by_name[sample.name].append(sample)

    lines: list[str] = []

    for definition in METRIC_DEFINITIONS:
        name = definition.name

        lines.append(f"# HELP {name} {_escape_help(definition.description)}")
        lines.append(f"# TYPE {name} {definition.metric_type}")

        for sample in sorted(
            by_name[name],
            key=lambda item: item.labels,
        ):
            if sample.labels:
                rendered_labels = ",".join(
                    f'{label}="{_escape_label(value)}"'
                    for label, value in sample.labels
                )
                identifier = f"{name}{{{rendered_labels}}}"
            else:
                identifier = name

            lines.append(f"{identifier} {sample.value}")

    return "\n".join(lines) + "\n"

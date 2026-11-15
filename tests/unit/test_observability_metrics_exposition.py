"""Testes da exposicao textual das metricas Prometheus."""

import pytest

from credit_risk_monitoring.observability.metrics_aggregation import (
    MetricSample,
)
from credit_risk_monitoring.observability.metrics_exposition import (
    render_metrics,
)


def sample(
    name="credit_risk_running_executions",
    labels=(("pipeline", "scoring"),),
    value=2.0,
):
    return MetricSample(
        name=name,
        labels=labels,
        value=value,
    )


def test_renders_valid_gauge_with_labels():
    text = render_metrics((sample(),))

    assert "# TYPE credit_risk_running_executions gauge" in text
    assert 'credit_risk_running_executions{pipeline="scoring"} 2.0' in text
    assert text.endswith("\n")


def test_emits_help_and_type_for_all_catalog_metrics():
    text = render_metrics(())

    assert text.count("# HELP ") == 7
    assert text.count("# TYPE ") == 7


def test_rejects_unknown_metric():
    with pytest.raises(ValueError, match="desconhecida"):
        render_metrics((sample(name="unknown_metric"),))


def test_rejects_incompatible_labels():
    with pytest.raises(ValueError, match="incompatíveis"):
        render_metrics(
            (
                sample(
                    labels=(("batch_id", "sensitive"),),
                ),
            )
        )


@pytest.mark.parametrize(
    "invalid_value",
    [float("nan"), float("inf"), float("-inf"), -1.0],
)
def test_rejects_invalid_numeric_values(invalid_value):
    with pytest.raises(ValueError, match="numerico"):
        render_metrics((sample(value=invalid_value),))


def test_rejects_duplicate_samples():
    with pytest.raises(ValueError, match="duplicada"):
        render_metrics((sample(), sample()))


def test_escapes_label_values():
    text = render_metrics(
        (
            sample(
                labels=(("pipeline", 'a"b\\c\nx'),),
            ),
        )
    )

    assert 'pipeline="a\\"b\\\\c\\nx"' in text


def test_output_is_independent_of_sample_order():
    first = sample(
        labels=(("pipeline", "monitoring"),),
    )
    second = sample(
        labels=(("pipeline", "scoring"),),
    )

    assert render_metrics((first, second)) == render_metrics((second, first))

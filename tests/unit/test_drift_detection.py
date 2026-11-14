"""Testes da integracao estatistica com Evidently."""

import json

import numpy as np
import pandas as pd
import pytest

from credit_risk_monitoring.drift.detection import (
    FeatureDriftResult,
    extract_feature_drift,
    run_evidently_drift,
)


def test_extract_feature_drift() -> None:
    metrics = [
        {
            "config": {
                "type": "evidently:metric_v2:ValueDrift",
                "column": "AMT_CREDIT",
                "method": "K-S p_value",
                "threshold": 0.05,
            },
            "value": 0.001,
        },
    ]

    results = extract_feature_drift(
        metrics,
        ("AMT_CREDIT",),
    )

    assert len(results) == 1
    assert results[0].feature == "AMT_CREDIT"
    assert results[0].drift_detected
    assert results[0].score == 0.001


def test_extract_rejects_missing_metric() -> None:
    with pytest.raises(ValueError, match="incompletos"):
        extract_feature_drift([], ("AMT_CREDIT",))


def test_extract_rejects_unsupported_method() -> None:
    metrics = [
        {
            "config": {
                "type": "evidently:metric_v2:ValueDrift",
                "column": "AMT_CREDIT",
                "method": "unknown",
                "threshold": 0.05,
            },
            "value": 0.01,
        },
    ]

    with pytest.raises(ValueError, match="Metodo"):
        extract_feature_drift(metrics, ("AMT_CREDIT",))


def test_real_evidently_execution() -> None:
    rng = np.random.default_rng(642)

    reference = pd.DataFrame(
        {
            "AMT_CREDIT": rng.normal(200000, 30000, 500),
        }
    )

    production = pd.DataFrame(
        {
            "AMT_CREDIT": rng.normal(270000, 30000, 500),
        }
    )

    snapshot, results = run_evidently_drift(
        reference,
        production,
        ("AMT_CREDIT",),
    )

    assert snapshot is not None
    assert len(results) == 1
    assert results[0].method == "K-S p_value"
    assert 0 <= results[0].score <= 1
    assert results[0].drift_detected


def test_rejects_missing_feature() -> None:
    reference = pd.DataFrame({"AMT_CREDIT": [100.0, 200.0]})
    production = pd.DataFrame({"OTHER": [100.0, 200.0]})

    with pytest.raises(ValueError, match="ausentes"):
        run_evidently_drift(
            reference,
            production,
            ("AMT_CREDIT",),
        )


@pytest.mark.parametrize(
    ("method", "score"),
    [
        ("K-S p_value", 0.001),
        ("chi-square p_value", 0.002),
        ("Z-test p_value", 0.0),
    ],
)
def test_extract_supported_statistical_methods(
    method: str,
    score: float,
) -> None:
    metrics = [
        {
            "config": {
                "type": "evidently:metric_v2:ValueDrift",
                "column": "TEST_FEATURE",
                "method": method,
                "threshold": 0.05,
            },
            "value": score,
        },
    ]

    result = extract_feature_drift(
        metrics,
        ("TEST_FEATURE",),
    )

    assert result[0].method == method
    assert result[0].score == score
    assert result[0].drift_detected


@pytest.mark.parametrize(
    "invalid_score",
    [float("nan"), float("inf"), -0.1, 1.1, True],
)
def test_extract_rejects_invalid_pvalues(
    invalid_score,
) -> None:
    metrics = [
        {
            "config": {
                "type": "evidently:metric_v2:ValueDrift",
                "column": "TEST_FEATURE",
                "method": "K-S p_value",
                "threshold": 0.05,
            },
            "value": invalid_score,
        },
    ]

    with pytest.raises(
        ValueError,
        match="Score estatistico invalido|P-value",
    ):
        extract_feature_drift(
            metrics,
            ("TEST_FEATURE",),
        )


def test_extract_preserves_feature_order() -> None:
    metrics = [
        {
            "config": {
                "type": "evidently:metric_v2:ValueDrift",
                "column": feature,
                "method": "K-S p_value",
                "threshold": 0.05,
            },
            "value": 0.01,
        }
        for feature in ("B", "A")
    ]

    result = extract_feature_drift(metrics, ("A", "B"))

    assert tuple(item.feature for item in result) == ("A", "B")


def test_evidently_mixed_feature_types() -> None:
    rng = np.random.default_rng(642)
    size = 1000

    reference = pd.DataFrame(
        {
            "AMT_CREDIT": rng.normal(200000, 30000, size),
            "NAME_INCOME_TYPE": rng.choice(
                ["Working", "Pensioner", "State servant"],
                size=size,
                p=[0.65, 0.25, 0.10],
            ),
            "FLAG_OWN_CAR": rng.choice(
                ["Y", "N"],
                size=size,
                p=[0.40, 0.60],
            ),
        }
    )

    production = pd.DataFrame(
        {
            "AMT_CREDIT": rng.normal(250000, 30000, size),
            "NAME_INCOME_TYPE": rng.choice(
                ["Working", "Pensioner", "State servant"],
                size=size,
                p=[0.30, 0.50, 0.20],
            ),
            "FLAG_OWN_CAR": rng.choice(
                ["Y", "N"],
                size=size,
                p=[0.75, 0.25],
            ),
        }
    )

    features = tuple(reference.columns)

    _, results = run_evidently_drift(
        reference,
        production,
        features,
    )

    assert len(results) == 3

    methods = {item.feature: item.method for item in results}

    assert methods["AMT_CREDIT"] == "K-S p_value"
    assert methods["NAME_INCOME_TYPE"] == "chi-square p_value"
    assert methods["FLAG_OWN_CAR"] == "Z-test p_value"

    assert all(item.drift_detected for item in results)


def test_evidently_rejects_incompatible_feature_types() -> None:
    reference = pd.DataFrame({"AMT_CREDIT": [100.0, 200.0]})
    production = pd.DataFrame({"AMT_CREDIT": ["100", "200"]})

    with pytest.raises(ValueError, match="Tipos incompatíveis"):
        run_evidently_drift(
            reference,
            production,
            ("AMT_CREDIT",),
        )


@pytest.mark.parametrize(
    ("method", "score", "threshold", "expected"),
    [
        ("Wasserstein distance (normed)", 0.03, 0.1, False),
        ("Wasserstein distance (normed)", 0.25, 0.1, True),
        ("Wasserstein distance (normed)", 1.25, 0.1, True),
        ("Jensen-Shannon distance", 0.02, 0.1, False),
        ("Jensen-Shannon distance", 0.30, 0.1, True),
        ("K-S p_value", 0.001, 0.05, True),
        ("K-S p_value", 0.20, 0.05, False),
    ],
)
def test_extract_interprets_method_direction(
    method: str,
    score: float,
    threshold: float,
    expected: bool,
) -> None:
    metrics = [
        {
            "config": {
                "type": "evidently:metric_v2:ValueDrift",
                "column": "TEST_FEATURE",
                "method": method,
                "threshold": threshold,
            },
            "value": score,
        }
    ]

    result = extract_feature_drift(
        metrics,
        ("TEST_FEATURE",),
    )

    assert result[0].method == method
    assert result[0].score == score
    assert result[0].drift_detected is expected


def test_extract_rejects_nonfinite_distance() -> None:
    metrics = [
        {
            "config": {
                "type": "evidently:metric_v2:ValueDrift",
                "column": "TEST_FEATURE",
                "method": "Wasserstein distance (normed)",
                "threshold": 0.1,
            },
            "value": float("inf"),
        }
    ]

    with pytest.raises(ValueError, match="Score"):
        extract_feature_drift(
            metrics,
            ("TEST_FEATURE",),
        )


def test_feature_result_serializes_numpy_scalars() -> None:
    result = FeatureDriftResult(
        feature="AMT_CREDIT",
        method="Wasserstein distance (normed)",
        score=np.float64(0.37),
        threshold=np.float64(0.1),
        drift_detected=np.bool_(True),
    )

    payload = result.to_dict()

    assert type(payload["score"]) is float
    assert type(payload["threshold"]) is float
    assert type(payload["drift_detected"]) is bool

    json.dumps(payload, allow_nan=False)


def test_monitoring_calls_evidently_once():
    """O monitoramento nao pode executar drift duas vezes."""
    import ast
    from pathlib import Path

    source = Path("src/credit_risk_monitoring/drift/monitoring.py").read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source)

    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "monitor_production_batch"
    ]

    assert len(functions) == 1

    calls = [
        node
        for node in ast.walk(functions[0])
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_evidently_drift"
    ]

    assert len(calls) == 1, (
        "monitor_production_batch deve chamar run_evidently_drift exatamente uma vez."
    )

"""Testes dos resultados agregados de data drift."""

import json

import numpy as np
import pytest

from credit_risk_monitoring.drift.detection import (
    FeatureDriftResult,
)
from credit_risk_monitoring.drift.results import (
    build_drift_summary,
)


@pytest.fixture
def sample_features() -> tuple[FeatureDriftResult, ...]:
    return (
        FeatureDriftResult(
            feature="AMT_CREDIT",
            method="Wasserstein distance (normed)",
            score=0.37,
            threshold=0.1,
            drift_detected=True,
        ),
        FeatureDriftResult(
            feature="AMT_INCOME_TOTAL",
            method="Wasserstein distance (normed)",
            score=0.33,
            threshold=0.1,
            drift_detected=True,
        ),
        FeatureDriftResult(
            feature="AMT_ANNUITY",
            method="Wasserstein distance (normed)",
            score=0.01,
            threshold=0.1,
            drift_detected=False,
        ),
    )


def test_build_drift_summary_counts_features(
    sample_features: tuple[FeatureDriftResult, ...],
) -> None:
    result = build_drift_summary(
        batch_id="test-strong",
        scenario_id="strong",
        reference_rows=30751,
        production_rows=46127,
        feature_results=sample_features,
    )

    assert result.features_analyzed == 3
    assert result.features_drifted == 2
    assert result.drift_share == pytest.approx(2 / 3)
    assert result.drift_detected


def test_summary_without_drift() -> None:
    features = (
        FeatureDriftResult(
            feature="AMT_CREDIT",
            method="Wasserstein distance (normed)",
            score=0.01,
            threshold=0.1,
            drift_detected=False,
        ),
    )

    result = build_drift_summary(
        batch_id="test-control",
        scenario_id="control",
        reference_rows=100,
        production_rows=100,
        feature_results=features,
    )

    assert result.features_drifted == 0
    assert result.drift_share == 0.0
    assert not result.drift_detected


def test_summary_is_json_serializable(
    sample_features: tuple[FeatureDriftResult, ...],
) -> None:
    result = build_drift_summary(
        batch_id="test-strong",
        scenario_id="strong",
        reference_rows=30751,
        production_rows=46127,
        feature_results=sample_features,
    )

    payload = result.to_dict()

    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
    )

    decoded = json.loads(encoded)

    assert decoded["drift"]["features_drifted"] == 2
    assert len(decoded["drift"]["feature_results"]) == 3
    assert "SK_ID_CURR" not in encoded
    assert "TARGET" not in encoded


@pytest.mark.parametrize(
    ("batch_id", "scenario_id"),
    [
        ("", "strong"),
        ("test", ""),
        ("   ", "strong"),
    ],
)
def test_rejects_invalid_identifiers(
    batch_id: str,
    scenario_id: str,
    sample_features: tuple[FeatureDriftResult, ...],
) -> None:
    with pytest.raises(ValueError):
        build_drift_summary(
            batch_id=batch_id,
            scenario_id=scenario_id,
            reference_rows=100,
            production_rows=100,
            feature_results=sample_features,
        )


def test_rejects_duplicate_features(
    sample_features: tuple[FeatureDriftResult, ...],
) -> None:
    duplicate = (sample_features[0], sample_features[0])

    with pytest.raises(ValueError, match="duplicadas"):
        build_drift_summary(
            batch_id="test",
            scenario_id="strong",
            reference_rows=100,
            production_rows=100,
            feature_results=duplicate,
        )


def test_rejects_empty_results() -> None:
    with pytest.raises(ValueError, match="vazios"):
        build_drift_summary(
            batch_id="test",
            scenario_id="control",
            reference_rows=100,
            production_rows=100,
            feature_results=(),
        )


@pytest.mark.parametrize("invalid_rows", [0, -1, True])
def test_rejects_invalid_row_counts(
    invalid_rows: int,
    sample_features: tuple[FeatureDriftResult, ...],
) -> None:
    with pytest.raises(ValueError):
        build_drift_summary(
            batch_id="test",
            scenario_id="strong",
            reference_rows=invalid_rows,
            production_rows=100,
            feature_results=sample_features,
        )


def test_drift_summary_serializes_numpy_booleans() -> None:
    features = (
        FeatureDriftResult(
            feature="AMT_CREDIT",
            method="Wasserstein distance (normed)",
            score=np.float64(0.37),
            threshold=np.float64(0.1),
            drift_detected=np.bool_(True),
        ),
        FeatureDriftResult(
            feature="AMT_INCOME_TOTAL",
            method="Wasserstein distance (normed)",
            score=np.float64(0.01),
            threshold=np.float64(0.1),
            drift_detected=np.bool_(False),
        ),
    )

    summary = build_drift_summary(
        batch_id="numpy-regression",
        scenario_id="strong",
        reference_rows=30751,
        production_rows=46127,
        feature_results=features,
    )

    payload = summary.to_dict()

    assert type(payload["drift"]["features_drifted"]) is int
    assert type(payload["drift"]["drift_share"]) is float
    assert type(payload["drift"]["drift_detected"]) is bool

    assert payload["drift"]["features_drifted"] == 1
    assert payload["drift"]["drift_share"] == 0.5

    encoded = json.dumps(payload, allow_nan=False)
    assert len(json.loads(encoded)["drift"]["feature_results"]) == 2

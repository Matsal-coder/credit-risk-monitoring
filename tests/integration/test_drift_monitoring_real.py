"""Testes da integracao entre qualidade, scoring e drift."""

import json
from pathlib import Path

import pandas as pd
import pytest

from credit_risk_monitoring.drift import monitoring
from credit_risk_monitoring.drift.detection import FeatureDriftResult
from credit_risk_monitoring.drift.simulation import reconstruct_raw_batch

REFERENCE_PATH = Path("data/processed/reference.csv")
PRODUCTION_PATH = Path("data/processed/test.csv")
MODEL_PATH = Path("artifacts/baseline_model.joblib")


@pytest.fixture
def real_batches() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carrega pequenas amostras das particoes existentes."""
    paths = (REFERENCE_PATH, PRODUCTION_PATH, MODEL_PATH)

    if not all(path.is_file() for path in paths):
        pytest.skip("Artefatos reais nao disponiveis.")

    reference = pd.read_csv(REFERENCE_PATH, nrows=8)
    production_prepared = pd.read_csv(
        PRODUCTION_PATH,
        nrows=8,
    )

    production_raw = reconstruct_raw_batch(production_prepared)

    assert set(reference["SK_ID_CURR"]).isdisjoint(set(production_raw["SK_ID_CURR"]))

    return reference, production_raw


def fake_evidently(
    reference: pd.DataFrame,
    production: pd.DataFrame,
    features: tuple[str, ...],
) -> tuple[object, tuple[FeatureDriftResult, ...]]:
    """Retorna resultado controlado para testar orquestracao."""
    assert len(reference) == 8
    assert len(production) == 8
    assert len(features) == 16

    feature_results = tuple(
        FeatureDriftResult(
            feature=feature,
            method="Wasserstein distance (normed)",
            score=0.2 if feature == "AMT_CREDIT" else 0.01,
            threshold=0.1,
            drift_detected=feature == "AMT_CREDIT",
        )
        for feature in features
    )

    return object(), feature_results


def test_valid_batch_runs_scoring_and_drift(
    real_batches: tuple[pd.DataFrame, pd.DataFrame],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference, production = real_batches

    monkeypatch.setattr(
        monitoring,
        "run_evidently_drift",
        fake_evidently,
    )

    result = monitoring.monitor_production_batch(
        reference,
        production,
        batch_id="integration-valid",
        scenario_id="control",
        model_path=MODEL_PATH,
    )

    assert result.approved
    assert result.inference.scored_rows == 8
    assert len(result.inference.probabilities) == 8
    assert all(0 <= score <= 1 for score in result.inference.probabilities)

    assert result.drift is not None
    assert result.drift.features_analyzed == 16
    assert result.drift.features_drifted == 1
    assert result.drift.drift_detected
    assert result.snapshot is not None


def test_invalid_batch_blocks_scoring_and_drift(
    real_batches: tuple[pd.DataFrame, pd.DataFrame],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference, production = real_batches

    invalid = production.copy()
    invalid.loc[invalid.index[0], "AMT_CREDIT"] = -100.0

    def forbidden_drift(*args, **kwargs):
        raise AssertionError("Evidently nao deveria executar.")

    monkeypatch.setattr(
        monitoring,
        "run_evidently_drift",
        forbidden_drift,
    )

    result = monitoring.monitor_production_batch(
        reference,
        invalid,
        batch_id="integration-rejected",
        scenario_id="invalid",
        model_path=MODEL_PATH,
    )

    assert not result.approved
    assert result.inference.status == "rejected"
    assert result.inference.scored_rows == 0
    assert result.drift is None
    assert result.snapshot is None


def test_overlap_is_rejected_before_scoring(
    real_batches: tuple[pd.DataFrame, pd.DataFrame],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference, production = real_batches

    overlapping = production.copy()
    overlapping.loc[overlapping.index[0], "SK_ID_CURR"] = reference.iloc[0][
        "SK_ID_CURR"
    ]

    def forbidden_scoring(*args, **kwargs):
        raise AssertionError("Scoring nao deveria executar.")

    monkeypatch.setattr(
        monitoring,
        "run_quality_gated_inference",
        forbidden_scoring,
    )

    with pytest.raises(ValueError, match="Sobreposicao"):
        monitoring.monitor_production_batch(
            reference,
            overlapping,
            batch_id="integration-overlap",
            scenario_id="control",
            model_path=MODEL_PATH,
        )


def test_invalid_reference_is_rejected(
    real_batches: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    reference, production = real_batches

    invalid_reference = reference.copy()
    invalid_reference.loc[invalid_reference.index[0], "AMT_CREDIT"] = -100.0

    with pytest.raises(ValueError, match="Pandera"):
        monitoring.monitor_production_batch(
            invalid_reference,
            production,
            batch_id="integration-invalid-reference",
            scenario_id="control",
            model_path=MODEL_PATH,
        )


def test_monitoring_json_has_no_individual_scores(
    real_batches: tuple[pd.DataFrame, pd.DataFrame],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference, production = real_batches

    monkeypatch.setattr(
        monitoring,
        "run_evidently_drift",
        fake_evidently,
    )

    result = monitoring.monitor_production_batch(
        reference,
        production,
        batch_id="integration-json",
        scenario_id="control",
        model_path=MODEL_PATH,
    )

    payload = result.to_dict()

    encoded = json.dumps(payload, allow_nan=False)

    assert payload["execution_status"] == "completed"
    assert payload["quality_status"] == "approved"
    assert payload["drift"]["features_analyzed"] == 16

    assert "probabilities" not in encoded
    assert "predictions" not in encoded
    assert "SK_ID_CURR" not in encoded
    assert "TARGET" not in encoded

"""Testes da inferencia com barreira bloqueante de qualidade."""

from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from credit_risk_monitoring.data.preparation import MODEL_FEATURES
from credit_risk_monitoring.modeling.inference import (
    load_baseline_model,
    run_quality_gated_inference,
)
from credit_risk_monitoring.quality.results import (
    QualityViolation,
    ValidationResult,
)
from credit_risk_monitoring.quality.validation import (
    validate_batch,
)


@pytest.fixture
def raw_batch() -> pd.DataFrame:
    """Lote bruto sintetico sem TARGET."""
    return pd.DataFrame(
        {
            "SK_ID_CURR": [100001, 100002],
            "AMT_CREDIT": [450000.0, 300000.0],
            "AMT_INCOME_TOTAL": [180000.0, 120000.0],
            "AMT_ANNUITY": [25000.0, 18000.0],
            "AMT_GOODS_PRICE": [400000.0, 280000.0],
            "EXT_SOURCE_2": [0.55, 0.60],
            "EXT_SOURCE_3": [0.65, np.nan],
            "DAYS_BIRTH": [-12000, -16000],
            "DAYS_EMPLOYED": [-2000.0, 365243.0],
            "DAYS_REGISTRATION": [-3000.0, -5000.0],
            "CNT_CHILDREN": [1, 0],
            "CNT_FAM_MEMBERS": [3.0, 2.0],
            "NAME_INCOME_TYPE": ["Working", "Pensioner"],
            "NAME_EDUCATION_TYPE": [
                "Higher education",
                "Secondary / secondary special",
            ],
            "FLAG_OWN_CAR": ["N", "Y"],
            "FLAG_OWN_REALTY": ["Y", "N"],
            "NAME_CONTRACT_TYPE": [
                "Cash loans",
                "Revolving loans",
            ],
        }
    )


@pytest.fixture
def mock_model() -> Mock:
    """Pipeline simulado com probabilidades conhecidas."""
    model = Mock()
    model.predict_proba.return_value = np.array(
        [
            [0.80, 0.20],
            [0.10, 0.90],
        ]
    )
    return model


def test_valid_batch_calls_predict_proba_once(
    raw_batch: pd.DataFrame,
    mock_model: Mock,
) -> None:
    with patch(
        "credit_risk_monitoring.modeling.inference.load_baseline_model",
        return_value=(mock_model, 0.50),
    ) as loader:
        result = run_quality_gated_inference(
            raw_batch,
            batch_id="valid-batch",
        )

    assert result.approved
    assert result.scored_rows == 2
    assert result.threshold == 0.50
    assert result.probabilities == pytest.approx((0.20, 0.90))
    assert result.predictions == (0, 1)

    assert len(result.validations) == 2
    assert all(item.approved for item in result.validations)

    loader.assert_called_once()
    mock_model.predict_proba.assert_called_once()

    features = mock_model.predict_proba.call_args.args[0]

    assert list(features.columns) == list(MODEL_FEATURES)
    assert features.shape == (2, 17)
    assert "SK_ID_CURR" not in features.columns
    assert "TARGET" not in features.columns


def test_raw_rejection_does_not_load_or_call_model(
    raw_batch: pd.DataFrame,
    mock_model: Mock,
) -> None:
    raw_batch.loc[0, "AMT_CREDIT"] = -100.0

    with patch(
        "credit_risk_monitoring.modeling.inference.load_baseline_model",
        return_value=(mock_model, 0.50),
    ) as loader:
        result = run_quality_gated_inference(
            raw_batch,
            batch_id="invalid-raw",
        )

    assert not result.approved
    assert result.scored_rows == 0
    assert result.probabilities == ()
    assert result.predictions == ()
    assert result.threshold is None

    assert len(result.validations) == 1
    assert result.validations[0].stage == "raw_inference"

    loader.assert_not_called()
    mock_model.predict_proba.assert_not_called()


def test_prepared_rejection_does_not_call_model(
    raw_batch: pd.DataFrame,
    mock_model: Mock,
) -> None:
    """Simula falha no segundo contrato apos raw aprovado."""
    original_validate = validate_batch

    def validate_with_prepared_rejection(
        df: pd.DataFrame,
        stage: str,
        batch_id: str,
    ) -> ValidationResult:
        if stage == "prepared_inference":
            return ValidationResult(
                batch_id=batch_id,
                stage="prepared_inference",
                status="rejected",
                total_rows=len(df),
                violations=(
                    QualityViolation(
                        column="DAYS_EMPLOYED_SENTINEL",
                        rule="valid_employment_indicator",
                        count=1,
                    ),
                ),
            )

        return original_validate(df, stage, batch_id)

    with (
        patch(
            "credit_risk_monitoring.modeling.inference.validate_batch",
            side_effect=validate_with_prepared_rejection,
        ),
        patch(
            "credit_risk_monitoring.modeling.inference.load_baseline_model",
            return_value=(mock_model, 0.50),
        ) as loader,
    ):
        result = run_quality_gated_inference(
            raw_batch,
            batch_id="invalid-prepared",
        )

    assert not result.approved
    assert result.scored_rows == 0
    assert result.probabilities == ()
    assert result.predictions == ()
    assert len(result.validations) == 2
    assert result.validations[0].approved
    assert not result.validations[1].approved

    loader.assert_not_called()
    mock_model.predict_proba.assert_not_called()


def test_threshold_from_loaded_model_is_respected(
    raw_batch: pd.DataFrame,
    mock_model: Mock,
) -> None:
    with patch(
        "credit_risk_monitoring.modeling.inference.load_baseline_model",
        return_value=(mock_model, 0.75),
    ):
        result = run_quality_gated_inference(
            raw_batch,
            batch_id="threshold-check",
        )

    assert result.approved
    assert result.threshold == 0.75
    assert result.predictions == (0, 1)


def test_scores_are_omitted_from_default_payload(
    raw_batch: pd.DataFrame,
    mock_model: Mock,
) -> None:
    with patch(
        "credit_risk_monitoring.modeling.inference.load_baseline_model",
        return_value=(mock_model, 0.50),
    ):
        result = run_quality_gated_inference(
            raw_batch,
            batch_id="privacy-check",
        )

    payload = result.to_dict()

    assert "probabilities" not in payload
    assert "predictions" not in payload
    assert "SK_ID_CURR" not in payload

    detailed = result.to_dict(include_scores=True)

    assert detailed["probabilities"] == pytest.approx([0.20, 0.90])
    assert detailed["predictions"] == [0, 1]


@pytest.mark.parametrize(
    "invalid_probabilities",
    [
        np.array([[0.8, 0.2]]),
        np.array([[0.8, np.nan], [0.1, 0.9]]),
        np.array([[0.8, 0.2], [-0.1, 1.1]]),
        np.array([[0.8, 0.3], [0.1, 0.9]]),
    ],
)
def test_invalid_model_probabilities_raise_error(
    raw_batch: pd.DataFrame,
    mock_model: Mock,
    invalid_probabilities: np.ndarray,
) -> None:
    mock_model.predict_proba.return_value = invalid_probabilities

    with patch(
        "credit_risk_monitoring.modeling.inference.load_baseline_model",
        return_value=(mock_model, 0.50),
    ):
        with pytest.raises(ValueError, match="probabilidades|Probabilidades"):
            run_quality_gated_inference(
                raw_batch,
                batch_id="invalid-probabilities",
            )


def test_missing_model_raises_operational_error(
    raw_batch: pd.DataFrame,
) -> None:
    with patch(
        "credit_risk_monitoring.modeling.inference.load_baseline_model",
        side_effect=FileNotFoundError("model unavailable"),
    ):
        with pytest.raises(FileNotFoundError):
            run_quality_gated_inference(
                raw_batch,
                batch_id="missing-model",
            )


def test_invalid_raw_input_does_not_load_model(
    mock_model: Mock,
) -> None:
    with patch(
        "credit_risk_monitoring.modeling.inference.load_baseline_model",
        return_value=(mock_model, 0.50),
    ) as loader:
        with pytest.raises(TypeError, match="DataFrame"):
            run_quality_gated_inference(
                {"AMT_CREDIT": -100},
                batch_id="invalid-input",
            )

    loader.assert_not_called()


@pytest.mark.parametrize(
    "invalid_threshold",
    [None, True, "0.5", -0.1, 1.5, float("nan")],
)
def test_invalid_artifact_threshold_is_rejected(
    invalid_threshold: object,
) -> None:
    model = Mock()
    model.classes_ = np.array([0, 1])

    artifact = {
        "pipeline": model,
        "metadata": {
            "model_type": "LogisticRegression",
            "model_features": list(MODEL_FEATURES),
            "feature_count": len(MODEL_FEATURES),
            "threshold": invalid_threshold,
        },
    }

    with (
        patch(
            "credit_risk_monitoring.modeling.inference.joblib.load",
            return_value=artifact,
        ),
        patch(
            "credit_risk_monitoring.modeling.inference.check_is_fitted",
        ),
    ):
        with pytest.raises(ValueError, match="Threshold"):
            load_baseline_model(Path("synthetic-model.joblib"))


def test_unexpected_model_classes_are_rejected() -> None:
    model = Mock()
    model.classes_ = np.array([1, 0])

    artifact = {
        "pipeline": model,
        "metadata": {
            "model_type": "LogisticRegression",
            "model_features": list(MODEL_FEATURES),
            "feature_count": len(MODEL_FEATURES),
            "threshold": 0.50,
        },
    }

    with (
        patch(
            "credit_risk_monitoring.modeling.inference.joblib.load",
            return_value=artifact,
        ),
        patch(
            "credit_risk_monitoring.modeling.inference.check_is_fitted",
        ),
    ):
        with pytest.raises(ValueError, match="Classes"):
            load_baseline_model(Path("synthetic-model.joblib"))

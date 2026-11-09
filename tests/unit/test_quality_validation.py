"""Testes do servico de validacao e seus resultados."""

import json
from unittest.mock import patch

import pandas as pd
import pytest

from credit_risk_monitoring.quality.results import (
    QualityViolation,
    ValidationResult,
)
from credit_risk_monitoring.quality.validation import validate_batch


@pytest.fixture
def valid_batch() -> pd.DataFrame:
    """Lote bruto sintetico para validacao."""
    return pd.DataFrame(
        {
            "SK_ID_CURR": [100001, 100002],
            "AMT_CREDIT": [450000.0, 300000.0],
            "AMT_INCOME_TOTAL": [180000.0, 120000.0],
            "AMT_ANNUITY": [25000.0, 18000.0],
            "AMT_GOODS_PRICE": [400000.0, 280000.0],
            "EXT_SOURCE_2": [0.55, 0.60],
            "EXT_SOURCE_3": [0.65, None],
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
            "NAME_CONTRACT_TYPE": ["Cash loans", "Revolving loans"],
        }
    )


def test_valid_batch_returns_approved(
    valid_batch: pd.DataFrame,
) -> None:
    result = validate_batch(
        valid_batch,
        stage="raw_inference",
        batch_id="valid-batch",
    )

    assert result.approved
    assert result.status == "approved"
    assert result.total_rows == 2
    assert result.violation_count == 0
    assert result.violations == ()


def test_invalid_credit_returns_specific_violation(
    valid_batch: pd.DataFrame,
) -> None:
    valid_batch.loc[0, "AMT_CREDIT"] = -100.0

    result = validate_batch(
        valid_batch,
        stage="raw_inference",
        batch_id="negative-credit",
    )

    assert not result.approved
    assert result.status == "rejected"
    assert any(
        violation.column == "AMT_CREDIT" and violation.rule == "positive_credit"
        for violation in result.violations
    )


def test_multiple_invalid_rows_are_aggregated(
    valid_batch: pd.DataFrame,
) -> None:
    valid_batch["AMT_CREDIT"] = [-100.0, -200.0]

    result = validate_batch(
        valid_batch,
        stage="raw_inference",
        batch_id="multiple-errors",
    )

    assert not result.approved

    credit_violations = [
        violation
        for violation in result.violations
        if violation.column == "AMT_CREDIT" and violation.rule == "positive_credit"
    ]

    assert len(credit_violations) == 1
    assert credit_violations[0].count == 2
    assert result.violation_count >= 2


def test_missing_column_returns_structural_violation(
    valid_batch: pd.DataFrame,
) -> None:
    invalid = valid_batch.drop(columns=["AMT_CREDIT"])

    result = validate_batch(
        invalid,
        stage="raw_inference",
        batch_id="missing-column",
    )

    assert not result.approved
    assert any(
        violation.rule == "column_in_dataframe" for violation in result.violations
    )


def test_result_is_json_serializable(
    valid_batch: pd.DataFrame,
) -> None:
    result = validate_batch(
        valid_batch,
        stage="raw_inference",
        batch_id="json-check",
    )

    serialized = json.dumps(result.to_dict())

    assert '"status": "approved"' in serialized


def test_invalid_result_does_not_expose_customer_values(
    valid_batch: pd.DataFrame,
) -> None:
    valid_batch.loc[0, "AMT_CREDIT"] = -987654321.0

    result = validate_batch(
        valid_batch,
        stage="raw_inference",
        batch_id="privacy-check",
    )

    serialized = json.dumps(result.to_dict())

    assert not result.approved
    assert "987654321" not in serialized
    assert "100001" not in serialized


@pytest.mark.parametrize(
    "stage",
    ["unknown", "", "training"],
)
def test_unknown_stage_raises_value_error(
    valid_batch: pd.DataFrame,
    stage: str,
) -> None:
    with pytest.raises(ValueError, match="Estagio"):
        validate_batch(
            valid_batch,
            stage=stage,
            batch_id="invalid-stage",
        )


@pytest.mark.parametrize(
    "batch_id",
    ["", "   ", None, 123],
)
def test_invalid_batch_id_raises_value_error(
    valid_batch: pd.DataFrame,
    batch_id: object,
) -> None:
    with pytest.raises(ValueError, match="batch_id"):
        validate_batch(
            valid_batch,
            stage="raw_inference",
            batch_id=batch_id,
        )


def test_non_dataframe_input_raises_type_error() -> None:
    with pytest.raises(TypeError, match="DataFrame"):
        validate_batch(
            {"AMT_CREDIT": -100},
            stage="raw_inference",
            batch_id="invalid-input",
        )


def test_unexpected_operational_error_is_propagated(
    valid_batch: pd.DataFrame,
) -> None:
    with patch(
        "credit_risk_monitoring.quality.validation.RAW_INFERENCE_SCHEMA.validate",
        side_effect=RuntimeError("unexpected failure"),
    ):
        with pytest.raises(RuntimeError, match="unexpected failure"):
            validate_batch(
                valid_batch,
                stage="raw_inference",
                batch_id="operational-failure",
            )


def test_violation_result_properties() -> None:
    result = ValidationResult(
        batch_id="test-result",
        stage="raw_inference",
        status="rejected",
        total_rows=10,
        violations=(
            QualityViolation(
                column="AMT_CREDIT",
                rule="positive_credit",
                count=3,
            ),
            QualityViolation(
                column="EXT_SOURCE_2",
                rule="external_score_range",
                count=2,
            ),
        ),
    )

    assert not result.approved
    assert result.violation_count == 5

    payload = result.to_dict()

    assert payload["status"] == "rejected"
    assert len(payload["violations"]) == 2
    assert payload["violations"][0]["severity"] == "error"

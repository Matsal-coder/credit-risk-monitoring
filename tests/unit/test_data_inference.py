"""Testes da preparacao de dados para inferencia."""

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from credit_risk_monitoring.data.inference import (
    prepare_inference_features,
)
from credit_risk_monitoring.data.preparation import (
    ID_COLUMN,
    MODEL_FEATURES,
    TARGET_COLUMN,
    prepare_features,
)


@pytest.fixture
def raw_batch() -> pd.DataFrame:
    """Dois registros sinteticos sem TARGET."""
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


def test_prepared_columns_and_order(
    raw_batch: pd.DataFrame,
) -> None:
    result = prepare_inference_features(raw_batch)

    assert list(result.columns) == [ID_COLUMN, *MODEL_FEATURES]
    assert TARGET_COLUMN not in result.columns
    assert len(result) == 2


def test_employment_sentinel_is_replaced(
    raw_batch: pd.DataFrame,
) -> None:
    result = prepare_inference_features(raw_batch)

    assert result["DAYS_EMPLOYED_SENTINEL"].tolist() == [0, 1]
    assert result.loc[0, "DAYS_EMPLOYED"] == -2000.0
    assert pd.isna(result.loc[1, "DAYS_EMPLOYED"])
    assert result["DAYS_EMPLOYED_SENTINEL"].dtype == "int8"


def test_original_null_is_not_marked_as_sentinel(
    raw_batch: pd.DataFrame,
) -> None:
    raw_batch.loc[0, "DAYS_EMPLOYED"] = np.nan

    result = prepare_inference_features(raw_batch)

    assert pd.isna(result.loc[0, "DAYS_EMPLOYED"])
    assert result.loc[0, "DAYS_EMPLOYED_SENTINEL"] == 0


def test_preparation_does_not_modify_input(
    raw_batch: pd.DataFrame,
) -> None:
    original = raw_batch.copy(deep=True)

    prepare_inference_features(raw_batch)

    assert_frame_equal(raw_batch, original)


def test_inference_matches_historical_preparation(
    raw_batch: pd.DataFrame,
) -> None:
    """Compara os dois caminhos sobre os mesmos registros."""
    labeled = raw_batch.copy()
    labeled[TARGET_COLUMN] = [0, 1]

    historical = prepare_features(labeled)
    inference = prepare_inference_features(raw_batch)

    expected = historical.drop(columns=[TARGET_COLUMN])

    assert_frame_equal(inference, expected)


def test_target_is_rejected(
    raw_batch: pd.DataFrame,
) -> None:
    raw_batch[TARGET_COLUMN] = [0, 1]

    with pytest.raises(ValueError, match="TARGET"):
        prepare_inference_features(raw_batch)


def test_missing_column_is_rejected(
    raw_batch: pd.DataFrame,
) -> None:
    invalid = raw_batch.drop(columns=["AMT_CREDIT"])

    with pytest.raises(ValueError, match="Colunas"):
        prepare_inference_features(invalid)


def test_unexpected_column_is_rejected(
    raw_batch: pd.DataFrame,
) -> None:
    raw_batch["UNEXPECTED_COLUMN"] = 1

    with pytest.raises(ValueError, match="Colunas"):
        prepare_inference_features(raw_batch)


def test_empty_batch_is_rejected(
    raw_batch: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="vazio"):
        prepare_inference_features(raw_batch.iloc[0:0])


def test_non_dataframe_is_rejected() -> None:
    with pytest.raises(TypeError, match="DataFrame"):
        prepare_inference_features({"AMT_CREDIT": 100})

"""Testes dos contratos Pandera de inferencia."""

import numpy as np
import pandas as pd
import pytest
from pandera.errors import SchemaError, SchemaErrors

from credit_risk_monitoring.quality.contracts import (
    PREPARED_INFERENCE_SCHEMA,
    RAW_INFERENCE_SCHEMA,
)

VALIDATION_ERRORS = (SchemaError, SchemaErrors)


@pytest.fixture
def raw_batch() -> pd.DataFrame:
    """Lote bruto sintetico com um cliente valido."""
    return pd.DataFrame(
        {
            "SK_ID_CURR": [100001],
            "AMT_CREDIT": [450000.0],
            "AMT_INCOME_TOTAL": [180000.0],
            "AMT_ANNUITY": [25000.0],
            "AMT_GOODS_PRICE": [400000.0],
            "EXT_SOURCE_2": [0.55],
            "EXT_SOURCE_3": [0.65],
            "DAYS_BIRTH": [-12000],
            "DAYS_EMPLOYED": [-2000.0],
            "DAYS_REGISTRATION": [-3000.0],
            "CNT_CHILDREN": [1],
            "CNT_FAM_MEMBERS": [3.0],
            "NAME_INCOME_TYPE": ["Working"],
            "NAME_EDUCATION_TYPE": ["Higher education"],
            "FLAG_OWN_CAR": ["N"],
            "FLAG_OWN_REALTY": ["Y"],
            "NAME_CONTRACT_TYPE": ["Cash loans"],
        }
    )


@pytest.fixture
def prepared_batch(raw_batch: pd.DataFrame) -> pd.DataFrame:
    """Lote sintetico apos transformacao da sentinela."""
    result = raw_batch.copy()
    result["DAYS_EMPLOYED_SENTINEL"] = pd.Series(
        [0],
        dtype="int8",
    )
    return result


def test_raw_batch_valid(raw_batch: pd.DataFrame) -> None:
    validated = RAW_INFERENCE_SCHEMA.validate(raw_batch, lazy=True)

    assert len(validated) == 1


def test_prepared_batch_valid(prepared_batch: pd.DataFrame) -> None:
    validated = PREPARED_INFERENCE_SCHEMA.validate(
        prepared_batch,
        lazy=True,
    )

    assert len(validated) == 1


def test_raw_employment_sentinel_is_allowed(
    raw_batch: pd.DataFrame,
) -> None:
    raw_batch["DAYS_EMPLOYED"] = 365243.0

    validated = RAW_INFERENCE_SCHEMA.validate(raw_batch, lazy=True)

    assert len(validated) == 1


def test_prepared_employment_sentinel_is_consistent(
    prepared_batch: pd.DataFrame,
) -> None:
    prepared_batch["DAYS_EMPLOYED"] = np.nan
    prepared_batch["DAYS_EMPLOYED_SENTINEL"] = 1

    validated = PREPARED_INFERENCE_SCHEMA.validate(
        prepared_batch,
        lazy=True,
    )

    assert len(validated) == 1


def test_legitimate_nulls_are_allowed(
    prepared_batch: pd.DataFrame,
) -> None:
    prepared_batch["EXT_SOURCE_3"] = np.nan
    prepared_batch["AMT_ANNUITY"] = np.nan
    prepared_batch["NAME_INCOME_TYPE"] = None

    validated = PREPARED_INFERENCE_SCHEMA.validate(
        prepared_batch,
        lazy=True,
    )

    assert len(validated) == 1


@pytest.mark.parametrize(
    ("column", "invalid_value"),
    [
        ("AMT_CREDIT", -100.0),
        ("AMT_INCOME_TOTAL", 0.0),
        ("EXT_SOURCE_2", 1.5),
        ("EXT_SOURCE_3", -0.1),
        ("DAYS_BIRTH", 100),
        ("CNT_CHILDREN", -1),
        ("FLAG_OWN_CAR", "INVALID"),
        ("NAME_CONTRACT_TYPE", "INVALID"),
    ],
)
def test_raw_semantic_violations_are_rejected(
    raw_batch: pd.DataFrame,
    column: str,
    invalid_value: object,
) -> None:
    raw_batch[column] = invalid_value

    with pytest.raises(VALIDATION_ERRORS):
        RAW_INFERENCE_SCHEMA.validate(raw_batch, lazy=True)


def test_duplicate_customer_ids_are_rejected(
    raw_batch: pd.DataFrame,
) -> None:
    duplicated = pd.concat(
        [raw_batch, raw_batch],
        ignore_index=True,
    )

    with pytest.raises(VALIDATION_ERRORS):
        RAW_INFERENCE_SCHEMA.validate(duplicated, lazy=True)


def test_missing_required_column_is_rejected(
    raw_batch: pd.DataFrame,
) -> None:
    invalid = raw_batch.drop(columns=["AMT_CREDIT"])

    with pytest.raises(VALIDATION_ERRORS):
        RAW_INFERENCE_SCHEMA.validate(invalid, lazy=True)


def test_extra_column_is_rejected(
    raw_batch: pd.DataFrame,
) -> None:
    raw_batch["UNEXPECTED_COLUMN"] = 123

    with pytest.raises(VALIDATION_ERRORS):
        RAW_INFERENCE_SCHEMA.validate(raw_batch, lazy=True)


def test_empty_batch_is_rejected(raw_batch: pd.DataFrame) -> None:
    empty = raw_batch.iloc[0:0].copy()

    with pytest.raises(VALIDATION_ERRORS):
        RAW_INFERENCE_SCHEMA.validate(empty, lazy=True)


@pytest.mark.parametrize("invalid_value", [-1, 2])
def test_invalid_employment_indicator_is_rejected(
    prepared_batch: pd.DataFrame,
    invalid_value: int,
) -> None:
    prepared_batch["DAYS_EMPLOYED_SENTINEL"] = invalid_value

    with pytest.raises(VALIDATION_ERRORS):
        PREPARED_INFERENCE_SCHEMA.validate(
            prepared_batch,
            lazy=True,
        )


def test_inconsistent_employment_sentinel_is_rejected(
    prepared_batch: pd.DataFrame,
) -> None:
    prepared_batch["DAYS_EMPLOYED_SENTINEL"] = 1
    prepared_batch["DAYS_EMPLOYED"] = -2000.0

    with pytest.raises(VALIDATION_ERRORS):
        PREPARED_INFERENCE_SCHEMA.validate(
            prepared_batch,
            lazy=True,
        )


def test_prepared_positive_employment_days_are_rejected(
    prepared_batch: pd.DataFrame,
) -> None:
    prepared_batch["DAYS_EMPLOYED"] = 365243.0

    with pytest.raises(VALIDATION_ERRORS):
        PREPARED_INFERENCE_SCHEMA.validate(
            prepared_batch,
            lazy=True,
        )

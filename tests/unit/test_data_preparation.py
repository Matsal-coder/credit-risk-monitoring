"""Testes da preparacao de dados e dos splits."""

import pandas as pd
import pytest

from credit_risk_monitoring.data.preparation import (
    MODEL_FEATURES,
    prepare_features,
    split_dataset,
    validate_partitions,
    validate_source,
)


@pytest.fixture
def sample_data():
    """Base sintetica pequena com ambas as classes."""

    n = 200

    return pd.DataFrame(
        {
            "SK_ID_CURR": range(100000, 100000 + n),
            "TARGET": [0] * 160 + [1] * 40,
            "AMT_CREDIT": [100000.0] * n,
            "AMT_INCOME_TOTAL": [50000.0] * n,
            "AMT_ANNUITY": [10000.0] * n,
            "AMT_GOODS_PRICE": [90000.0] * n,
            "EXT_SOURCE_2": [0.5] * n,
            "EXT_SOURCE_3": [0.6] * n,
            "DAYS_BIRTH": [-12000] * n,
            "DAYS_EMPLOYED": [-1000] * (n - 1) + [365243],
            "DAYS_REGISTRATION": [-2000.0] * n,
            "CNT_CHILDREN": [1] * n,
            "CNT_FAM_MEMBERS": [3.0] * n,
            "NAME_INCOME_TYPE": ["Working"] * n,
            "NAME_EDUCATION_TYPE": ["Higher education"] * n,
            "FLAG_OWN_CAR": ["N"] * n,
            "FLAG_OWN_REALTY": ["Y"] * n,
            "NAME_CONTRACT_TYPE": ["Cash loans"] * n,
        }
    )


def test_source_is_valid(sample_data):
    validate_source(sample_data)


def test_duplicate_ids_are_rejected(sample_data):
    sample_data.loc[1, "SK_ID_CURR"] = sample_data.loc[0, "SK_ID_CURR"]

    with pytest.raises(ValueError, match="duplicados"):
        validate_source(sample_data)


def test_invalid_target_is_rejected(sample_data):
    sample_data.loc[0, "TARGET"] = 2

    with pytest.raises(ValueError, match="apenas 0 e 1"):
        validate_source(sample_data)


def test_missing_feature_is_rejected(sample_data):
    sample_data = sample_data.drop(columns=["AMT_CREDIT"])

    with pytest.raises(ValueError, match="Colunas obrigatorias"):
        validate_source(sample_data)


def test_sentinel_is_replaced_and_flagged(sample_data):
    result = prepare_features(sample_data)

    last = result.iloc[-1]

    assert pd.isna(last["DAYS_EMPLOYED"])
    assert last["DAYS_EMPLOYED_SENTINEL"] == 1
    assert result["DAYS_EMPLOYED_SENTINEL"].sum() == 1


def test_model_features_exclude_target_and_id():
    assert "TARGET" not in MODEL_FEATURES
    assert "SK_ID_CURR" not in MODEL_FEATURES


def test_splits_are_deterministic(sample_data):
    first = split_dataset(sample_data)
    second = split_dataset(sample_data)

    for name in first:
        pd.testing.assert_frame_equal(first[name], second[name])


def test_splits_have_no_overlap(sample_data):
    partitions = split_dataset(sample_data)

    validate_partitions(partitions, expected_size=len(sample_data))

    all_ids = pd.concat([partition["SK_ID_CURR"] for partition in partitions.values()])

    assert all_ids.is_unique
    assert len(all_ids) == len(sample_data)


def test_split_proportions(sample_data):
    partitions = split_dataset(sample_data)

    assert len(partitions["train"]) == 120
    assert len(partitions["validation"]) == 30
    assert len(partitions["test"]) == 30
    assert len(partitions["reference"]) == 20


def test_splits_preserve_target_prevalence(sample_data):
    partitions = split_dataset(sample_data)

    expected = sample_data["TARGET"].mean()

    for partition in partitions.values():
        observed = partition["TARGET"].mean()
        assert abs(observed - expected) < 0.05

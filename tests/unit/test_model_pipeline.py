"""Testes do pipeline de preprocessamento e baseline."""

import numpy as np
import pandas as pd
import pytest
from sklearn.exceptions import NotFittedError

from credit_risk_monitoring.data.preparation import MODEL_FEATURES
from credit_risk_monitoring.modeling.pipeline import (
    build_baseline_pipeline,
    build_preprocessor,
)


@pytest.fixture
def sample_features():
    """Cria features sinteticas para verificar transformacoes."""

    n = 120

    return pd.DataFrame(
        {
            "AMT_CREDIT": np.linspace(50000, 250000, n),
            "AMT_INCOME_TOTAL": np.linspace(20000, 120000, n),
            "AMT_ANNUITY": np.linspace(5000, 25000, n),
            "AMT_GOODS_PRICE": np.linspace(45000, 230000, n),
            "EXT_SOURCE_2": np.linspace(0.1, 0.9, n),
            "EXT_SOURCE_3": np.linspace(0.2, 0.8, n),
            "DAYS_BIRTH": np.linspace(-20000, -8000, n),
            "DAYS_EMPLOYED": np.linspace(-10000, -100, n),
            "DAYS_REGISTRATION": np.linspace(-7000, -200, n),
            "CNT_CHILDREN": np.tile([0, 1, 2], 40),
            "CNT_FAM_MEMBERS": np.tile([1, 2, 3], 40),
            "NAME_INCOME_TYPE": np.tile(["Working", "Pensioner", "State servant"], 40),
            "NAME_EDUCATION_TYPE": np.tile(["Secondary", "Higher education"], 60),
            "FLAG_OWN_CAR": np.tile(["N", "Y"], 60),
            "FLAG_OWN_REALTY": np.tile(["Y", "N"], 60),
            "NAME_CONTRACT_TYPE": np.tile(["Cash loans", "Revolving loans"], 60),
            "DAYS_EMPLOYED_SENTINEL": np.zeros(n, dtype=int),
        }
    )


def test_preprocessor_is_not_fitted_initially(sample_features):
    preprocessor = build_preprocessor()

    with pytest.raises(NotFittedError):
        preprocessor.transform(sample_features)


def test_preprocessor_handles_missing_values(sample_features):
    features = sample_features.copy()

    features.loc[0, "AMT_INCOME_TOTAL"] = np.nan
    features.loc[1, "NAME_INCOME_TYPE"] = None

    preprocessor = build_preprocessor()
    result = preprocessor.fit_transform(features)

    dense = result.toarray() if hasattr(result, "toarray") else np.asarray(result)

    assert np.isfinite(dense).all()


def test_unknown_category_does_not_break_transform(sample_features):
    train = sample_features.iloc[:100].copy()
    test = sample_features.iloc[100:].copy()

    test.loc[100, "NAME_INCOME_TYPE"] = "UNKNOWN_CATEGORY"

    preprocessor = build_preprocessor()
    preprocessor.fit(train)

    transformed = preprocessor.transform(test)

    assert transformed.shape[0] == len(test)


def test_pipeline_produces_probabilities(sample_features):
    target = np.tile([0, 1], 60)

    model = build_baseline_pipeline()
    model.fit(sample_features, target)

    probabilities = model.predict_proba(sample_features)

    assert probabilities.shape == (len(sample_features), 2)
    assert np.isfinite(probabilities).all()
    assert ((probabilities >= 0) & (probabilities <= 1)).all()


def test_model_feature_contract(sample_features):
    assert list(sample_features.columns) == list(MODEL_FEATURES)


def test_preprocessing_statistics_use_training_only(sample_features):
    """Valores externos ao treino nao alteram estatisticas ajustadas."""

    train = sample_features.iloc[:100].copy()
    validation = sample_features.iloc[100:].copy()

    # Valor ausente durante o treino.
    train.loc[0, "AMT_INCOME_TOTAL"] = np.nan

    # Valor extremo presente apenas na validacao.
    validation.loc[100, "AMT_INCOME_TOTAL"] = 1e12

    preprocessor = build_preprocessor()
    preprocessor.fit(train)

    numeric_pipeline = preprocessor.named_transformers_["numeric"]

    imputer = numeric_pipeline.named_steps["imputer"]
    scaler = numeric_pipeline.named_steps["scaler"]

    income_index = 1  # AMT_INCOME_TOTAL em NUMERIC_FEATURES

    expected_median = train["AMT_INCOME_TOTAL"].median()

    assert np.isclose(
        imputer.statistics_[income_index],
        expected_median,
    )

    original_mean = scaler.mean_.copy()
    original_scale = scaler.scale_.copy()

    # Transformar a validacao nao deve modificar o ajuste.
    preprocessor.transform(validation)

    np.testing.assert_array_equal(
        scaler.mean_,
        original_mean,
    )
    np.testing.assert_array_equal(
        scaler.scale_,
        original_scale,
    )


def test_indicator_is_not_scaled(sample_features):
    """Indicador binario permanece 0/1 apos preprocessamento."""

    features = sample_features.copy()

    features.loc[0, "DAYS_EMPLOYED_SENTINEL"] = 1
    features.loc[1, "DAYS_EMPLOYED_SENTINEL"] = 1

    preprocessor = build_preprocessor()
    transformed = preprocessor.fit_transform(features)

    dense = (
        transformed.toarray()
        if hasattr(transformed, "toarray")
        else np.asarray(transformed)
    )

    indicator = dense[:, -1]

    np.testing.assert_array_equal(
        indicator,
        features["DAYS_EMPLOYED_SENTINEL"].to_numpy(),
    )


def test_extra_columns_are_not_used(sample_features):
    """Colunas externas nao entram no preprocessamento."""

    features = sample_features.copy()
    features["SK_ID_CURR"] = range(len(features))
    features["TARGET"] = np.tile([0, 1], len(features) // 2)

    preprocessor = build_preprocessor()

    transformed_with_extra = preprocessor.fit_transform(features)
    transformed_without_extra = preprocessor.transform(features.loc[:, MODEL_FEATURES])

    def as_dense(data):
        return data.toarray() if hasattr(data, "toarray") else np.asarray(data)

    np.testing.assert_allclose(
        as_dense(transformed_with_extra),
        as_dense(transformed_without_extra),
    )

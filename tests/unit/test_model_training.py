"""Testes das metricas e selecao do threshold."""

import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import f1_score

from credit_risk_monitoring.data.preparation import (
    CATEGORICAL_FEATURES,
    DERIVED_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
)
from credit_risk_monitoring.modeling.finalization import (
    evaluate_final_model,
    save_final_model,
)
from credit_risk_monitoring.modeling.training import (
    evaluate_probabilities,
    select_threshold_by_f1,
    train_baseline,
)


def test_evaluation_confusion_matrix():
    y = np.array([0, 0, 1, 1])
    scores = np.array([0.1, 0.8, 0.4, 0.9])

    result = evaluate_probabilities(y, scores, threshold=0.5)

    assert result["confusion_matrix"] == {
        "tn": 1,
        "fp": 1,
        "fn": 1,
        "tp": 1,
    }


def test_threshold_selection_maximizes_f1():
    y = np.array([0, 0, 1, 1, 1, 0])
    scores = np.array([0.05, 0.2, 0.3, 0.4, 0.8, 0.1])

    result = select_threshold_by_f1(y, scores)

    candidate_f1 = [f1_score(y, scores >= threshold) for threshold in np.unique(scores)]

    assert result["f1"] == pytest.approx(max(candidate_f1))


def test_selected_threshold_is_deterministic():
    y = np.array([0, 1, 0, 1, 1, 0])
    scores = np.array([0.1, 0.7, 0.3, 0.8, 0.5, 0.2])

    first = select_threshold_by_f1(y, scores)
    second = select_threshold_by_f1(y, scores)

    assert first == second


def test_invalid_probabilities_are_rejected():
    y = np.array([0, 1, 0, 1])
    scores = np.array([0.1, 0.8, np.nan, 0.9])

    with pytest.raises(ValueError, match="nao finitas"):
        select_threshold_by_f1(y, scores)


def test_invalid_threshold_is_rejected():
    y = np.array([0, 1, 0, 1])
    scores = np.array([0.1, 0.8, 0.2, 0.9])

    with pytest.raises(ValueError, match="Threshold"):
        evaluate_probabilities(y, scores, threshold=1.5)


@pytest.fixture
def synthetic_model_data():
    """Cria particoes sinteticas disjuntas para treinamento."""

    rng = np.random.default_rng(42)
    n = 160

    data = {
        "SK_ID_CURR": np.arange(100000, 100000 + n),
        "TARGET": np.tile([0, 0, 0, 1], n // 4),
    }

    for column in NUMERIC_FEATURES:
        data[column] = rng.normal(
            loc=100.0,
            scale=20.0,
            size=n,
        )

    for column in CATEGORICAL_FEATURES:
        data[column] = np.tile(["A", "B"], n // 2)

    for column in DERIVED_FEATURES:
        data[column] = np.zeros(n, dtype=int)

    df = pd.DataFrame(data)

    return (
        df.iloc[:120].copy(),
        df.iloc[120:].copy(),
    )


def test_train_baseline_returns_fitted_model(synthetic_model_data):
    train, validation = synthetic_model_data

    model, metrics, diagnostics = train_baseline(
        train,
        validation,
    )

    probabilities = model.predict_proba(validation.loc[:, MODEL_FEATURES])

    assert probabilities.shape == (len(validation), 2)
    assert metrics["n_rows"] == len(validation)
    assert diagnostics["train_rows"] == len(train)
    assert diagnostics["validation_rows"] == len(validation)
    assert diagnostics["feature_count"] == 17


def test_train_baseline_rejects_overlapping_ids(synthetic_model_data):
    train, validation = synthetic_model_data

    validation.loc[validation.index[0], "SK_ID_CURR"] = train["SK_ID_CURR"].iloc[0]

    with pytest.raises(ValueError, match="Sobreposicao"):
        train_baseline(train, validation)


def test_train_baseline_rejects_missing_feature(synthetic_model_data):
    train, validation = synthetic_model_data

    train = train.drop(columns=["AMT_CREDIT"])

    with pytest.raises(ValueError, match="Colunas ausentes"):
        train_baseline(train, validation)


def test_train_baseline_rejects_invalid_target(synthetic_model_data):
    train, validation = synthetic_model_data

    validation.loc[validation.index[0], "TARGET"] = 2

    with pytest.raises(ValueError, match="TARGET invalido"):
        train_baseline(train, validation)


def test_nan_threshold_is_rejected():
    y = np.array([0, 1, 0, 1])
    scores = np.array([0.1, 0.8, 0.2, 0.9])

    with pytest.raises(ValueError, match="Threshold"):
        evaluate_probabilities(y, scores, threshold=float("nan"))


def test_final_evaluation_keeps_threshold_fixed(synthetic_model_data):
    """O threshold do teste deve vir da validacao."""

    train, remaining = synthetic_model_data

    validation = remaining.iloc[:20].copy()
    test = remaining.iloc[20:].copy()

    _, results = evaluate_final_model(train, validation, test)

    assert results["selection_strategy"] == "max_f1"

    assert results["threshold"] == pytest.approx(
        results["validation_selected"]["threshold"]
    )

    assert results["test"]["threshold"] == pytest.approx(results["threshold"])

    assert results["test"]["n_rows"] == len(test)


def test_final_evaluation_rejects_test_overlap(synthetic_model_data):
    """O teste nao pode compartilhar IDs com o treino."""

    train, remaining = synthetic_model_data

    validation = remaining.iloc[:20].copy()
    test = remaining.iloc[20:].copy()

    test.loc[test.index[0], "SK_ID_CURR"] = train["SK_ID_CURR"].iloc[0]

    with pytest.raises(ValueError, match="Sobreposicao"):
        evaluate_final_model(train, validation, test)


def test_model_serialization_preserves_probabilities(
    synthetic_model_data,
    tmp_path,
):
    """O modelo recarregado deve preservar as probabilidades."""

    train, remaining = synthetic_model_data

    validation = remaining.iloc[:20].copy()
    test = remaining.iloc[20:].copy()

    model, results = evaluate_final_model(
        train,
        validation,
        test,
    )

    x_test = test.loc[:, MODEL_FEATURES]

    original_probabilities = model.predict_proba(x_test)[:, 1]

    manifest = {
        "source": {
            "sha256": "synthetic_source_hash",
        },
        "partitions": {
            name: {"sha256": f"synthetic_{name}_hash"}
            for name in ("train", "validation", "test", "reference")
        },
    }

    model_path = tmp_path / "baseline_model.joblib"
    metrics_path = tmp_path / "baseline_metrics.json"

    save_final_model(
        model,
        results,
        model_path,
        metrics_path,
        data_manifest=manifest,
    )

    assert model_path.is_file()
    assert metrics_path.is_file()

    # Carregar somente artefato confiavel criado pelo teste.
    saved = joblib.load(model_path)

    restored_model = saved["pipeline"]
    restored_probabilities = restored_model.predict_proba(x_test)[:, 1]

    np.testing.assert_allclose(
        original_probabilities,
        restored_probabilities,
        rtol=0,
        atol=1e-12,
    )

    assert saved["metadata"]["threshold"] == pytest.approx(results["threshold"])


def test_persisted_metadata_and_metrics(
    synthetic_model_data,
    tmp_path,
):
    """Os artefatos devem registrar os contratos essenciais."""

    train, remaining = synthetic_model_data

    validation = remaining.iloc[:20].copy()
    test = remaining.iloc[20:].copy()

    model, results = evaluate_final_model(
        train,
        validation,
        test,
    )

    manifest = {
        "source": {
            "sha256": "source_sha256_example",
        },
        "partitions": {
            name: {"sha256": f"{name}_sha256_example"}
            for name in ("train", "validation", "test", "reference")
        },
    }

    model_path = tmp_path / "model.joblib"
    metrics_path = tmp_path / "metrics.json"

    save_final_model(
        model,
        results,
        model_path,
        metrics_path,
        data_manifest=manifest,
    )

    data = json.loads(metrics_path.read_text(encoding="utf-8"))

    metadata = data["metadata"]

    assert metadata["model_type"] == "LogisticRegression"
    assert metadata["model_features"] == list(MODEL_FEATURES)
    assert metadata["feature_count"] == 17
    assert metadata["threshold_strategy"] == "max_f1"
    assert metadata["source_sha256"] == "source_sha256_example"

    assert metadata["partition_sha256"]["test"] == ("test_sha256_example")

    assert all(
        library in metadata["versions"]
        for library in (
            "python",
            "pandas",
            "numpy",
            "scikit-learn",
            "joblib",
        )
    )

    assert data["results"]["threshold"] == pytest.approx(results["threshold"])

    assert data["results"]["test"]["f1"] == pytest.approx(results["test"]["f1"])

    assert data["results"]["selection_partition"] == "validation"
    assert data["results"]["evaluation_partition"] == "test"

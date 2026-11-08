"""Avaliacao final e persistencia do baseline."""

import json
import platform
from importlib.metadata import version
from pathlib import Path

import joblib
import pandas as pd

from credit_risk_monitoring.data.preparation import (
    ID_COLUMN,
    MODEL_FEATURES,
    TARGET_COLUMN,
)
from credit_risk_monitoring.modeling.training import (
    evaluate_probabilities,
    select_threshold_by_f1,
    train_baseline,
    validate_model_data,
)


def evaluate_final_model(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    *,
    random_state: int = 42,
) -> tuple:
    """Treina, seleciona threshold e avalia no teste."""

    for name, df in (
        ("train", train),
        ("validation", validation),
        ("test", test),
    ):
        validate_model_data(df, name)

    # Garante separacao de todos os conjuntos rotulados.
    ids = [set(df[ID_COLUMN]) for df in (train, validation, test)]

    if any(ids[i].intersection(ids[j]) for i, j in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("Sobreposicao entre particoes")

    model, default_metrics, diagnostics = train_baseline(
        train,
        validation,
        random_state=random_state,
    )

    validation_scores = model.predict_proba(validation.loc[:, MODEL_FEATURES])[:, 1]

    selected_metrics = select_threshold_by_f1(
        validation[TARGET_COLUMN],
        validation_scores,
    )

    selected_threshold = selected_metrics["threshold"]

    # O threshold ja esta fixado antes de acessar os scores do teste.
    test_scores = model.predict_proba(test.loc[:, MODEL_FEATURES])[:, 1]

    test_metrics = evaluate_probabilities(
        test[TARGET_COLUMN],
        test_scores,
        threshold=selected_threshold,
    )

    results = {
        "selection_strategy": "max_f1",
        "selection_partition": "validation",
        "evaluation_partition": "test",
        "threshold": selected_threshold,
        "validation_default": default_metrics,
        "validation_selected": selected_metrics,
        "test": test_metrics,
        "diagnostics": diagnostics,
    }

    return model, results


def save_final_model(
    model,
    results: dict,
    model_path: Path,
    metrics_path: Path,
    *,
    data_manifest: dict,
) -> None:
    """Salva o pipeline completo e seus metadados."""

    model_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "model_type": "LogisticRegression",
        "model_features": list(MODEL_FEATURES),
        "feature_count": len(MODEL_FEATURES),
        "threshold": results["threshold"],
        "threshold_strategy": "max_f1",
        "random_state": results["diagnostics"]["random_state"],
        "versions": {
            "python": platform.python_version(),
            "pandas": version("pandas"),
            "numpy": version("numpy"),
            "scikit-learn": version("scikit-learn"),
            "joblib": version("joblib"),
        },
        "source_sha256": data_manifest["source"]["sha256"],
        "partition_sha256": {
            name: info["sha256"] for name, info in data_manifest["partitions"].items()
        },
    }

    # Somente modelos produzidos localmente devem ser carregados.
    joblib.dump(
        {
            "pipeline": model,
            "metadata": metadata,
        },
        model_path,
    )

    output = {
        "metadata": metadata,
        "results": results,
    }

    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )

"""Treinamento inicial e avaliacao do baseline de credito."""

import warnings

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

from credit_risk_monitoring.data.preparation import (
    ID_COLUMN,
    MODEL_FEATURES,
    TARGET_COLUMN,
)
from credit_risk_monitoring.modeling.pipeline import (
    build_baseline_pipeline,
)

DEFAULT_THRESHOLD = 0.50


def validate_model_data(df: pd.DataFrame, name: str) -> None:
    """Verifica a estrutura minima da particao rotulada."""

    required = [ID_COLUMN, TARGET_COLUMN, *MODEL_FEATURES]

    if df.empty:
        raise ValueError(f"Particao vazia: {name}")

    if not df.columns.is_unique:
        raise ValueError(f"Colunas duplicadas: {name}")

    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Colunas ausentes em {name}: {missing}")

    if df[ID_COLUMN].isna().any():
        raise ValueError(f"Identificadores nulos em {name}")

    if df[ID_COLUMN].duplicated().any():
        raise ValueError(f"Identificadores duplicados em {name}")

    target = df[TARGET_COLUMN]

    if target.isna().any() or not target.isin([0, 1]).all():
        raise ValueError(f"TARGET invalido em {name}")

    if target.nunique() != 2:
        raise ValueError(f"TARGET precisa conter duas classes: {name}")


def evaluate_probabilities(
    y_true,
    probabilities,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """Calcula metricas de classificacao com threshold explicito."""

    y = np.asarray(y_true)
    scores = np.asarray(probabilities, dtype=float)

    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Threshold deve ser finito e estar entre 0 e 1")

    if y.ndim != 1 or scores.ndim != 1 or len(y) != len(scores):
        raise ValueError("Dimensoes de avaliacao invalidas")

    if len(y) == 0 or set(np.unique(y)) != {0, 1}:
        raise ValueError("Avaliacao requer as duas classes")

    if not np.isfinite(scores).all():
        raise ValueError("Probabilidades nao finitas")

    if ((scores < 0) | (scores > 1)).any():
        raise ValueError("Probabilidades fora de [0, 1]")

    predictions = (scores >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()

    return {
        "threshold": float(threshold),
        "n_rows": int(len(y)),
        "prevalence": float(y.mean()),
        "roc_auc": float(roc_auc_score(y, scores)),
        "average_precision": float(average_precision_score(y, scores)),
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "recall": float(recall_score(y, predictions, zero_division=0)),
        "f1": float(f1_score(y, predictions, zero_division=0)),
        "predicted_positive_rate": float(predictions.mean()),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
        "score_distribution": {
            "min": float(scores.min()),
            "p10": float(np.quantile(scores, 0.10)),
            "median": float(np.median(scores)),
            "p90": float(np.quantile(scores, 0.90)),
            "max": float(scores.max()),
            "mean": float(scores.mean()),
        },
    }


def train_baseline(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    *,
    random_state: int = 42,
):
    """Ajusta somente no treino e avalia na validacao."""

    validate_model_data(train, "train")
    validate_model_data(validation, "validation")

    train_ids = set(train[ID_COLUMN])
    validation_ids = set(validation[ID_COLUMN])

    if train_ids.intersection(validation_ids):
        raise ValueError("Sobreposicao entre treino e validacao")

    x_train = train.loc[:, MODEL_FEATURES]
    y_train = train[TARGET_COLUMN]

    x_validation = validation.loc[:, MODEL_FEATURES]
    y_validation = validation[TARGET_COLUMN]

    model = build_baseline_pipeline(
        class_weight=None,
        random_state=random_state,
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(x_train, y_train)

    convergence_warnings = [
        str(warning.message)
        for warning in caught
        if issubclass(warning.category, ConvergenceWarning)
    ]

    probabilities = model.predict_proba(x_validation)[:, 1]

    metrics = evaluate_probabilities(
        y_validation,
        probabilities,
        threshold=DEFAULT_THRESHOLD,
    )

    classifier = model.named_steps["classifier"]

    diagnostics = {
        "model": "LogisticRegression",
        "solver": classifier.solver,
        "max_iter": classifier.max_iter,
        "class_weight": classifier.class_weight,
        "random_state": random_state,
        "n_iter": classifier.n_iter_.tolist(),
        "convergence_warnings": convergence_warnings,
        "train_rows": len(train),
        "validation_rows": len(validation),
        "feature_count": len(MODEL_FEATURES),
    }

    return model, metrics, diagnostics


def select_threshold_by_f1(y_true, probabilities) -> dict:
    """Seleciona o threshold que maximiza F1 na validacao.

    Em empates numericos, prefere o maior threshold.
    Nao utiliza dados de teste nem reajusta o modelo.
    """

    # Reutiliza as verificacoes de entrada existentes.
    evaluate_probabilities(
        y_true,
        probabilities,
        threshold=DEFAULT_THRESHOLD,
    )

    precision, recall, thresholds = precision_recall_curve(
        y_true,
        probabilities,
    )

    # O ultimo ponto da curva nao possui threshold associado.
    p = precision[:-1]
    r = recall[:-1]

    denominator = p + r

    f1_values = np.divide(
        2 * p * r,
        denominator,
        out=np.zeros_like(p),
        where=denominator > 0,
    )

    best_f1 = float(f1_values.max())

    # Desempate deterministico pelo maior threshold.
    candidates = np.flatnonzero(
        np.isclose(
            f1_values,
            best_f1,
            rtol=0,
            atol=1e-12,
        )
    )

    best_index = int(candidates[-1])
    best_threshold = float(thresholds[best_index])

    return evaluate_probabilities(
        y_true,
        probabilities,
        threshold=best_threshold,
    )

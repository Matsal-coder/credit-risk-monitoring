"""Analise diagnostica agregada de disparidades preditivas no teste.

Nao retreina o baseline, nao ajusta threshold e nao exporta dados individuais.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from credit_risk_monitoring.data.preparation import MODEL_FEATURES, TARGET_COLUMN
from credit_risk_monitoring.modeling.inference import load_baseline_model
from credit_risk_monitoring.modeling.training import validate_model_data

TEST_PATH = Path("data/processed/test.csv")
MODEL_PATH = Path("artifacts/baseline_model.joblib")
OUTPUT_PATH = Path("artifacts/fairness_test_aggregated.json")

MIN_GROUP_SIZE = 100
MIN_DENOMINATOR = 20

GROUP_COLUMNS = (
    "age_group",
    "education",
    "income_type",
)


def safe_rate(numerator: int, denominator: int, minimum: int = 1) -> float | None:
    """Retorna None para denominadores nulos ou insuficientes."""
    if denominator < minimum:
        return None
    return float(numerator / denominator)


def build_age_groups(days_birth: pd.Series) -> pd.Series:
    """Agrupa idades aproximadas derivadas de DAYS_BIRTH."""
    values = pd.to_numeric(days_birth, errors="coerce")
    ages = -values / 365.25
    ages = ages.where((ages >= 0) & (ages <= 120))

    groups = pd.cut(
        ages,
        bins=[0, 30, 45, 60, float("inf")],
        labels=["under_30", "30_to_44", "45_to_59", "60_plus"],
        right=False,
    )
    return groups.astype("string").fillna("MISSING")


def build_group_columns(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Define os grupos a partir de atributos existentes no teste."""
    return {
        "age_group": build_age_groups(df["DAYS_BIRTH"]),
        "education": df["NAME_EDUCATION_TYPE"].astype("string").fillna("MISSING"),
        "income_type": df["NAME_INCOME_TYPE"].astype("string").fillna("MISSING"),
    }


def confusion_counts(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict[str, int]:
    """Calcula a matriz binaria sem depender da presenca das duas classes."""
    return {
        "tn": int(np.sum((y_true == 0) & (y_pred == 0))),
        "fp": int(np.sum((y_true == 0) & (y_pred == 1))),
        "fn": int(np.sum((y_true == 1) & (y_pred == 0))),
        "tp": int(np.sum((y_true == 1) & (y_pred == 1))),
    }


def aggregate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    min_denominator: int = MIN_DENOMINATOR,
) -> dict:
    """Calcula indicadores agregados e sinaliza suporte insuficiente."""
    counts = confusion_counts(y_true, y_pred)
    tn, fp = counts["tn"], counts["fp"]
    fn, tp = counts["fn"], counts["tp"]

    n = len(y_true)
    actual_positive = tp + fn
    actual_negative = tn + fp
    predicted_positive = tp + fp

    return {
        "n": int(n),
        "actual_positive": actual_positive,
        "actual_negative": actual_negative,
        "predicted_positive": predicted_positive,
        "prevalence": safe_rate(actual_positive, n),
        "predicted_positive_rate": safe_rate(predicted_positive, n),
        "precision": safe_rate(tp, predicted_positive, min_denominator),
        "recall_tpr": safe_rate(tp, actual_positive, min_denominator),
        "fpr": safe_rate(fp, actual_negative, min_denominator),
        "confusion_matrix": counts,
    }


def evaluate_groups(
    labels: pd.Series,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    min_group_size: int = MIN_GROUP_SIZE,
    min_denominator: int = MIN_DENOMINATOR,
) -> list[dict]:
    """Calcula metricas agregadas, consolidando grupos pequenos."""
    if len(labels) != len(y_true) or len(y_true) != len(y_pred):
        raise ValueError("Dimensoes inconsistentes na avaliacao por grupo.")

    normalized = labels.astype("string").fillna("MISSING")
    results = []
    suppressed_total = 0

    for group in sorted(normalized.unique()):
        mask = normalized.eq(group).to_numpy()
        n = int(np.sum(mask))

        if n < min_group_size:
            suppressed_total += n
            continue

        results.append(
            {
                "group": str(group),
                "n": n,
                "status": "evaluated",
                "metrics": aggregate_metrics(
                    y_true[mask],
                    y_pred[mask],
                    min_denominator=min_denominator,
                ),
            }
        )

    if suppressed_total:
        results.append(
            {
                "group": "SUPPRESSED_GROUPS",
                "n": suppressed_total,
                "status": "small_groups_combined",
                "metrics": None,
            }
        )

    return results


def build_fairness_report(
    test: pd.DataFrame,
    probabilities: np.ndarray,
    threshold: float,
) -> dict:
    """Produz somente resultados agregados para fins diagnosticos."""
    validate_model_data(test, "test")

    scores = np.asarray(probabilities, dtype=float)

    if scores.shape != (len(test),):
        raise ValueError("Dimensao de probabilidades invalida.")

    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("Probabilidades invalidas.")

    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Threshold invalido.")

    y_true = test[TARGET_COLUMN].to_numpy(dtype=int)
    y_pred = (scores >= threshold).astype(int)

    grouped = {}
    for dimension, labels in build_group_columns(test).items():
        grouped[dimension] = evaluate_groups(labels, y_true, y_pred)

    return {
        "analysis": "diagnostic_group_fairness",
        "dataset": "test",
        "model": "persisted_baseline",
        "threshold": float(threshold),
        "min_group_size": MIN_GROUP_SIZE,
        "min_conditional_denominator": MIN_DENOMINATOR,
        "overall": aggregate_metrics(
            y_true,
            y_pred,
            min_denominator=MIN_DENOMINATOR,
        ),
        "groups": grouped,
        "limitations": [
            "Historical random test partition, not temporal production data.",
            "Group disparities do not establish discrimination or causality.",
            "TARGET prevalence can differ across groups.",
            "Small groups are suppressed from metric publication.",
            "Conditional metrics with insufficient support are null.",
            "No new model selection or threshold optimization is performed.",
        ],
    }


def save_report(payload: dict, destination: Path) -> Path:
    """Salva JSON agregado exclusivamente dentro de artifacts/."""
    destination = Path(destination)
    artifacts_root = Path("artifacts").resolve()
    resolved = destination.resolve()

    if not resolved.is_relative_to(artifacts_root):
        raise ValueError("O relatorio deve permanecer dentro de artifacts/.")

    if not destination.parent.is_dir():
        raise ValueError("Diretorio de saida inexistente.")

    serialized = json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    )

    with destination.open("x", encoding="utf-8") as output:
        output.write(serialized)
        output.write("\n")

    return destination


def run_analysis(
    test_path: Path = TEST_PATH,
    model_path: Path = MODEL_PATH,
    output_path: Path = OUTPUT_PATH,
) -> Path:
    """Executa avaliacao offline sem treinamento ou modificacao do modelo."""
    test = pd.read_csv(test_path, low_memory=False)
    validate_model_data(test, "test")

    model, threshold = load_baseline_model(model_path)

    scores = np.asarray(
        model.predict_proba(test.loc[:, MODEL_FEATURES])[:, 1],
        dtype=float,
    )

    report = build_fairness_report(test, scores, threshold)
    return save_report(report, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Avaliacao agregada de fairness do baseline no teste."
    )
    parser.add_argument("--test", type=Path, default=TEST_PATH)
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)

    args = parser.parse_args()

    destination = run_analysis(
        test_path=args.test,
        model_path=args.model,
        output_path=args.output,
    )
    print(f"Relatorio agregado salvo em: {destination}")


if __name__ == "__main__":
    main()

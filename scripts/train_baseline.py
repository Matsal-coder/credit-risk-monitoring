"""Executa treinamento e diagnostico do baseline na validacao."""

import argparse
import json
from pathlib import Path

import pandas as pd

from credit_risk_monitoring.data.preparation import MODEL_FEATURES
from credit_risk_monitoring.modeling.training import (
    select_threshold_by_f1,
    train_baseline,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Treina e avalia o baseline na validacao."
    )

    parser.add_argument(
        "--train",
        type=Path,
        default=Path("data/processed/train.csv"),
    )
    parser.add_argument(
        "--validation",
        type=Path,
        default=Path("data/processed/validation.csv"),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    train = pd.read_csv(args.train)
    validation = pd.read_csv(args.validation)

    model, default_metrics, diagnostics = train_baseline(
        train,
        validation,
        random_state=args.seed,
    )

    x_validation = validation.loc[:, MODEL_FEATURES]
    y_validation = validation["TARGET"]

    probabilities = model.predict_proba(x_validation)[:, 1]

    selected_metrics = select_threshold_by_f1(
        y_validation,
        probabilities,
    )

    print("\n=== DIAGNOSTICO DO MODELO ===")
    print(json.dumps(diagnostics, indent=2))

    print("\n=== THRESHOLD PADRAO: 0.50 ===")
    print(json.dumps(default_metrics, indent=2))

    print("\n=== THRESHOLD SELECIONADO POR F1 ===")
    print(json.dumps(selected_metrics, indent=2))

    print("\n=== COMPARACAO ===")

    for metric in (
        "threshold",
        "precision",
        "recall",
        "f1",
        "predicted_positive_rate",
    ):
        print(
            f"{metric:<25}"
            f"padrao={default_metrics[metric]:.6f} "
            f"selecionado={selected_metrics[metric]:.6f}"
        )

    print("\nNenhum modelo ou resultado foi persistido.")
    print("O conjunto de teste nao foi utilizado.")


if __name__ == "__main__":
    main()

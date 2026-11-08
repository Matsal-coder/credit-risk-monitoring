"""Executa avaliacao final e salva artefatos do baseline."""

import argparse
import json
from pathlib import Path

import pandas as pd
from verify_dataset import verify_artifacts

from credit_risk_monitoring.modeling.finalization import (
    evaluate_final_model,
    save_final_model,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finaliza e persiste o baseline de credito."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument(
        "--data-manifest",
        type=Path,
        default=Path("artifacts/data_manifest.json"),
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=Path("artifacts/baseline_model.joblib"),
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("artifacts/baseline_metrics.json"),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    # Valida os arquivos antes de utiliza-los.
    verify_artifacts(args.data_manifest, args.data_dir)

    manifest = json.loads(args.data_manifest.read_text(encoding="utf-8"))

    if args.seed != manifest["preparation"]["random_state"]:
        raise ValueError("Seed divergente do manifesto de dados")

    train = pd.read_csv(args.data_dir / "train.csv")
    validation = pd.read_csv(args.data_dir / "validation.csv")
    test = pd.read_csv(args.data_dir / "test.csv")

    model, results = evaluate_final_model(
        train,
        validation,
        test,
        random_state=args.seed,
    )

    save_final_model(
        model,
        results,
        args.model_output,
        args.metrics_output,
        data_manifest=manifest,
    )

    print("\n=== AVALIACAO FINAL DO BASELINE ===")
    print(f"Threshold: {results['threshold']:.9f}")

    for name in ("validation_selected", "test"):
        metrics = results[name]

        print(f"\n{name.upper()}")
        for key in (
            "roc_auc",
            "average_precision",
            "precision",
            "recall",
            "f1",
        ):
            print(f"{key:<22}{metrics[key]:.6f}")

        print("Matriz:", metrics["confusion_matrix"])

    print(f"\nModelo salvo em: {args.model_output}")
    print(f"Metricas salvas em: {args.metrics_output}")


if __name__ == "__main__":
    main()

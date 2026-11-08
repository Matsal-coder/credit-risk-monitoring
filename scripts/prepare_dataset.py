"""Gera particoes e manifesto do Home Credit Default Risk."""

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from credit_risk_monitoring.data.preparation import (
    ID_COLUMN,
    MODEL_FEATURES,
    RANDOM_STATE,
    TARGET_COLUMN,
    load_dataset,
    prepare_features,
    split_dataset,
)

DEFAULT_INPUT = Path("data/raw/application_train.csv")
DEFAULT_OUTPUT = Path("data/processed")
DEFAULT_MANIFEST = Path("artifacts/data_manifest.json")


def sha256_file(path: Path) -> str:
    """Calcula o hash do conteudo de um arquivo."""

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def generate_artifacts(
    input_path: Path,
    output_dir: Path,
    manifest_path: Path,
    random_state: int = RANDOM_STATE,
) -> dict:
    """Prepara os dados e persiste splits e metadados."""

    source = load_dataset(input_path)
    prepared = prepare_features(source)
    partitions = split_dataset(
        prepared,
        random_state=random_state,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "source": {
            "filename": input_path.name,
            "sha256": sha256_file(input_path),
            "rows": len(source),
            "columns": len(source.columns),
        },
        "preparation": {
            "random_state": random_state,
            "split_strategy": "stratified_random",
            "split_proportions": {
                "train": 0.60,
                "validation": 0.15,
                "test": 0.15,
                "reference": 0.10,
            },
            "id_column": ID_COLUMN,
            "target_column": TARGET_COLUMN,
            "model_features": list(MODEL_FEATURES),
            "sentinel": {
                "column": "DAYS_EMPLOYED",
                "value": 365243,
                "replacement": "NaN",
                "indicator": "DAYS_EMPLOYED_SENTINEL",
            },
        },
        "versions": {
            "pandas": version("pandas"),
            "numpy": version("numpy"),
            "scikit-learn": version("scikit-learn"),
        },
        "partitions": {},
    }

    for name, partition in partitions.items():
        output = partition

        if name == "reference":
            output = partition.drop(columns=[TARGET_COLUMN])

        path = output_dir / f"{name}.csv"
        output.to_csv(path, index=False)

        manifest["partitions"][name] = {
            "filename": path.name,
            "rows": len(partition),
            "columns": list(output.columns),
            "target_prevalence": float(partition[TARGET_COLUMN].mean()),
            "sha256": sha256_file(path),
        }

    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara e particiona o Home Credit.")

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=RANDOM_STATE,
    )

    args = parser.parse_args()

    manifest = generate_artifacts(
        input_path=args.input,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        random_state=args.seed,
    )

    print("\n=== PREPARACAO CONCLUIDA ===")

    for name, info in manifest["partitions"].items():
        print(
            f"{name:<12}"
            f"linhas={info['rows']:>7,} "
            f"target={info['target_prevalence']:.6%} "
            f"sha256={info['sha256'][:16]}"
        )

    print(f"\nManifesto salvo em: {args.manifest}")
    print(f"Particoes salvas em: {args.output_dir}")


if __name__ == "__main__":
    main()

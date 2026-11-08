"""Verifica integridade e contratos dos datasets preparados."""

import argparse
import json
from pathlib import Path

import pandas as pd
from prepare_dataset import sha256_file

from credit_risk_monitoring.data.preparation import (
    ID_COLUMN,
    MODEL_FEATURES,
    TARGET_COLUMN,
)

DEFAULT_MANIFEST = Path("artifacts/data_manifest.json")
DEFAULT_OUTPUT_DIR = Path("data/processed")

PARTITION_NAMES = ("train", "validation", "test", "reference")


def verify_artifacts(
    manifest_path: Path,
    output_dir: Path,
) -> dict:
    """Verifica arquivos contra o manifesto de preparacao."""

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifesto nao encontrado: {manifest_path}")

    with manifest_path.open(encoding="utf-8") as file:
        manifest = json.load(file)

    if not isinstance(manifest, dict):
        raise ValueError("Manifesto invalido.")

    preparation = manifest.get("preparation", {})
    definitions = manifest.get("partitions", {})

    if not isinstance(preparation, dict):
        raise ValueError("Configuracao de preparacao invalida.")

    if not isinstance(definitions, dict):
        raise ValueError("Definicao de particoes invalida.")

    if set(definitions) != set(PARTITION_NAMES):
        raise ValueError("Particoes incompletas ou inesperadas.")

    if preparation.get("id_column") != ID_COLUMN:
        raise ValueError("Identificador inconsistente.")

    if preparation.get("target_column") != TARGET_COLUMN:
        raise ValueError("Target inconsistente.")

    if preparation.get("model_features") != list(MODEL_FEATURES):
        raise ValueError("Lista de features inconsistente.")

    all_ids = set()
    total_rows = 0
    results = {}

    for name in PARTITION_NAMES:
        info = definitions[name]

        if not isinstance(info, dict):
            raise ValueError(f"Metadados invalidos: {name}")

        expected_filename = f"{name}.csv"

        if info.get("filename") != expected_filename:
            raise ValueError(f"Nome de arquivo invalido: {name}")

        path = output_dir / expected_filename

        if not path.is_file():
            raise FileNotFoundError(f"Particao nao encontrada: {path}")

        actual_hash = sha256_file(path)

        if actual_hash != info.get("sha256"):
            raise ValueError(f"Hash SHA-256 divergente: {name}")

        df = pd.read_csv(path, low_memory=False)

        expected_columns = [
            ID_COLUMN,
            TARGET_COLUMN,
            *MODEL_FEATURES,
        ]

        if name == "reference":
            expected_columns.remove(TARGET_COLUMN)

        if not df.columns.is_unique:
            raise ValueError(f"Colunas duplicadas: {name}")

        if df.columns.tolist() != expected_columns:
            raise ValueError(f"Schema de colunas invalido: {name}")

        if info.get("columns") != expected_columns:
            raise ValueError(f"Schema divergente no manifesto: {name}")

        if len(df) != info.get("rows") or df.empty:
            raise ValueError(f"Quantidade de registros invalida: {name}")

        ids = df[ID_COLUMN]

        if ids.isna().any() or ids.duplicated().any():
            raise ValueError(f"Identificadores invalidos: {name}")

        partition_ids = set(ids.tolist())

        if all_ids.intersection(partition_ids):
            raise ValueError(f"Sobreposicao de IDs detectada: {name}")

        all_ids.update(partition_ids)
        total_rows += len(df)

        if name != "reference":
            target = df[TARGET_COLUMN]

            if target.isna().any() or not target.isin([0, 1]).all():
                raise ValueError(f"TARGET invalido: {name}")

            recorded_prevalence = info.get("target_prevalence")

            if (
                not isinstance(recorded_prevalence, (int, float))
                or abs(float(target.mean()) - recorded_prevalence) > 1e-12
            ):
                raise ValueError(f"Prevalencia inconsistente: {name}")

        results[name] = {
            "rows": len(df),
            "sha256": actual_hash,
            "valid": True,
        }

    source = manifest.get("source", {})

    if not isinstance(source, dict):
        raise ValueError("Metadados de origem invalidos.")

    if total_rows != source.get("rows"):
        raise ValueError("Total de registros difere da origem.")

    return {
        "valid": True,
        "total_rows": total_rows,
        "partitions": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica datasets preparados.")

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    args = parser.parse_args()

    try:
        result = verify_artifacts(
            args.manifest,
            args.output_dir,
        )
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        parser.exit(1, f"VERIFICACAO REPROVADA: {exc}\n")

    print("\n=== INTEGRIDADE DOS DATASETS ===")

    for name, info in result["partitions"].items():
        print(f"{name:<12}linhas={info['rows']:>7,} sha256={info['sha256'][:16]} OK")

    print(f"\nTotal de registros: {result['total_rows']:,}")
    print("VERIFICACAO APROVADA")


if __name__ == "__main__":
    main()

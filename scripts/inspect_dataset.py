"""Inspecao inicial do Home Credit Default Risk.

Produz estatisticas agregadas sem exportar registros individuais.
Nao realiza preprocessamento, selecao de features ou treinamento.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

DEFAULT_INPUT = Path("data/raw/application_train.csv")
DEFAULT_OUTPUT = Path("artifacts/inspection_summary.json")

REQUIRED_COLUMNS = ("SK_ID_CURR", "TARGET")


def inspect_dataset(path: Path) -> dict:
    """Carrega o CSV e retorna um resumo agregado."""

    if not path.is_file():
        raise FileNotFoundError(f"Dataset nao encontrado: {path}")

    df = pd.read_csv(path, low_memory=False)

    if df.empty:
        raise ValueError("O dataset esta vazio.")

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in df.columns
    ]
    if missing_columns:
        raise ValueError(f"Colunas obrigatorias ausentes: {missing_columns}")

    target = df["TARGET"]
    target_values = set(target.dropna().unique().tolist())
    target_valid = target.notna().all() and target_values == {0, 1}

    target_counts = {
        str(key): int(value) for key, value in target.value_counts(dropna=False).items()
    }

    target_prevalence = float(target.eq(1).mean()) if target_valid else None

    ids = df["SK_ID_CURR"]

    column_profiles = []

    for column in df.columns:
        series = df[column]
        is_categorical = (
            pd.api.types.is_object_dtype(series.dtype)
            or isinstance(series.dtype, pd.CategoricalDtype)
            or pd.api.types.is_bool_dtype(series.dtype)
        )

        column_profiles.append(
            {
                "column": column,
                "dtype": str(series.dtype),
                "missing_count": int(series.isna().sum()),
                "missing_pct": round(float(series.isna().mean() * 100), 4),
                "unique_non_null": int(series.nunique(dropna=True)),
                "categorical": bool(is_categorical),
            }
        )

    sentinel_summary = {}

    if "DAYS_EMPLOYED" in df.columns:
        series = df["DAYS_EMPLOYED"]
        count = int(series.eq(365243).sum())
        sentinel_summary["DAYS_EMPLOYED_365243"] = {
            "count": count,
            "pct": round(count / len(df) * 100, 4),
        }

    categorical_columns = [
        profile["column"] for profile in column_profiles if profile["categorical"]
    ]

    summary = {
        "source_file": path.name,
        "n_rows": int(len(df)),
        "n_columns": int(len(df.columns)),
        "column_names": df.columns.tolist(),
        "target": {
            "valid_binary": bool(target_valid),
            "missing_count": int(target.isna().sum()),
            "counts": target_counts,
            "prevalence_positive": target_prevalence,
        },
        "identifier": {
            "column": "SK_ID_CURR",
            "missing_count": int(ids.isna().sum()),
            "duplicate_count": int(ids.duplicated().sum()),
            "unique_non_null": int(ids.nunique(dropna=True)),
        },
        "categorical_columns": categorical_columns,
        "sentinels": sentinel_summary,
        "column_profiles": column_profiles,
    }

    return summary


def save_summary(summary: dict, output_path: Path) -> None:
    """Salva o resumo em JSON, sem registros individuais."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            summary,
            file,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )


def print_summary(summary: dict) -> None:
    """Imprime os principais resultados da inspecao."""

    print("\n=== HOME CREDIT: INSPECAO INICIAL ===")
    print(f"Arquivo: {summary['source_file']}")
    print(f"Linhas: {summary['n_rows']:,}")
    print(f"Colunas: {summary['n_columns']}")

    print("\nTARGET")
    target = summary["target"]
    print(f"Binario valido: {target['valid_binary']}")
    print(f"Nulos: {target['missing_count']}")
    print(f"Contagens: {target['counts']}")
    print(f"Prevalencia positiva: {target['prevalence_positive']}")

    print("\nIDENTIFICADOR")
    print(summary["identifier"])

    print("\nCOLUNAS CATEGORICAS")
    print(summary["categorical_columns"])

    print("\nSENTINELAS")
    print(summary["sentinels"])

    print("\nTOP 20 COLUNAS COM MAIS NULOS")
    profiles = sorted(
        summary["column_profiles"],
        key=lambda item: item["missing_pct"],
        reverse=True,
    )

    for item in profiles[:20]:
        print(f"{item['column']:<35} {item['missing_pct']:>8.2f}% tipo={item['dtype']}")

    print("\nInspecao finalizada.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspeciona o dataset Home Credit.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Caminho do CSV de entrada.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Caminho do resumo JSON.",
    )

    args = parser.parse_args()

    summary = inspect_dataset(args.input)
    save_summary(summary, args.output)
    print_summary(summary)

    print(f"\nResumo salvo em: {args.output}")


if __name__ == "__main__":
    main()

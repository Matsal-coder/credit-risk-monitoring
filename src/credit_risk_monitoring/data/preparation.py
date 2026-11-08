"""Preparacao deterministica dos dados do Home Credit.

Nao realiza imputacao, scaling ou encoding aprendido.
Essas transformacoes pertencerao ao pipeline de modelagem.
"""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

RANDOM_STATE = 42

ID_COLUMN = "SK_ID_CURR"
TARGET_COLUMN = "TARGET"

NUMERIC_FEATURES = (
    "AMT_CREDIT",
    "AMT_INCOME_TOTAL",
    "AMT_ANNUITY",
    "AMT_GOODS_PRICE",
    "EXT_SOURCE_2",
    "EXT_SOURCE_3",
    "DAYS_BIRTH",
    "DAYS_EMPLOYED",
    "DAYS_REGISTRATION",
    "CNT_CHILDREN",
    "CNT_FAM_MEMBERS",
)

CATEGORICAL_FEATURES = (
    "NAME_INCOME_TYPE",
    "NAME_EDUCATION_TYPE",
    "FLAG_OWN_CAR",
    "FLAG_OWN_REALTY",
    "NAME_CONTRACT_TYPE",
)

DERIVED_FEATURES = ("DAYS_EMPLOYED_SENTINEL",)

MODEL_FEATURES = (
    *NUMERIC_FEATURES,
    *CATEGORICAL_FEATURES,
    *DERIVED_FEATURES,
)

REQUIRED_COLUMNS = (
    ID_COLUMN,
    TARGET_COLUMN,
    *NUMERIC_FEATURES,
    *CATEGORICAL_FEATURES,
)


def validate_source(df: pd.DataFrame) -> None:
    """Verifica invariantes estruturais minimas do dataset."""

    if df.empty:
        raise ValueError("O dataset nao pode estar vazio.")

    if not df.columns.is_unique:
        raise ValueError("O dataset possui nomes de colunas duplicados.")

    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))

    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {missing}")

    ids = df[ID_COLUMN]

    if ids.isna().any():
        raise ValueError("SK_ID_CURR possui valores ausentes.")

    if ids.duplicated().any():
        raise ValueError("SK_ID_CURR possui valores duplicados.")

    target = df[TARGET_COLUMN]

    if target.isna().any():
        raise ValueError("TARGET possui valores ausentes.")

    if not target.isin([0, 1]).all():
        raise ValueError("TARGET deve conter apenas 0 e 1.")

    if target.nunique() != 2:
        raise ValueError("TARGET precisa conter as duas classes.")

    for column in NUMERIC_FEATURES:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"Feature numerica invalida: {column}")


def load_dataset(path: Path) -> pd.DataFrame:
    """Carrega o CSV e verifica a estrutura minima."""

    if not path.is_file():
        raise FileNotFoundError(f"Dataset nao encontrado: {path}")

    df = pd.read_csv(path, low_memory=False)

    validate_source(df)

    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Seleciona features e trata a sentinela de emprego."""

    validate_source(df)

    result = df.loc[:, REQUIRED_COLUMNS].copy()

    sentinel = result["DAYS_EMPLOYED"].eq(365243)

    result["DAYS_EMPLOYED_SENTINEL"] = sentinel.astype("int8")

    result["DAYS_EMPLOYED"] = result["DAYS_EMPLOYED"].mask(sentinel).astype("float64")

    return result.loc[
        :,
        [ID_COLUMN, TARGET_COLUMN, *MODEL_FEATURES],
    ]


def split_dataset(
    df: pd.DataFrame,
    random_state: int = RANDOM_STATE,
) -> dict[str, pd.DataFrame]:
    """Divide os registros em treino, validacao, teste e referencia.

    Proporcoes:
        train: 60%
        validation: 15%
        test: 15%
        reference: 10%

    A referencia e independente das outras particoes.
    """

    validate_source(df)

    train, remaining = train_test_split(
        df,
        train_size=0.60,
        stratify=df[TARGET_COLUMN],
        random_state=random_state,
    )

    reference, remaining = train_test_split(
        remaining,
        train_size=0.25,
        stratify=remaining[TARGET_COLUMN],
        random_state=random_state,
    )

    validation, test = train_test_split(
        remaining,
        train_size=0.50,
        stratify=remaining[TARGET_COLUMN],
        random_state=random_state,
    )

    partitions = {
        "train": train.reset_index(drop=True),
        "validation": validation.reset_index(drop=True),
        "test": test.reset_index(drop=True),
        "reference": reference.reset_index(drop=True),
    }

    validate_partitions(partitions, expected_size=len(df))

    return partitions


def validate_partitions(
    partitions: dict[str, pd.DataFrame],
    expected_size: int,
) -> None:
    """Verifica cobertura e ausencia de sobreposicao entre splits."""

    expected_names = {"train", "validation", "test", "reference"}

    if set(partitions) != expected_names:
        raise ValueError("Conjunto de particoes invalido.")

    all_ids = []

    for name, partition in partitions.items():
        if partition.empty:
            raise ValueError(f"Particao vazia: {name}")

        validate_source(partition)
        all_ids.extend(partition[ID_COLUMN].tolist())

    if len(all_ids) != expected_size:
        raise ValueError("Quantidade total de registros inconsistente.")

    if len(set(all_ids)) != len(all_ids):
        raise ValueError("Sobreposicao detectada entre particoes.")

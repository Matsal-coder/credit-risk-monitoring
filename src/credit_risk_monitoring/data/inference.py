"""Preparacao deterministica de lotes para inferencia."""

import pandas as pd

from credit_risk_monitoring.data.preparation import (
    ID_COLUMN,
    MODEL_FEATURES,
    TARGET_COLUMN,
    transform_employment_sentinel,
)
from credit_risk_monitoring.quality.contracts import (
    RAW_INFERENCE_COLUMNS,
)


def prepare_inference_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Prepara lote sem TARGET para o baseline persistido.

    Esta funcao pressupoe que o contrato raw_inference
    tenha sido aprovado antes de sua chamada.

    Nao realiza imputacao, encoding, scaling ou fit.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("O lote deve ser um pandas DataFrame.")

    if df.empty:
        raise ValueError("O lote de inferencia nao pode estar vazio.")

    if not df.columns.is_unique:
        raise ValueError("O lote possui nomes de colunas duplicados.")

    if TARGET_COLUMN in df.columns:
        raise ValueError("Lotes de inferencia nao devem conter TARGET.")

    expected = set(RAW_INFERENCE_COLUMNS)
    received = set(df.columns)

    if received != expected:
        raise ValueError("Colunas incompatíveis com a entrada de inferencia.")

    result = df.loc[:, RAW_INFERENCE_COLUMNS].copy()
    result = transform_employment_sentinel(result)

    return result.loc[
        :,
        [ID_COLUMN, *MODEL_FEATURES],
    ]

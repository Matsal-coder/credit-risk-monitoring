"""Simulacao deterministica de lotes de producao.

Este modulo preserva os datasets originais e reutiliza
os contratos existentes de qualidade de dados.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from credit_risk_monitoring.data.preparation import (
    TARGET_COLUMN,
)
from credit_risk_monitoring.quality.contracts import (
    PREPARED_INFERENCE_COLUMNS,
    RAW_INFERENCE_COLUMNS,
)
from credit_risk_monitoring.quality.validation import (
    validate_batch,
)


def reconstruct_raw_batch(
    prepared_df: pd.DataFrame,
) -> pd.DataFrame:
    """Reconstrói entrada bruta a partir de dados preparados.

    Aceita as colunas esperadas para inferencia preparada,
    com TARGET opcional, sem modificar o DataFrame recebido.

    A sentinela de DAYS_EMPLOYED e restaurada somente
    nos registros identificados pelo indicador derivado.

    Dados inconsistentes sao rejeitados, nao corrigidos.
    """
    if not isinstance(prepared_df, pd.DataFrame):
        raise TypeError("A entrada deve ser um pandas DataFrame.")

    if prepared_df.empty:
        raise ValueError("O dataset de producao nao pode estar vazio.")

    if not prepared_df.columns.is_unique:
        raise ValueError("Existem nomes de colunas duplicados.")

    expected = set(PREPARED_INFERENCE_COLUMNS)
    received = set(prepared_df.columns)

    if TARGET_COLUMN in received:
        received.remove(TARGET_COLUMN)

    if received != expected:
        raise ValueError("Colunas incompatíveis com o formato preparado.")

    prepared = prepared_df.loc[:, PREPARED_INFERENCE_COLUMNS].copy()

    validation = validate_batch(
        prepared,
        stage="prepared_inference",
        batch_id="drift-reconstruction",
    )

    if not validation.approved:
        raise ValueError("Dados preparados rejeitados pelo contrato Pandera.")

    indicator = prepared["DAYS_EMPLOYED_SENTINEL"]
    employment = prepared["DAYS_EMPLOYED"]

    if (indicator.eq(0) & employment.eq(365243)).any():
        raise ValueError("Sentinela inconsistente nos dados preparados.")

    raw = prepared.drop(columns=["DAYS_EMPLOYED_SENTINEL"])

    raw.loc[indicator.eq(1), "DAYS_EMPLOYED"] = 365243.0

    raw = raw.loc[:, RAW_INFERENCE_COLUMNS]

    return raw.copy()


# Cenarios aprovados para simulacao controlada.
ScenarioId = Literal["control", "moderate", "strong"]

DEFAULT_SIMULATION_SEED = 642

SCENARIOS = {
    "control": {
        "affected_fraction": 0.0,
        "income_multiplier": 1.0,
        "credit_multiplier": 1.0,
    },
    "moderate": {
        "affected_fraction": 0.5,
        "income_multiplier": 0.90,
        "credit_multiplier": 1.10,
    },
    "strong": {
        "affected_fraction": 1.0,
        "income_multiplier": 0.80,
        "credit_multiplier": 1.25,
    },
}


@dataclass(frozen=True)
class SimulationResult:
    """Resultado de uma simulacao de producao."""

    scenario_id: ScenarioId
    seed: int
    total_rows: int
    changed_rows: int
    income_multiplier: float
    credit_multiplier: float
    raw_batch: pd.DataFrame

    def to_dict(self) -> dict:
        """Retorna metadados agregados sem dados individuais."""
        return {
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "total_rows": self.total_rows,
            "changed_rows": self.changed_rows,
            "income_multiplier": self.income_multiplier,
            "credit_multiplier": self.credit_multiplier,
        }


def simulate_production_batch(
    prepared_df: pd.DataFrame,
    scenario_id: ScenarioId,
    *,
    seed: int = DEFAULT_SIMULATION_SEED,
) -> SimulationResult:
    """Produz lote bruto com drift controlado.

    Recebe dados preparados, opcionalmente com TARGET.

    A mesma selecao de registros recebe as alteracoes
    de renda e credito.

    Registros selecionados devem possuir valores
    finitos e positivos nas duas variaveis.

    Nenhum dado original e modificado.
    """
    if scenario_id not in SCENARIOS:
        raise ValueError("Cenario de simulacao desconhecido.")

    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("Seed deve ser um inteiro nao negativo.")

    config = SCENARIOS[scenario_id]

    raw = reconstruct_raw_batch(prepared_df)

    total_rows = len(raw)
    fraction = config["affected_fraction"]

    changed_rows = int(total_rows * fraction)

    if fraction > 0 and changed_rows == 0:
        changed_rows = 1

    if changed_rows > 0:
        columns = ["AMT_INCOME_TOTAL", "AMT_CREDIT"]

        values = raw.loc[:, columns].to_numpy(dtype=float)

        eligible_mask = np.isfinite(values).all(axis=1) & (values > 0).all(axis=1)

        eligible_positions = np.flatnonzero(eligible_mask)

        if len(eligible_positions) < changed_rows:
            raise ValueError(
                "Registros elegiveis insuficientes para o cenario solicitado."
            )

        rng = np.random.default_rng(seed)

        selected_positions = rng.choice(
            eligible_positions,
            size=changed_rows,
            replace=False,
        )

        transformations = {
            "AMT_INCOME_TOTAL": config["income_multiplier"],
            "AMT_CREDIT": config["credit_multiplier"],
        }

        for column, multiplier in transformations.items():
            column_position = raw.columns.get_loc(column)

            original_values = raw.iloc[selected_positions, column_position].to_numpy(
                dtype=float, copy=True
            )

            with np.errstate(over="ignore", under="ignore", invalid="ignore"):
                transformed_values = original_values * multiplier

            if (
                not np.isfinite(transformed_values).all()
                or not (transformed_values > 0).all()
            ):
                raise ValueError(
                    f"Valores invalidos apos transformacao da feature {column}."
                )

            raw.iloc[selected_positions, column_position] = transformed_values

    validation = validate_batch(
        raw,
        stage="raw_inference",
        batch_id=f"simulation-{scenario_id}",
    )

    if not validation.approved:
        raise ValueError("Lote simulado rejeitado pelo contrato Pandera.")

    return SimulationResult(
        scenario_id=scenario_id,
        seed=seed,
        total_rows=total_rows,
        changed_rows=changed_rows,
        income_multiplier=config["income_multiplier"],
        credit_multiplier=config["credit_multiplier"],
        raw_batch=raw,
    )

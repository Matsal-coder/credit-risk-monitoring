"""Orquestracao de inferencia e deteccao de data drift."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from credit_risk_monitoring.data.preparation import (
    CATEGORICAL_FEATURES,
    ID_COLUMN,
    NUMERIC_FEATURES,
)
from credit_risk_monitoring.drift.detection import run_evidently_drift
from credit_risk_monitoring.drift.results import (
    DriftSummary,
    build_drift_summary,
)
from credit_risk_monitoring.drift.simulation import reconstruct_raw_batch
from credit_risk_monitoring.modeling.inference import (
    DEFAULT_MODEL_PATH,
    InferenceResult,
    run_quality_gated_inference,
)
from credit_risk_monitoring.quality.validation import validate_batch

DRIFT_FEATURES = (*NUMERIC_FEATURES, *CATEGORICAL_FEATURES)


@dataclass(frozen=True)
class MonitoringResult:
    """Resultado de uma execucao de monitoramento."""

    batch_id: str
    scenario_id: str
    inference: InferenceResult
    drift: DriftSummary | None
    snapshot: object | None = None

    @property
    def approved(self) -> bool:
        return self.inference.approved

    def to_dict(self) -> dict:
        """Serializa somente resultados operacionais agregados."""
        return {
            "batch_id": self.batch_id,
            "scenario_id": self.scenario_id,
            "execution_status": "completed",
            "quality_status": self.inference.status,
            "inference": self.inference.to_dict(),
            "drift": (
                self.drift.to_dict()["drift"] if self.drift is not None else None
            ),
        }


def monitor_production_batch(
    reference_prepared: pd.DataFrame,
    production_raw: pd.DataFrame,
    *,
    batch_id: str,
    scenario_id: str,
    model_path: Path = DEFAULT_MODEL_PATH,
) -> MonitoringResult:
    """Executa qualidade, scoring e drift sem persistencia.

    A referencia recebida esta no formato preparado.
    A producao recebida esta no formato bruto.

    Lotes rejeitados pelo quality gate nao geram
    predicoes nem executam a comparacao estatistica.
    """
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id invalido.")

    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise ValueError("scenario_id invalido.")

    reference_raw = reconstruct_raw_batch(reference_prepared)

    reference_validation = validate_batch(
        reference_raw,
        stage="raw_inference",
        batch_id="drift-reference",
    )

    if not reference_validation.approved:
        raise ValueError("Referencia rejeitada pelo contrato de qualidade.")

    # A separacao entre referencia e producao deve ser
    # verificada antes do carregamento do baseline.
    if ID_COLUMN in production_raw.columns:
        reference_ids = set(reference_raw[ID_COLUMN])
        production_ids = set(production_raw[ID_COLUMN].dropna())

        if not reference_ids.isdisjoint(production_ids):
            raise ValueError("Sobreposicao entre referencia e producao.")

    inference = run_quality_gated_inference(
        production_raw,
        batch_id=batch_id,
        model_path=model_path,
    )

    # Um lote rejeitado nao pode gerar scoring nem drift.
    if not inference.approved:
        return MonitoringResult(
            batch_id=batch_id,
            scenario_id=scenario_id,
            inference=inference,
            drift=None,
        )

    snapshot, feature_results = run_evidently_drift(
        reference_raw,
        production_raw,
        DRIFT_FEATURES,
    )

    summary = build_drift_summary(
        batch_id=batch_id,
        scenario_id=scenario_id,
        reference_rows=len(reference_raw),
        production_rows=len(production_raw),
        feature_results=feature_results,
    )

    return MonitoringResult(
        batch_id=batch_id,
        scenario_id=scenario_id,
        inference=inference,
        drift=summary,
        snapshot=snapshot,
    )

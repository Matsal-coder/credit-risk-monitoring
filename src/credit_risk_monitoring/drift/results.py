"""Resultados agregados do monitoramento de data drift."""

from dataclasses import dataclass

from credit_risk_monitoring.drift.detection import (
    FeatureDriftResult,
)


@dataclass(frozen=True)
class DriftSummary:
    """Sumario de drift sem registros individuais."""

    batch_id: str
    scenario_id: str
    reference_rows: int
    production_rows: int
    features_analyzed: int
    features_drifted: int
    drift_share: float
    drift_detected: bool
    feature_results: tuple[FeatureDriftResult, ...]

    def to_dict(self) -> dict:
        """Exporta resultado estatistico agregado."""
        return {
            "batch_id": self.batch_id,
            "scenario_id": self.scenario_id,
            "reference_rows": self.reference_rows,
            "production_rows": self.production_rows,
            "drift": {
                "features_analyzed": self.features_analyzed,
                "features_drifted": self.features_drifted,
                "drift_share": self.drift_share,
                "drift_detected": self.drift_detected,
                "feature_results": [item.to_dict() for item in self.feature_results],
            },
        }


def build_drift_summary(
    *,
    batch_id: str,
    scenario_id: str,
    reference_rows: int,
    production_rows: int,
    feature_results: tuple[FeatureDriftResult, ...],
) -> DriftSummary:
    """Agrega os resultados estatisticos por feature."""
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id invalido.")

    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise ValueError("scenario_id invalido.")

    if (
        isinstance(reference_rows, bool)
        or not isinstance(reference_rows, int)
        or reference_rows <= 0
    ):
        raise ValueError("Quantidade de referencia invalida.")

    if (
        isinstance(production_rows, bool)
        or not isinstance(production_rows, int)
        or production_rows <= 0
    ):
        raise ValueError("Quantidade de producao invalida.")

    if not feature_results:
        raise ValueError("Resultados estatisticos vazios.")

    names = [item.feature for item in feature_results]

    if len(set(names)) != len(names):
        raise ValueError("Features duplicadas no sumario.")

    analyzed = len(feature_results)
    drifted = sum(bool(item.drift_detected) for item in feature_results)

    return DriftSummary(
        batch_id=batch_id,
        scenario_id=scenario_id,
        reference_rows=reference_rows,
        production_rows=production_rows,
        features_analyzed=analyzed,
        features_drifted=int(drifted),
        drift_share=float(drifted / analyzed),
        drift_detected=bool(drifted > 0),
        feature_results=feature_results,
    )

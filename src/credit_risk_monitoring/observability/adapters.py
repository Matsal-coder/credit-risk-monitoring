"""Adaptadores entre resultados do pipeline e eventos operacionais."""

import re
from datetime import datetime

from credit_risk_monitoring.drift.monitoring import MonitoringResult
from credit_risk_monitoring.modeling.inference import InferenceResult
from credit_risk_monitoring.observability.events import (
    OperationalEvent,
    finish_event,
)

ERROR_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def _inference_fields(result: InferenceResult) -> dict:
    """Extrai somente metadados agregados da inferencia."""
    violations = sum(validation.violation_count for validation in result.validations)

    return {
        "quality_status": result.status,
        "total_rows": result.total_rows,
        "scored_rows": result.scored_rows,
        "quality_violations": violations,
    }


def _monitoring_fields(result: MonitoringResult) -> dict:
    """Extrai qualidade e drift sem dados individuais."""
    fields = _inference_fields(result.inference)

    if result.drift is None:
        fields.update(
            {
                "drift_status": "not_evaluated",
                "features_analyzed": None,
                "features_drifted": None,
                "drift_share": None,
            }
        )
    else:
        drift = result.drift
        fields.update(
            {
                "drift_status": (
                    "detected" if drift.drift_detected else "not_detected"
                ),
                "features_analyzed": drift.features_analyzed,
                "features_drifted": drift.features_drifted,
                "drift_share": drift.drift_share,
            }
        )

    return fields


def _validate_identity(
    initial: OperationalEvent,
    *,
    pipeline: str,
    batch_id: str,
    scenario_id: str | None = None,
) -> None:
    """Impede associar resultados de outra tentativa."""
    if initial.execution_status != "running":
        raise ValueError("Adaptador exige evento inicial running.")

    if initial.pipeline != pipeline:
        raise ValueError("Pipeline do evento incompativel.")

    if initial.batch_id != batch_id:
        raise ValueError("batch_id do resultado incompativel.")

    if scenario_id is not None:
        if initial.scenario_id != scenario_id:
            raise ValueError("scenario_id incompativel.")


def build_scoring_event(
    initial: OperationalEvent,
    result: InferenceResult,
    *,
    finished_at: datetime,
    duration_seconds: float,
) -> OperationalEvent:
    """Converte uma inferencia concluida em evento terminal."""
    _validate_identity(
        initial,
        pipeline="scoring",
        batch_id=result.batch_id,
    )

    return finish_event(
        initial,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        execution_status="completed",
        exit_code=0 if result.approved else 2,
        **_inference_fields(result),
    )


def build_monitoring_event(
    initial: OperationalEvent,
    result: MonitoringResult,
    *,
    finished_at: datetime,
    duration_seconds: float,
) -> OperationalEvent:
    """Converte monitoramento concluido em evento terminal."""
    _validate_identity(
        initial,
        pipeline="monitoring",
        batch_id=result.batch_id,
        scenario_id=result.scenario_id,
    )

    if result.approved and result.drift is None:
        raise ValueError("Monitoramento aprovado sem resultado de drift.")

    return finish_event(
        initial,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        execution_status="completed",
        exit_code=0 if result.approved else 2,
        **_monitoring_fields(result),
    )


def build_failure_event(
    initial: OperationalEvent,
    error: Exception,
    *,
    finished_at: datetime,
    duration_seconds: float,
    partial_result: MonitoringResult | InferenceResult | None = None,
) -> OperationalEvent:
    """Registra falha sem persistir mensagens de excecao."""
    if not isinstance(error, Exception):
        raise TypeError("Erro operacional deve ser Exception.")

    error_type = type(error).__name__

    if ERROR_NAME_PATTERN.fullmatch(error_type) is None:
        error_type = "OperationalError"

    fields: dict = {
        "quality_status": "not_evaluated",
    }

    if partial_result is not None:
        if isinstance(partial_result, MonitoringResult):
            _validate_identity(
                initial,
                pipeline="monitoring",
                batch_id=partial_result.batch_id,
                scenario_id=partial_result.scenario_id,
            )
            fields = _monitoring_fields(partial_result)

        elif isinstance(partial_result, InferenceResult):
            _validate_identity(
                initial,
                pipeline="scoring",
                batch_id=partial_result.batch_id,
            )
            fields = _inference_fields(partial_result)

        else:
            raise TypeError("Resultado parcial desconhecido.")

    return finish_event(
        initial,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        execution_status="failed",
        exit_code=1,
        error_type=error_type,
        **fields,
    )

"""Contratos imutaveis de eventos operacionais do pipeline."""

import math
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

PipelineType = Literal["monitoring", "scoring"]
ExecutionStatus = Literal["running", "completed", "failed"]
QualityStatus = Literal["approved", "rejected", "not_evaluated"]
DriftStatus = Literal["detected", "not_detected", "not_evaluated"]

BATCH_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
ERROR_TYPE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")

MONITORING_SCENARIOS = frozenset({"control", "moderate", "strong", "external"})


@dataclass(frozen=True, kw_only=True)
class OperationalEvent:
    """Snapshot validado de uma tentativa de execucao."""

    execution_id: str
    batch_id: str
    pipeline: PipelineType
    scenario_id: str
    started_at: datetime
    execution_status: ExecutionStatus

    finished_at: datetime | None = None
    duration_seconds: float | None = None
    quality_status: QualityStatus = "not_evaluated"
    drift_status: DriftStatus = "not_evaluated"
    exit_code: int | None = None
    total_rows: int | None = None
    scored_rows: int | None = None
    features_analyzed: int | None = None
    features_drifted: int | None = None
    drift_share: float | None = None
    quality_violations: int | None = None
    error_type: str | None = None

    def __post_init__(self) -> None:
        """Rejeita estados inconsistentes ou valores inseguros."""
        self._validate_identity()
        self._validate_timing()
        self._validate_counts()
        self._validate_state()

    def _validate_identity(self) -> None:
        if not isinstance(self.execution_id, str):
            raise ValueError("execution_id deve ser UUID string.")

        try:
            identifier = UUID(self.execution_id)
        except ValueError as exc:
            raise ValueError("execution_id invalido.") from exc

        if identifier.version != 4 or str(identifier) != self.execution_id:
            raise ValueError("execution_id deve ser UUID4 canonico.")

        if (
            not isinstance(self.batch_id, str)
            or BATCH_ID_PATTERN.fullmatch(self.batch_id) is None
        ):
            raise ValueError("batch_id operacional invalido.")

        if self.pipeline not in ("monitoring", "scoring"):
            raise ValueError("Pipeline desconhecido.")

        if self.pipeline == "monitoring":
            if self.scenario_id not in MONITORING_SCENARIOS:
                raise ValueError("Cenario de monitoramento invalido.")
        elif self.scenario_id != "not_applicable":
            raise ValueError("Scoring nao possui cenario de drift.")

        if self.execution_status not in (
            "running",
            "completed",
            "failed",
        ):
            raise ValueError("Estado de execucao invalido.")

        if self.quality_status not in (
            "approved",
            "rejected",
            "not_evaluated",
        ):
            raise ValueError("Estado de qualidade invalido.")

        if self.drift_status not in (
            "detected",
            "not_detected",
            "not_evaluated",
        ):
            raise ValueError("Estado de drift invalido.")

    def _validate_timing(self) -> None:
        for value in (self.started_at, self.finished_at):
            if value is None:
                continue

            if not isinstance(value, datetime):
                raise ValueError("Timestamp deve ser datetime.")

            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("Timestamp deve possuir timezone.")

            if value.utcoffset().total_seconds() != 0:
                raise ValueError("Timestamp deve estar em UTC.")

        if self.finished_at is not None:
            if self.finished_at < self.started_at:
                raise ValueError("Conclusao anterior ao inicio.")

        if self.duration_seconds is not None:
            if (
                isinstance(self.duration_seconds, bool)
                or not isinstance(self.duration_seconds, (int, float))
                or not math.isfinite(self.duration_seconds)
                or self.duration_seconds < 0
            ):
                raise ValueError("Duracao operacional invalida.")

    def _validate_counts(self) -> None:
        names = (
            "total_rows",
            "scored_rows",
            "features_analyzed",
            "features_drifted",
            "quality_violations",
        )

        for name in names:
            value = getattr(self, name)

            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise ValueError(f"Contagem invalida: {name}.")

        if self.total_rows is not None and self.scored_rows is not None:
            if self.scored_rows > self.total_rows:
                raise ValueError("Scoring excede linhas recebidas.")

        if self.features_drifted is not None:
            if (
                self.features_analyzed is None
                or self.features_drifted > self.features_analyzed
            ):
                raise ValueError("Contagem de drift inconsistente.")

        drift_values = (
            self.features_analyzed,
            self.features_drifted,
            self.drift_share,
        )

        if any(value is not None for value in drift_values):
            if any(value is None for value in drift_values):
                raise ValueError("Metricas de drift incompletas.")

            if self.features_analyzed <= 0:
                raise ValueError("Quantidade de features invalida.")

            if (
                isinstance(self.drift_share, bool)
                or not isinstance(self.drift_share, (int, float))
                or not math.isfinite(self.drift_share)
                or not 0 <= self.drift_share <= 1
            ):
                raise ValueError("Proporcao de drift invalida.")

            expected = self.features_drifted / self.features_analyzed
            if not math.isclose(self.drift_share, expected, rel_tol=0, abs_tol=1e-9):
                raise ValueError("Proporcao de drift inconsistente.")

    def _validate_state(self) -> None:
        if self.pipeline == "scoring":
            if self.drift_status != "not_evaluated":
                raise ValueError("Scoring nao avalia drift.")

        if self.drift_status == "not_evaluated":
            if any(
                value is not None
                for value in (
                    self.features_analyzed,
                    self.features_drifted,
                    self.drift_share,
                )
            ):
                raise ValueError("Drift nao avaliado possui metricas.")
        else:
            if self.pipeline != "monitoring":
                raise ValueError("Drift exige pipeline de monitoramento.")

            if self.quality_status != "approved":
                raise ValueError("Drift exige qualidade aprovada.")

            if self.features_drifted is None:
                raise ValueError("Drift avaliado exige metricas.")

            detected = self.features_drifted > 0
            if detected != (self.drift_status == "detected"):
                raise ValueError("Flag de drift inconsistente.")

        if self.quality_status == "rejected":
            if self.scored_rows != 0:
                raise ValueError("Rejeicao exige zero linhas pontuadas.")
            if self.drift_status != "not_evaluated":
                raise ValueError("Lote rejeitado nao avalia drift.")

        if self.quality_status == "not_evaluated":
            if any(
                value is not None
                for value in (
                    self.scored_rows,
                    self.quality_violations,
                )
            ):
                raise ValueError("Qualidade nao avaliada possui resultados.")

            if self.drift_status != "not_evaluated":
                raise ValueError("Drift exige avaliacao previa de qualidade.")

        if self.error_type is not None:
            if (
                not isinstance(self.error_type, str)
                or ERROR_TYPE_PATTERN.fullmatch(self.error_type) is None
            ):
                raise ValueError("Tipo de erro invalido.")

        if self.execution_status == "running":
            if any(
                value is not None
                for value in (
                    self.finished_at,
                    self.duration_seconds,
                    self.exit_code,
                    self.total_rows,
                    self.scored_rows,
                    self.features_analyzed,
                    self.features_drifted,
                    self.drift_share,
                    self.quality_violations,
                    self.error_type,
                )
            ):
                raise ValueError("Execucao inicial possui resultados.")

            if (
                self.quality_status != "not_evaluated"
                or self.drift_status != "not_evaluated"
            ):
                raise ValueError("Execucao inicial possui status final.")
            return

        if self.finished_at is None or self.duration_seconds is None:
            raise ValueError("Execucao terminal exige tempo final.")

        if isinstance(self.exit_code, bool):
            raise ValueError("Codigo de saida invalido.")

        if self.execution_status == "failed":
            if self.exit_code != 1 or self.error_type is None:
                raise ValueError("Falha exige exit 1 e tipo de erro.")
            return

        if self.quality_status == "not_evaluated":
            if any(
                value is not None
                for value in (
                    self.scored_rows,
                    self.quality_violations,
                )
            ):
                raise ValueError("Qualidade nao avaliada possui resultados.")

            if self.drift_status != "not_evaluated":
                raise ValueError("Drift exige avaliacao previa de qualidade.")

        if self.error_type is not None:
            raise ValueError("Execucao concluida nao possui erro.")

        if self.quality_status == "approved":
            if self.exit_code != 0:
                raise ValueError("Aprovacao exige exit 0.")

            if self.total_rows is None or self.scored_rows is None:
                raise ValueError("Aprovacao exige contagens.")

            if self.scored_rows != self.total_rows:
                raise ValueError("Scoring aprovado deve ser integral.")

            if self.pipeline == "monitoring" and self.drift_status == "not_evaluated":
                raise ValueError("Monitoramento aprovado exige drift.")

        elif self.quality_status == "rejected":
            if self.exit_code != 2 or self.total_rows is None:
                raise ValueError("Rejeicao exige exit 2 e total_rows.")

        else:
            raise ValueError("Conclusao sem avaliacao de qualidade.")

    def to_dict(self) -> dict:
        """Serializa somente os campos permitidos pelo contrato."""
        return {
            "execution_id": self.execution_id,
            "batch_id": self.batch_id,
            "pipeline": self.pipeline,
            "scenario_id": self.scenario_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat() if self.finished_at is not None else None
            ),
            "duration_seconds": self.duration_seconds,
            "execution_status": self.execution_status,
            "quality_status": self.quality_status,
            "drift_status": self.drift_status,
            "exit_code": self.exit_code,
            "total_rows": self.total_rows,
            "scored_rows": self.scored_rows,
            "features_analyzed": self.features_analyzed,
            "features_drifted": self.features_drifted,
            "drift_share": self.drift_share,
            "quality_violations": self.quality_violations,
            "error_type": self.error_type,
        }


def start_event(
    batch_id: str,
    pipeline: PipelineType,
    scenario_id: str,
) -> OperationalEvent:
    """Cria a identidade e o estado inicial da tentativa."""
    return OperationalEvent(
        execution_id=str(uuid4()),
        batch_id=batch_id,
        pipeline=pipeline,
        scenario_id=scenario_id,
        started_at=datetime.now(timezone.utc),
        execution_status="running",
    )


def finish_event(
    initial: OperationalEvent,
    *,
    finished_at: datetime,
    duration_seconds: float,
    execution_status: Literal["completed", "failed"],
    quality_status: QualityStatus,
    drift_status: DriftStatus = "not_evaluated",
    exit_code: int,
    total_rows: int | None = None,
    scored_rows: int | None = None,
    features_analyzed: int | None = None,
    features_drifted: int | None = None,
    drift_share: float | None = None,
    quality_violations: int | None = None,
    error_type: str | None = None,
) -> OperationalEvent:
    """Produz snapshot terminal sem alterar o original."""
    if initial.execution_status != "running":
        raise ValueError("Somente execucao inicial pode ser finalizada.")

    return replace(
        initial,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        execution_status=execution_status,
        quality_status=quality_status,
        drift_status=drift_status,
        exit_code=exit_code,
        total_rows=total_rows,
        scored_rows=scored_rows,
        features_analyzed=features_analyzed,
        features_drifted=features_drifted,
        drift_share=drift_share,
        quality_violations=quality_violations,
        error_type=error_type,
    )

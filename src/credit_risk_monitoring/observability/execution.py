"""Coordenacao do ciclo de vida de execucoes observaveis."""

import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TypeVar

from credit_risk_monitoring.drift.monitoring import MonitoringResult
from credit_risk_monitoring.modeling.inference import InferenceResult
from credit_risk_monitoring.observability.adapters import (
    build_failure_event,
)
from credit_risk_monitoring.observability.events import OperationalEvent
from credit_risk_monitoring.observability.store import SQLiteEventStore

ResultT = TypeVar("ResultT")


def execute_observed(
    *,
    store: SQLiteEventStore,
    initial: OperationalEvent,
    operation: Callable[[], ResultT],
    build_event: Callable[..., OperationalEvent],
    postprocess: Callable[[ResultT], None] | None = None,
    rollback_publication: Callable[[], None] | None = None,
) -> tuple[ResultT, OperationalEvent]:
    """Executa tentativa observavel com compensacao controlada.

    A publicacao acontece antes da persistencia terminal.

    Em caso de falha terminal, a compensacao somente sera
    acionada quando a leitura confirmar que o evento
    permanece no estado running.

    Nao ha atomicidade entre SQLite e filesystem.
    """
    if initial.execution_status != "running":
        raise ValueError("Execucao observavel exige evento running.")

    store.start(initial)

    started_clock = time.perf_counter()
    partial_result: ResultT | None = None

    try:
        result = operation()
        partial_result = result

        if postprocess is not None:
            postprocess(result)

        event = build_event(
            initial,
            result,
            finished_at=datetime.now(timezone.utc),
            duration_seconds=(time.perf_counter() - started_clock),
        )

    except Exception as exc:
        safe_partial = (
            partial_result
            if isinstance(
                partial_result,
                (MonitoringResult, InferenceResult),
            )
            else None
        )

        failure = build_failure_event(
            initial,
            exc,
            finished_at=datetime.now(timezone.utc),
            duration_seconds=(time.perf_counter() - started_clock),
            partial_result=safe_partial,
        )

        store.finish(failure)
        raise

    try:
        store.finish(event)

    except Exception:
        # Uma excecao nao comprova que o COMMIT falhou.
        # Consultar o estado antes de compensar arquivos.
        try:
            persisted = store.get(initial.execution_id)
        except Exception:
            # Estado indeterminado: preservar os arquivos
            # para reconciliacao posterior.
            raise

        if (
            persisted is not None
            and persisted.execution_status == "running"
            and rollback_publication is not None
        ):
            rollback_publication()

        raise

    return result, event

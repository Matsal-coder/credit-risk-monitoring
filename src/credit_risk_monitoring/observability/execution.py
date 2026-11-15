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
) -> tuple[ResultT, OperationalEvent]:
    """Executa uma tentativa com registro inicial e terminal.

    O evento inicial deve ser criado previamente com start_event.

    A operacao fornece o resultado do pipeline. O pos-processamento
    opcional faz parte do sucesso operacional da tentativa.

    Excecoes da operacao sao registradas e propagadas.
    Falhas de persistencia tambem sao propagadas.
    """
    if initial.execution_status != "running":
        raise ValueError("Execucao observavel exige evento running.")

    # Nao executar o pipeline se o inicio nao puder ser persistido.
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
            duration_seconds=time.perf_counter() - started_clock,
        )

    except Exception as exc:
        # Preservar somente resultados parciais de tipos conhecidos.
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
            duration_seconds=time.perf_counter() - started_clock,
            partial_result=safe_partial,
        )

        # Se a persistencia falhar, a excecao de armazenamento
        # sera propagada. Nao afirmar que a falha foi registrada.
        store.finish(failure)
        raise

    # A persistencia terminal fica fora do try acima.
    # Isso evita tentar finalizar duas vezes quando o proprio
    # armazenamento do evento de sucesso falhar.
    store.finish(event)

    return result, event

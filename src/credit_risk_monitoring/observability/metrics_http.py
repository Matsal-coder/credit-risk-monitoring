"""Aplicacao HTTP para exposicao das metricas operacionais."""

from pathlib import Path

from litestar import Litestar, get

from credit_risk_monitoring.observability.metrics_aggregation import (
    aggregate_metrics,
)
from credit_risk_monitoring.observability.metrics_exposition import (
    render_metrics,
)
from credit_risk_monitoring.observability.store import (
    DEFAULT_STORE_PATH,
    SQLiteEventStore,
)


def create_app(
    database_path: Path = DEFAULT_STORE_PATH,
) -> Litestar:
    """Constroi uma aplicacao ASGI independente das CLIs."""
    database = Path(database_path)

    @get(
        "/metrics",
        media_type="text/plain",
        sync_to_thread=True,
    )
    def get_metrics() -> str:
        """Consulta e publica as metricas no instante do scrape."""
        if not database.is_file():
            raise FileNotFoundError("Banco operacional indisponivel.")

        store = SQLiteEventStore(database)
        samples = aggregate_metrics(store)

        return render_metrics(samples)

    return Litestar(
        route_handlers=[get_metrics],
        openapi_config=None,
        debug=False,
    )

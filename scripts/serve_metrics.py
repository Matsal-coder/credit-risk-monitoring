"""Inicia localmente o exporter HTTP de metricas operacionais."""

import argparse
import sys
from pathlib import Path

import uvicorn

from credit_risk_monitoring.observability.metrics_http import create_app


def valid_port(value: str) -> int:
    """Valida uma porta TCP de usuario."""
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Porta invalida.") from exc

    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("Porta deve estar entre 1 e 65535.")

    return port


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Servidor local de metricas Prometheus."
    )
    parser.add_argument(
        "--events-db",
        type=Path,
        required=True,
        help="Banco SQLite operacional existente.",
    )
    parser.add_argument(
        "--port",
        type=valid_port,
        default=8000,
        help="Porta HTTP local (padrao: 8000).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database = args.events_db.resolve()

    if not database.is_file():
        raise FileNotFoundError("Banco SQLite operacional inexistente.")

    app = create_app(database)

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
        log_level="info",
        access_log=False,
        reload=False,
        workers=1,
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(
            f"OPERATIONAL_ERROR: {type(exc).__name__}",
            file=sys.stderr,
        )
        sys.exit(1)

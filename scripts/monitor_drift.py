"""CLI de simulacao e monitoramento de data drift."""

import argparse
import sys
from pathlib import Path

import pandas as pd

from credit_risk_monitoring.drift.monitoring import (
    MonitoringResult,
    monitor_production_batch,
)
from credit_risk_monitoring.drift.reporting import (
    save_monitoring_html,
    save_monitoring_json,
)
from credit_risk_monitoring.drift.simulation import simulate_production_batch
from credit_risk_monitoring.modeling.inference import DEFAULT_MODEL_PATH
from credit_risk_monitoring.observability.adapters import build_monitoring_event
from credit_risk_monitoring.observability.events import start_event
from credit_risk_monitoring.observability.execution import execute_observed
from credit_risk_monitoring.observability.store import SQLiteEventStore


def build_parser() -> argparse.ArgumentParser:
    """Constroi interface de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Monitoramento de risco de credito com Evidently."
    )

    parser.add_argument(
        "--reference",
        type=Path,
        required=True,
        help="CSV de referencia no formato preparado.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Artefato persistido do baseline.",
    )
    parser.add_argument(
        "--batch-id",
        required=True,
        help="Identificador operacional do lote.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        required=True,
        help="Destino do relatorio JSON agregado.",
    )
    parser.add_argument(
        "--html-output",
        type=Path,
        required=True,
        help="Destino do relatorio HTML Evidently.",
    )
    parser.add_argument(
        "--events-db",
        type=Path,
        default=None,
        help="SQLite opcional para registrar eventos operacionais.",
    )

    modes = parser.add_subparsers(
        dest="mode",
        required=True,
    )

    simulate = modes.add_parser(
        "simulate",
        help="Simula um cenario a partir de dados preparados.",
    )
    simulate.add_argument(
        "--production-prepared",
        type=Path,
        required=True,
    )
    simulate.add_argument(
        "--scenario",
        choices=("control", "moderate", "strong"),
        required=True,
    )
    simulate.add_argument(
        "--seed",
        type=int,
        default=642,
    )

    monitor = modes.add_parser(
        "monitor",
        help="Monitora um lote bruto de inferencia.",
    )
    monitor.add_argument(
        "--production-raw",
        type=Path,
        required=True,
    )

    return parser


def validate_paths(
    *,
    reference: Path,
    production: Path,
    model: Path,
    json_output: Path,
    html_output: Path,
) -> None:
    """Impede sobrescrita e colisao entre entradas e saidas."""
    inputs = (reference, production, model)
    outputs = (json_output, html_output)

    for source in inputs:
        if not source.is_file():
            raise ValueError(f"Arquivo de entrada inexistente: {source}")

    resolved_inputs = {path.resolve() for path in inputs}
    resolved_outputs = [path.resolve() for path in outputs]

    if len(set(resolved_outputs)) != len(resolved_outputs):
        raise ValueError("Destinos JSON e HTML devem ser diferentes.")

    if any(path in resolved_inputs for path in resolved_outputs):
        raise ValueError("Saida coincide com arquivo de entrada.")

    for output in outputs:
        if not output.parent.is_dir():
            raise ValueError(f"Diretorio de saida inexistente: {output.parent}")

        if output.exists():
            raise FileExistsError(f"Arquivo de saida ja existe: {output}")


def _production_path(args: argparse.Namespace) -> Path:
    return args.production_prepared if args.mode == "simulate" else args.production_raw


def _run_pipeline(
    args: argparse.Namespace,
) -> tuple[MonitoringResult, int | None]:
    """Executa o pipeline existente sem persistir observabilidade."""
    production_path = _production_path(args)

    validate_paths(
        reference=args.reference,
        production=production_path,
        model=args.model,
        json_output=args.json_output,
        html_output=args.html_output,
    )

    reference = pd.read_csv(
        args.reference,
        low_memory=False,
    )
    production = pd.read_csv(
        production_path,
        low_memory=False,
    )

    if args.mode == "simulate":
        simulation = simulate_production_batch(
            production,
            args.scenario,
            seed=args.seed,
        )
        production_raw = simulation.raw_batch
        scenario_id = args.scenario
        changed_rows = simulation.changed_rows
    else:
        production_raw = production
        scenario_id = "external"
        changed_rows = None

    result = monitor_production_batch(
        reference,
        production_raw,
        batch_id=args.batch_id,
        scenario_id=scenario_id,
        model_path=args.model,
    )

    return result, changed_rows


def _process_result(
    args: argparse.Namespace,
    result: MonitoringResult,
    changed_rows: int | None,
) -> int:
    """Apresenta resultados e exporta relatorios quando aprovados."""
    print("Batch:", result.batch_id)
    print("Scenario:", result.scenario_id)
    print("Quality status:", result.inference.status)
    print("Total rows:", result.inference.total_rows)
    print("Scored rows:", result.inference.scored_rows)

    if changed_rows is not None:
        print("Changed rows:", changed_rows)

    if not result.approved:
        print("Monitoring rejected by quality gate.")
        return 2

    if result.drift is None or result.snapshot is None:
        raise RuntimeError("Monitoramento aprovado sem resultados completos.")

    created_outputs: list[Path] = []

    try:
        saved_json = save_monitoring_json(
            result,
            args.json_output,
        )
        created_outputs.append(saved_json)

        saved_html = save_monitoring_html(
            result,
            args.html_output,
        )
        created_outputs.append(saved_html)

    except Exception:
        for created in created_outputs:
            created.unlink(missing_ok=True)
        raise

    print("Features analyzed:", result.drift.features_analyzed)
    print("Features drifted:", result.drift.features_drifted)
    print("Drift share:", result.drift.drift_share)
    print("Drift detected:", result.drift.drift_detected)
    print("JSON output:", saved_json)
    print("HTML output:", saved_html)

    return 0


def run_cli(args: argparse.Namespace) -> int:
    """Preserva a interface tradicional sem observabilidade."""
    result, changed_rows = _run_pipeline(args)
    return _process_result(args, result, changed_rows)


def _validate_events_db_path(args: argparse.Namespace) -> None:
    """Evita colisao do banco com entradas e relatorios."""
    database = args.events_db.resolve()
    protected = {
        args.reference.resolve(),
        _production_path(args).resolve(),
        args.model.resolve(),
        args.json_output.resolve(),
        args.html_output.resolve(),
    }

    if database in protected:
        raise ValueError("Banco de eventos coincide com entrada ou saida.")


def run_observed_cli(args: argparse.Namespace) -> int:
    """Executa monitoramento instrumentado com persistencia SQLite."""
    _validate_events_db_path(args)

    store = SQLiteEventStore(args.events_db)

    scenario_id = args.scenario if args.mode == "simulate" else "external"

    initial = start_event(
        batch_id=args.batch_id,
        pipeline="monitoring",
        scenario_id=scenario_id,
    )

    changed_rows: int | None = None

    def operation() -> MonitoringResult:
        nonlocal changed_rows
        result, changed_rows = _run_pipeline(args)
        return result

    def postprocess(result: MonitoringResult) -> None:
        _process_result(args, result, changed_rows)

    _, event = execute_observed(
        store=store,
        initial=initial,
        operation=operation,
        build_event=build_monitoring_event,
        postprocess=postprocess,
    )

    return event.exit_code


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.events_db is not None:
            return run_observed_cli(args)

        return run_cli(args)

    except Exception as exc:
        if args.events_db is not None:
            # Nao expor paths nem mensagens potencialmente sensiveis.
            print(
                f"OPERATIONAL_ERROR: {type(exc).__name__}",
                file=sys.stderr,
            )
        else:
            # Mantem a apresentacao historica da CLI nao instrumentada.
            print(
                f"Operational error: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

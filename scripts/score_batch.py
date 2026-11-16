"""Executa scoring em lote com contratos de qualidade bloqueantes."""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from credit_risk_monitoring.modeling.inference import (
    DEFAULT_MODEL_PATH,
    InferenceResult,
    run_quality_gated_inference,
)
from credit_risk_monitoring.observability.adapters import build_scoring_event
from credit_risk_monitoring.observability.events import start_event
from credit_risk_monitoring.observability.execution import execute_observed
from credit_risk_monitoring.observability.publication import (
    PublicationRollbackError,
    PublicationTracker,
)
from credit_risk_monitoring.observability.store import SQLiteEventStore


def build_parser() -> argparse.ArgumentParser:
    """Define a interface do comando de scoring."""
    parser = argparse.ArgumentParser(
        description="Valida lote e executa baseline de credito."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="CSV de entrada sem TARGET e sem indicador derivado.",
    )
    parser.add_argument(
        "--batch-id",
        required=True,
        help="Identificador operacional do lote.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        required=True,
        help="Destino do relatorio JSON.",
    )
    parser.add_argument(
        "--scores-output",
        type=Path,
        help="CSV opcional com probabilidades individuais.",
    )
    parser.add_argument(
        "--events-db",
        type=Path,
        default=None,
        help="SQLite opcional para registrar eventos operacionais.",
    )
    return parser


def _check_output_paths(
    input_path: Path,
    model_path: Path,
    report_path: Path,
    scores_path: Path | None,
) -> None:
    """Impede sobrescrever entradas e resultados anteriores."""
    outputs = [report_path]

    if scores_path is not None:
        outputs.append(scores_path)

    resolved_outputs = [path.resolve() for path in outputs]

    if len(set(resolved_outputs)) != len(resolved_outputs):
        raise ValueError("Caminhos de saida devem ser distintos.")

    protected = {input_path.resolve(), model_path.resolve()}

    for path, resolved in zip(outputs, resolved_outputs, strict=True):
        if resolved in protected:
            raise ValueError("Saida coincide com arquivo de entrada.")

        if path.exists():
            raise FileExistsError("Arquivo de saida ja existe. Use outro caminho.")


def _write_outputs(
    result: InferenceResult,
    report_path: Path,
    scores_path: Path | None,
    publication_tracker: PublicationTracker | None = None,
) -> None:
    """Persiste resultados com rastreamento opcional da publicacao."""
    created_paths: list[Path] = []

    try:
        if result.approved and scores_path is not None:
            scores = pd.DataFrame(
                {
                    "row_index": range(result.scored_rows),
                    "probability_default": result.probabilities,
                    "prediction": result.predictions,
                }
            )

            scores_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with scores_path.open(
                "x",
                encoding="utf-8",
                newline="",
            ) as file:
                created_paths.append(scores_path)
                scores.to_csv(file, index=False)

            if publication_tracker is not None:
                publication_tracker.register(scores_path)

        report_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with report_path.open("x", encoding="utf-8") as file:
            created_paths.append(report_path)
            json.dump(
                result.to_dict(),
                file,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )

        if publication_tracker is not None:
            publication_tracker.register(report_path)

    except Exception as exc:
        if publication_tracker is None:
            # Mantem a limpeza historica sem observabilidade.
            for path in reversed(created_paths):
                path.unlink(missing_ok=True)
        else:
            registered = {artifact.path for artifact in publication_tracker.artifacts}

            untracked = [path for path in created_paths if path not in registered]

            # Nao apaga registros se a compensacao falhar.
            publication_tracker.rollback()

            if untracked:
                raise PublicationRollbackError(
                    "Publicacao falhou com artefatos sem identidade confirmada."
                ) from exc

        raise


def _run_scoring(args: argparse.Namespace) -> InferenceResult:
    """Executa validacao e inferencia existentes."""
    if not args.batch_id.strip():
        raise ValueError("batch_id deve ser nao vazio.")

    _check_output_paths(
        args.input,
        args.model,
        args.report_output,
        args.scores_output,
    )

    batch = pd.read_csv(args.input, low_memory=False)

    return run_quality_gated_inference(
        batch,
        batch_id=args.batch_id,
        model_path=args.model,
    )


def _print_result(
    args: argparse.Namespace,
    result: InferenceResult,
) -> int:
    """Apresenta o resultado com a semantica historica da CLI."""
    if not result.approved:
        print(
            f"REJECTED: batch_id={args.batch_id}; "
            f"rows={result.total_rows}; "
            f"report={args.report_output}"
        )
        return 2

    print(
        f"APPROVED: batch_id={args.batch_id}; "
        f"scored_rows={result.scored_rows}; "
        f"report={args.report_output}"
    )
    return 0


def run_cli(args: argparse.Namespace) -> int:
    """Executa o fluxo tradicional sem persistencia operacional."""
    result = _run_scoring(args)

    _write_outputs(
        result,
        report_path=args.report_output,
        scores_path=args.scores_output,
    )

    return _print_result(args, result)


def _validate_events_db_path(args: argparse.Namespace) -> None:
    """Impede que o SQLite colida com entradas ou saidas."""
    database = args.events_db.resolve()

    protected = {
        args.input.resolve(),
        args.model.resolve(),
        args.report_output.resolve(),
    }

    if args.scores_output is not None:
        protected.add(args.scores_output.resolve())

    if database in protected:
        raise ValueError("Banco de eventos coincide com entrada ou saida.")


def run_observed_cli(args: argparse.Namespace) -> int:
    """Executa scoring com publicacao e confirmacao terminal."""
    _validate_events_db_path(args)

    store = SQLiteEventStore(args.events_db)

    initial = start_event(
        batch_id=args.batch_id,
        pipeline="scoring",
        scenario_id="not_applicable",
    )

    publication_tracker = PublicationTracker()

    def postprocess(result: InferenceResult) -> None:
        _write_outputs(
            result,
            report_path=args.report_output,
            scores_path=args.scores_output,
            publication_tracker=publication_tracker,
        )

    result, event = execute_observed(
        store=store,
        initial=initial,
        operation=lambda: _run_scoring(args),
        build_event=build_scoring_event,
        postprocess=postprocess,
        rollback_publication=publication_tracker.rollback,
    )

    # Anunciar conclusao somente apos persistencia terminal.
    _print_result(args, result)

    return event.exit_code


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada compativel com o comando anterior."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.events_db is not None:
        return run_observed_cli(args)

    return run_cli(args)


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as exc:
        # Preserva o contrato de erro sanitizado da CLI.
        print(
            f"OPERATIONAL_ERROR: {type(exc).__name__}",
            file=sys.stderr,
        )
        exit_code = 1

    sys.exit(exit_code)

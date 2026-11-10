"""Executa scoring em lote com contratos de qualidade bloqueantes."""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from credit_risk_monitoring.modeling.inference import (
    DEFAULT_MODEL_PATH,
    run_quality_gated_inference,
)


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
    result,
    report_path: Path,
    scores_path: Path | None,
) -> None:
    """Persiste resultados sem deixar arquivos parciais em falhas."""
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

    except Exception:
        for path in reversed(created_paths):
            path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    """Executa o lote e retorna codigo de saida operacional."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.batch_id.strip():
        raise ValueError("batch_id deve ser nao vazio.")

    _check_output_paths(
        args.input,
        args.model,
        args.report_output,
        args.scores_output,
    )

    # Leitura em memoria; nao altera o arquivo original.
    batch = pd.read_csv(args.input, low_memory=False)

    result = run_quality_gated_inference(
        batch,
        batch_id=args.batch_id,
        model_path=args.model,
    )

    _write_outputs(
        result,
        report_path=args.report_output,
        scores_path=args.scores_output,
    )

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


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as exc:
        # Nao imprime dados, payloads nem mensagens potencialmente
        # sensiveis provenientes das excecoes internas.
        print(
            f"OPERATIONAL_ERROR: {type(exc).__name__}",
            file=sys.stderr,
        )
        exit_code = 1

    sys.exit(exit_code)

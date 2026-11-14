"""Exportacao segura de resultados agregados de monitoramento."""

import json
import math
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from credit_risk_monitoring.drift.monitoring import MonitoringResult


def build_monitoring_payload(result: MonitoringResult) -> dict:
    """Constrói payload agregado sem previsoes individuais."""
    if not result.approved or result.drift is None:
        raise ValueError("Nao e permitido exportar monitoramento nao aprovado.")

    inference = result.inference
    scored_rows = inference.scored_rows

    if scored_rows <= 0:
        raise ValueError("Quantidade de linhas pontuadas invalida.")

    if (
        len(inference.probabilities) != scored_rows
        or len(inference.predictions) != scored_rows
    ):
        raise ValueError("Resultados de inferencia inconsistentes.")

    mean_probability = math.fsum(inference.probabilities) / scored_rows
    predicted_defaults = int(sum(inference.predictions))

    if (
        not math.isfinite(mean_probability)
        or not 0 <= mean_probability <= 1
        or not 0 <= predicted_defaults <= scored_rows
    ):
        raise ValueError("Metricas agregadas invalidas.")

    payload = result.to_dict()

    for validation in payload.get("inference", {}).get("validations", []):
        violations = validation.get("violations")

        if isinstance(violations, tuple):
            validation["violations"] = list(violations)

    payload["prediction_summary"] = {
        "scored_rows": scored_rows,
        "mean_default_probability": mean_probability,
        "predicted_defaults": predicted_defaults,
        "positive_prediction_rate": predicted_defaults / scored_rows,
        "model_threshold": inference.threshold,
    }

    return payload


def save_monitoring_json(
    result: MonitoringResult,
    output_path: Path,
) -> Path:
    """Grava JSON agregado sem sobrescrever e sem deixar escrita parcial."""
    payload = build_monitoring_payload(result)

    serialized = json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    )

    destination = Path(output_path)

    if not destination.parent.is_dir():
        raise ValueError("Diretorio de saida inexistente.")

    created = False

    try:
        # Modo x garante criacao exclusiva.
        with destination.open("x", encoding="utf-8") as output:
            created = True
            output.write(serialized)
            output.write("\n")

    except Exception:
        # Remove somente o arquivo criado por esta chamada.
        if created:
            destination.unlink(missing_ok=True)
        raise

    return destination


def save_monitoring_html(
    result: MonitoringResult,
    output_path: Path,
) -> Path:
    """Exporta snapshot Evidently sem sobrescrever arquivos.

    O HTML e gerado primeiro em diretorio temporario.
    A copia definitiva usa criacao exclusiva.
    """
    if not result.approved or result.drift is None:
        raise ValueError("Nao e permitido exportar monitoramento nao aprovado.")

    if result.snapshot is None:
        raise ValueError("Snapshot Evidently indisponivel.")

    destination = Path(output_path)

    if not destination.parent.is_dir():
        raise ValueError("Diretorio de saida inexistente.")

    if destination.exists():
        raise FileExistsError(f"Arquivo de saida ja existe: {destination}")

    with TemporaryDirectory() as temporary:
        temporary_path = Path(temporary) / "evidently-report.html"

        # A API do Evidently recebe um caminho de arquivo.
        result.snapshot.save_html(str(temporary_path))

        if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
            raise ValueError("HTML Evidently ausente ou vazio.")

        created = False

        try:
            # Modo xb: criacao exclusiva, sem sobrescrita.
            with (
                temporary_path.open("rb") as source,
                destination.open("xb") as output,
            ):
                created = True
                shutil.copyfileobj(source, output)

        except Exception:
            # Remove apenas o arquivo criado por esta tentativa.
            # Um arquivo preexistente nunca deve ser excluido.
            if created:
                destination.unlink(missing_ok=True)
            raise

    return destination

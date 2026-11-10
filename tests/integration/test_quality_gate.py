"""Testes de integracao da barreira de qualidade e inferencia."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
import pytest

from credit_risk_monitoring.data.inference import (
    prepare_inference_features,
)
from credit_risk_monitoring.data.preparation import MODEL_FEATURES
from credit_risk_monitoring.modeling.inference import (
    run_quality_gated_inference,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "score_batch.py"
MODEL_PATH = PROJECT_ROOT / "artifacts" / "baseline_model.joblib"


@pytest.fixture
def raw_batch() -> pd.DataFrame:
    """Lote inteiramente sintetico com duas solicitacoes."""
    return pd.DataFrame(
        {
            "SK_ID_CURR": [100001, 100002],
            "AMT_CREDIT": [450000.0, 300000.0],
            "AMT_INCOME_TOTAL": [180000.0, 120000.0],
            "AMT_ANNUITY": [25000.0, 18000.0],
            "AMT_GOODS_PRICE": [400000.0, 280000.0],
            "EXT_SOURCE_2": [0.55, 0.60],
            "EXT_SOURCE_3": [0.65, np.nan],
            "DAYS_BIRTH": [-12000, -16000],
            "DAYS_EMPLOYED": [-2000.0, 365243.0],
            "DAYS_REGISTRATION": [-3000.0, -5000.0],
            "CNT_CHILDREN": [1, 0],
            "CNT_FAM_MEMBERS": [3.0, 2.0],
            "NAME_INCOME_TYPE": ["Working", "Pensioner"],
            "NAME_EDUCATION_TYPE": [
                "Higher education",
                "Secondary / secondary special",
            ],
            "FLAG_OWN_CAR": ["N", "Y"],
            "FLAG_OWN_REALTY": ["Y", "N"],
            "NAME_CONTRACT_TYPE": [
                "Cash loans",
                "Revolving loans",
            ],
        }
    )


def run_cli(
    input_path: Path,
    report_path: Path,
    scores_path: Path | None = None,
    model_path: Path = MODEL_PATH,
) -> subprocess.CompletedProcess:
    """Executa o script real sem modificar o repositorio."""
    command = [
        sys.executable,
        str(SCRIPT_PATH),
        "--input",
        str(input_path),
        "--batch-id",
        "integration-test",
        "--model",
        str(model_path),
        "--report-output",
        str(report_path),
    ]

    if scores_path is not None:
        command.extend(["--scores-output", str(scores_path)])

    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def test_valid_cli_scores_match_persisted_baseline(
    tmp_path: Path,
    raw_batch: pd.DataFrame,
) -> None:
    """Compara scoring via CLI com o modelo oficial."""
    input_path = tmp_path / "valid.csv"
    report_path = tmp_path / "report.json"
    scores_path = tmp_path / "scores.csv"

    raw_batch.to_csv(input_path, index=False)

    completed = run_cli(
        input_path,
        report_path,
        scores_path,
    )

    assert completed.returncode == 0, completed.stderr
    assert report_path.is_file()
    assert scores_path.is_file()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    scores = pd.read_csv(scores_path)

    assert report["status"] == "approved"
    assert report["scored_rows"] == len(raw_batch)
    assert len(report["validations"]) == 2
    assert all(item["status"] == "approved" for item in report["validations"])

    artifact = joblib.load(MODEL_PATH)
    pipeline = artifact["pipeline"]
    metadata = artifact["metadata"]

    prepared = prepare_inference_features(raw_batch)
    expected = pipeline.predict_proba(prepared.loc[:, MODEL_FEATURES])[:, 1]

    np.testing.assert_allclose(
        scores["probability_default"].to_numpy(),
        expected,
        rtol=1e-10,
        atol=1e-12,
    )

    threshold = metadata["threshold"]
    expected_predictions = (expected >= threshold).astype(int)

    np.testing.assert_array_equal(
        scores["prediction"].to_numpy(),
        expected_predictions,
    )

    assert report["threshold"] == threshold
    assert report["scored_rows"] == 2
    assert scores["row_index"].tolist() == [0, 1]


def test_invalid_cli_rejects_without_scores(
    tmp_path: Path,
    raw_batch: pd.DataFrame,
) -> None:
    """Lote invalido gera relatorio, mas nenhum score."""
    raw_batch.loc[0, "AMT_CREDIT"] = -100.0

    input_path = tmp_path / "invalid.csv"
    report_path = tmp_path / "rejected.json"
    scores_path = tmp_path / "scores.csv"

    raw_batch.to_csv(input_path, index=False)

    completed = run_cli(
        input_path,
        report_path,
        scores_path,
    )

    assert completed.returncode == 2
    assert "REJECTED" in completed.stdout
    assert report_path.is_file()
    assert not scores_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["status"] == "rejected"
    assert report["scored_rows"] == 0
    assert report["threshold"] is None
    assert len(report["validations"]) == 1

    violations = report["validations"][0]["violations"]

    assert any(
        item["column"] == "AMT_CREDIT" and item["rule"] == "positive_credit"
        for item in violations
    )


def test_multiple_violations_are_reported(
    tmp_path: Path,
    raw_batch: pd.DataFrame,
) -> None:
    """Falhas independentes sao reportadas no mesmo lote."""
    raw_batch.loc[0, "AMT_CREDIT"] = -100.0
    raw_batch.loc[1, "EXT_SOURCE_2"] = 1.5

    input_path = tmp_path / "multi_invalid.csv"
    report_path = tmp_path / "multi_report.json"

    raw_batch.to_csv(input_path, index=False)

    completed = run_cli(input_path, report_path)

    assert completed.returncode == 2

    report = json.loads(report_path.read_text(encoding="utf-8"))
    violations = report["validations"][0]["violations"]

    rules = {(item["column"], item["rule"]) for item in violations}

    assert ("AMT_CREDIT", "positive_credit") in rules
    assert ("EXT_SOURCE_2", "external_score_range") in rules
    assert report["scored_rows"] == 0


def test_existing_output_is_not_overwritten(
    tmp_path: Path,
    raw_batch: pd.DataFrame,
) -> None:
    """Resultados preexistentes devem ser preservados."""
    input_path = tmp_path / "valid.csv"
    report_path = tmp_path / "existing.json"

    raw_batch.to_csv(input_path, index=False)
    report_path.write_text("existing-content", encoding="utf-8")

    completed = run_cli(input_path, report_path)

    assert completed.returncode == 1
    assert "OPERATIONAL_ERROR" in completed.stderr

    assert report_path.read_text(encoding="utf-8") == "existing-content"


def test_missing_model_does_not_publish_approval(
    tmp_path: Path,
    raw_batch: pd.DataFrame,
) -> None:
    """Falha ao carregar modelo nao gera resultados aprovados."""
    input_path = tmp_path / "valid.csv"
    report_path = tmp_path / "report.json"
    scores_path = tmp_path / "scores.csv"
    missing_model = tmp_path / "missing-model.joblib"

    raw_batch.to_csv(input_path, index=False)

    completed = run_cli(
        input_path,
        report_path,
        scores_path,
        model_path=missing_model,
    )

    assert completed.returncode == 1
    assert "OPERATIONAL_ERROR" in completed.stderr
    assert not report_path.exists()
    assert not scores_path.exists()


def test_valid_cli_without_scores_output(
    tmp_path: Path,
    raw_batch: pd.DataFrame,
) -> None:
    """Relatorio operacional pode ser gerado sem scores individuais."""
    input_path = tmp_path / "valid.csv"
    report_path = tmp_path / "report.json"

    raw_batch.to_csv(input_path, index=False)

    completed = run_cli(input_path, report_path)

    assert completed.returncode == 0

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["status"] == "approved"
    assert report["scored_rows"] == 2
    assert "probabilities" not in report
    assert "predictions" not in report

    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "report.json",
        "valid.csv",
    ]


def test_report_write_failure_cleans_created_scores(
    tmp_path: Path,
    raw_batch: pd.DataFrame,
) -> None:
    """Falha ao gravar JSON remove o CSV criado na tentativa."""
    spec = importlib.util.spec_from_file_location(
        "quality_score_batch_test_module",
        SCRIPT_PATH,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    result = run_quality_gated_inference(
        raw_batch,
        batch_id="write-failure-test",
        model_path=MODEL_PATH,
    )

    assert result.approved

    report_path = tmp_path / "report.json"
    scores_path = tmp_path / "scores.csv"

    with patch.object(
        module.json,
        "dump",
        side_effect=OSError("simulated write failure"),
    ):
        with pytest.raises(OSError, match="simulated write failure"):
            module._write_outputs(
                result,
                report_path=report_path,
                scores_path=scores_path,
            )

    assert not report_path.exists()
    assert not scores_path.exists()

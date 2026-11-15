"""Testes da CLI de scoring com observabilidade SQLite."""

import importlib.util
import json
from pathlib import Path

import pytest

from credit_risk_monitoring.modeling.inference import InferenceResult
from credit_risk_monitoring.observability.store import SQLiteEventStore
from credit_risk_monitoring.quality.results import (
    QualityViolation,
    ValidationResult,
)

SCRIPT_PATH = Path("scripts/score_batch.py")


@pytest.fixture
def cli():
    spec = importlib.util.spec_from_file_location(
        "observed_scoring_cli",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def paths(tmp_path):
    input_path = tmp_path / "input.csv"
    model_path = tmp_path / "model.joblib"

    input_path.write_text("placeholder", encoding="utf-8")
    model_path.write_text("placeholder", encoding="utf-8")

    return {
        "input": input_path,
        "model": model_path,
        "report": tmp_path / "report.json",
        "scores": tmp_path / "scores.csv",
        "database": tmp_path / "events.sqlite3",
    }


def arguments(cli, paths, *, with_scores=False):
    command = [
        "--input",
        str(paths["input"]),
        "--batch-id",
        "observed-scoring",
        "--model",
        str(paths["model"]),
        "--report-output",
        str(paths["report"]),
        "--events-db",
        str(paths["database"]),
    ]

    if with_scores:
        command.extend(["--scores-output", str(paths["scores"])])

    return cli.build_parser().parse_args(command)


def make_result(*, rejected=False):
    violations = (
        (
            QualityViolation(
                column="AMT_CREDIT",
                rule="positive_credit",
                count=2,
            ),
        )
        if rejected
        else ()
    )

    validation = ValidationResult(
        batch_id="observed-scoring",
        stage="raw_inference",
        status="rejected" if rejected else "approved",
        total_rows=5,
        violations=violations,
    )

    return InferenceResult(
        batch_id="observed-scoring",
        status="rejected" if rejected else "approved",
        total_rows=5,
        validations=(validation,),
        threshold=None if rejected else 0.14,
        probabilities=() if rejected else (0.2,) * 5,
        predictions=() if rejected else (1,) * 5,
    )


def mock_inference(cli, monkeypatch, result):
    monkeypatch.setattr(
        cli.pd,
        "read_csv",
        lambda *args, **kwargs: object(),
    )

    monkeypatch.setattr(
        cli,
        "run_quality_gated_inference",
        lambda *args, **kwargs: result,
    )


def read_event(paths):
    store = SQLiteEventStore(paths["database"])
    assert store.count() == 1
    return store.list_events()[0]


def test_parser_accepts_events_db(cli, paths):
    args = arguments(cli, paths)

    assert args.events_db == paths["database"]
    assert args.scores_output is None


def test_approved_scoring_is_persisted(cli, paths, monkeypatch):
    mock_inference(cli, monkeypatch, make_result())

    exit_code = cli.run_observed_cli(arguments(cli, paths))
    event = read_event(paths)

    assert exit_code == 0
    assert event.execution_status == "completed"
    assert event.quality_status == "approved"
    assert event.drift_status == "not_evaluated"
    assert event.scored_rows == 5
    assert event.quality_violations == 0
    assert paths["report"].is_file()

    report = json.loads(paths["report"].read_text(encoding="utf-8"))
    assert report["status"] == "approved"
    assert "probabilities" not in report


def test_rejected_scoring_does_not_create_scores(cli, paths, monkeypatch):
    mock_inference(cli, monkeypatch, make_result(rejected=True))

    exit_code = cli.run_observed_cli(arguments(cli, paths, with_scores=True))
    event = read_event(paths)

    assert exit_code == 2
    assert event.execution_status == "completed"
    assert event.quality_status == "rejected"
    assert event.scored_rows == 0
    assert event.quality_violations == 2
    assert paths["report"].is_file()
    assert not paths["scores"].exists()


def test_approved_scoring_can_export_scores(cli, paths, monkeypatch):
    mock_inference(cli, monkeypatch, make_result())

    exit_code = cli.run_observed_cli(arguments(cli, paths, with_scores=True))

    assert exit_code == 0
    assert paths["scores"].is_file()

    event = read_event(paths)
    serialized = str(event.to_dict())

    assert "probabilities" not in serialized
    assert "predictions" not in serialized
    assert "row_index" not in serialized


def test_inference_exception_is_persisted(cli, paths, monkeypatch):
    def failing_inference(*args, **kwargs):
        raise FileNotFoundError("/private/model.joblib")

    monkeypatch.setattr(
        cli.pd,
        "read_csv",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        cli,
        "run_quality_gated_inference",
        failing_inference,
    )

    with pytest.raises(FileNotFoundError):
        cli.run_observed_cli(arguments(cli, paths))

    event = read_event(paths)

    assert event.execution_status == "failed"
    assert event.exit_code == 1
    assert event.quality_status == "not_evaluated"
    assert event.error_type == "FileNotFoundError"
    assert "/private/" not in str(event.to_dict())
    assert not paths["report"].exists()


def test_export_exception_preserves_partial_inference(cli, paths, monkeypatch):
    mock_inference(cli, monkeypatch, make_result())

    def failing_export(*args, **kwargs):
        raise OSError("Sensitive output path")

    monkeypatch.setattr(
        cli,
        "_write_outputs",
        failing_export,
    )

    with pytest.raises(OSError):
        cli.run_observed_cli(arguments(cli, paths))

    event = read_event(paths)

    assert event.execution_status == "failed"
    assert event.exit_code == 1
    assert event.quality_status == "approved"
    assert event.scored_rows == 5
    assert event.error_type == "OSError"
    assert "Sensitive output path" not in str(event.to_dict())


def test_database_collision_is_rejected(cli, paths):
    args = arguments(cli, paths)
    args.events_db = paths["input"]

    with pytest.raises(ValueError, match="coincide"):
        cli.run_observed_cli(args)

    assert paths["input"].read_text(encoding="utf-8") == "placeholder"


def test_existing_report_records_operational_failure(cli, paths):
    paths["report"].write_text(
        "original",
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError):
        cli.run_observed_cli(arguments(cli, paths))

    event = read_event(paths)

    assert event.execution_status == "failed"
    assert event.exit_code == 1
    assert event.quality_status == "not_evaluated"
    assert event.error_type == "FileExistsError"
    assert paths["report"].read_text(encoding="utf-8") == "original"

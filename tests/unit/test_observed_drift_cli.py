"""Testes da integracao da CLI de drift com SQLite."""

import importlib.util
from pathlib import Path

import pytest

from credit_risk_monitoring.drift.monitoring import MonitoringResult
from credit_risk_monitoring.drift.results import DriftSummary
from credit_risk_monitoring.modeling.inference import InferenceResult
from credit_risk_monitoring.observability.store import SQLiteEventStore
from credit_risk_monitoring.quality.results import ValidationResult

SCRIPT_PATH = Path("scripts/monitor_drift.py")


@pytest.fixture
def cli():
    spec = importlib.util.spec_from_file_location(
        "observed_drift_cli",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def paths(tmp_path):
    reference = tmp_path / "reference.csv"
    production = tmp_path / "production.csv"
    model = tmp_path / "model.joblib"

    for path in (reference, production, model):
        path.write_text("placeholder", encoding="utf-8")

    return {
        "reference": reference,
        "production": production,
        "model": model,
        "json": tmp_path / "report.json",
        "html": tmp_path / "report.html",
        "database": tmp_path / "events.sqlite3",
    }


def arguments(cli, paths, *, batch_id="observed-test"):
    return cli.build_parser().parse_args(
        [
            "--reference",
            str(paths["reference"]),
            "--model",
            str(paths["model"]),
            "--batch-id",
            batch_id,
            "--json-output",
            str(paths["json"]),
            "--html-output",
            str(paths["html"]),
            "--events-db",
            str(paths["database"]),
            "monitor",
            "--production-raw",
            str(paths["production"]),
        ]
    )


def make_result(*, rejected=False, drifted=False):
    validation = ValidationResult(
        batch_id="observed-test",
        stage="raw_inference",
        status="rejected" if rejected else "approved",
        total_rows=5,
    )

    inference = InferenceResult(
        batch_id="observed-test",
        status="rejected" if rejected else "approved",
        total_rows=5,
        validations=(validation,),
        threshold=None if rejected else 0.14,
        probabilities=() if rejected else (0.2,) * 5,
        predictions=() if rejected else (1,) * 5,
    )

    drift = None
    if not rejected:
        drift = DriftSummary(
            batch_id="observed-test",
            scenario_id="external",
            reference_rows=10,
            production_rows=5,
            features_analyzed=16,
            features_drifted=2 if drifted else 0,
            drift_share=0.125 if drifted else 0.0,
            drift_detected=drifted,
            feature_results=(),
        )

    return MonitoringResult(
        batch_id="observed-test",
        scenario_id="external",
        inference=inference,
        drift=drift,
        snapshot=None if rejected else object(),
    )


def mock_pipeline(cli, monkeypatch, result):
    monkeypatch.setattr(
        cli.pd,
        "read_csv",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        cli,
        "monitor_production_batch",
        lambda *args, **kwargs: result,
    )


def test_parser_accepts_events_db(cli, paths):
    args = arguments(cli, paths)

    assert args.events_db == paths["database"]
    assert args.mode == "monitor"


def test_rejection_persists_exit_2(cli, paths, monkeypatch):
    mock_pipeline(cli, monkeypatch, make_result(rejected=True))

    args = arguments(cli, paths)
    exit_code = cli.run_observed_cli(args)

    store = SQLiteEventStore(paths["database"])
    event = store.list_events()[0]

    assert exit_code == 2
    assert store.count() == 1
    assert event.execution_status == "completed"
    assert event.quality_status == "rejected"
    assert event.scored_rows == 0
    assert event.drift_status == "not_evaluated"
    assert not paths["json"].exists()
    assert not paths["html"].exists()


def test_drift_persists_exit_0(cli, paths, monkeypatch):
    mock_pipeline(cli, monkeypatch, make_result(drifted=True))

    def save_json(_result, path):
        path.write_text("{}", encoding="utf-8")
        return path

    def save_html(_result, path):
        path.write_text("<html></html>", encoding="utf-8")
        return path

    monkeypatch.setattr(cli, "save_monitoring_json", save_json)
    monkeypatch.setattr(cli, "save_monitoring_html", save_html)

    args = arguments(cli, paths)
    exit_code = cli.run_observed_cli(args)

    store = SQLiteEventStore(paths["database"])
    event = store.list_events()[0]

    assert exit_code == 0
    assert event.execution_status == "completed"
    assert event.drift_status == "detected"
    assert event.features_analyzed == 16
    assert event.features_drifted == 2
    assert paths["json"].is_file()
    assert paths["html"].is_file()


def test_export_failure_persists_exit_1(cli, paths, monkeypatch):
    mock_pipeline(cli, monkeypatch, make_result(drifted=True))

    def save_json(_result, path):
        path.write_text("temporary", encoding="utf-8")
        return path

    def fail_html(_result, _path):
        raise OSError("sensitive path /private/data")

    monkeypatch.setattr(cli, "save_monitoring_json", save_json)
    monkeypatch.setattr(cli, "save_monitoring_html", fail_html)

    args = arguments(cli, paths)

    with pytest.raises(OSError):
        cli.run_observed_cli(args)

    event = SQLiteEventStore(paths["database"]).list_events()[0]

    assert event.execution_status == "failed"
    assert event.exit_code == 1
    assert event.error_type == "OSError"
    assert event.drift_status == "detected"
    assert "sensitive path" not in str(event.to_dict())
    assert not paths["json"].exists()
    assert not paths["html"].exists()


def test_missing_input_is_recorded(cli, paths):
    paths["production"].unlink()

    args = arguments(cli, paths)

    with pytest.raises(ValueError, match="inexistente"):
        cli.run_observed_cli(args)

    event = SQLiteEventStore(paths["database"]).list_events()[0]

    assert event.execution_status == "failed"
    assert event.exit_code == 1
    assert event.quality_status == "not_evaluated"
    assert event.error_type == "ValueError"


def test_database_cannot_overlap_input(cli, paths):
    args = arguments(cli, paths)
    args.events_db = paths["reference"]

    with pytest.raises(ValueError, match="coincide"):
        cli.run_observed_cli(args)

    assert paths["reference"].read_text(encoding="utf-8") == "placeholder"

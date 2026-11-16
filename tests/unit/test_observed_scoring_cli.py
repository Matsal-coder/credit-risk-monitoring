"""Testes da CLI de scoring com observabilidade SQLite."""

import importlib.util
import json
from pathlib import Path

import pytest

from credit_risk_monitoring.modeling.inference import InferenceResult
from credit_risk_monitoring.observability.publication import (
    PublicationRollbackError,
)
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


def test_terminal_failure_after_scoring_publication(
    cli,
    paths,
    monkeypatch,
    capsys,
):
    """Falha terminal nao pode manter publicacao inconclusiva."""
    mock_inference(cli, monkeypatch, make_result())

    original_store = cli.SQLiteEventStore
    stores = []

    class FailingTerminalStore(original_store):
        def finish(self, event):
            raise OSError("simulated SQLite terminal failure")

    def make_store(path):
        store = FailingTerminalStore(path)
        stores.append(store)
        return store

    monkeypatch.setattr(cli, "SQLiteEventStore", make_store)

    args = arguments(cli, paths, with_scores=True)

    with pytest.raises(
        OSError,
        match="simulated SQLite terminal failure",
    ):
        cli.run_observed_cli(args)

    output = capsys.readouterr()

    assert "APPROVED:" not in output.out
    assert "REJECTED:" not in output.out

    assert len(stores) == 1
    persisted = stores[0].list_events()

    assert len(persisted) == 1
    assert persisted[0].execution_status == "running"

    # O SQLite nao confirmou a conclusao.
    # A publicacao deve ser compensada quando o estado
    # running puder ser confirmado com seguranca.
    assert not paths["report"].exists()
    assert not paths["scores"].exists()


def test_terminal_failure_with_unavailable_sqlite_preserves_outputs(
    cli,
    paths,
    monkeypatch,
    capsys,
):
    """Estado terminal indeterminado preserva artefatos."""
    mock_inference(cli, monkeypatch, make_result())

    original_store = cli.SQLiteEventStore

    class UnavailableTerminalStore(original_store):
        def finish(self, event):
            raise OSError("simulated terminal write failure")

        def get(self, execution_id):
            raise OSError("simulated SQLite read failure")

    monkeypatch.setattr(
        cli,
        "SQLiteEventStore",
        UnavailableTerminalStore,
    )

    args = arguments(cli, paths, with_scores=True)

    with pytest.raises(OSError):
        cli.run_observed_cli(args)

    captured = capsys.readouterr()

    assert "APPROVED:" not in captured.out
    assert "REJECTED:" not in captured.out

    assert paths["report"].is_file()
    assert paths["scores"].is_file()

    # A leitura interna falhou, mas o banco pode ser
    # reaberto fora da simulacao para inspecao.
    persisted = original_store(paths["database"]).list_events()

    assert len(persisted) == 1
    assert persisted[0].execution_status == "running"


def test_terminal_failure_preserves_replaced_scoring_report(
    cli,
    paths,
    monkeypatch,
    capsys,
):
    """Nao exclui relatorio substituido antes da compensacao."""
    mock_inference(cli, monkeypatch, make_result())

    original_store = cli.SQLiteEventStore

    class ReplacingTerminalStore(original_store):
        def finish(self, event):
            replacement = paths["report"].parent / "replacement.json"
            replacement.write_text(
                "replacement-content",
                encoding="utf-8",
            )
            replacement.replace(paths["report"])
            raise OSError("simulated terminal failure")

    monkeypatch.setattr(
        cli,
        "SQLiteEventStore",
        ReplacingTerminalStore,
    )

    args = arguments(cli, paths, with_scores=True)

    with pytest.raises(
        PublicationRollbackError,
        match="Identidade de artefato alterada",
    ):
        cli.run_observed_cli(args)

    captured = capsys.readouterr()

    assert "APPROVED:" not in captured.out
    assert "REJECTED:" not in captured.out

    assert paths["report"].read_text(encoding="utf-8") == "replacement-content"

    # A verificacao integral bloqueia a exclusao de
    # outros arquivos quando detecta identidade divergente.
    assert paths["scores"].is_file()

    persisted = original_store(paths["database"]).list_events()

    assert len(persisted) == 1
    assert persisted[0].execution_status == "running"


def test_scoring_finish_error_after_commit_preserves_outputs(
    cli,
    paths,
    monkeypatch,
    capsys,
):
    """Excecao apos commit nao deve excluir arquivos publicados."""
    mock_inference(cli, monkeypatch, make_result())

    original_store = cli.SQLiteEventStore

    class PostCommitFailureStore(original_store):
        def finish(self, event):
            super().finish(event)
            raise OSError("simulated failure after commit")

    monkeypatch.setattr(
        cli,
        "SQLiteEventStore",
        PostCommitFailureStore,
    )

    with pytest.raises(
        OSError,
        match="simulated failure after commit",
    ):
        cli.run_observed_cli(arguments(cli, paths, with_scores=True))

    captured = capsys.readouterr()

    assert "APPROVED:" not in captured.out
    assert paths["report"].is_file()
    assert paths["scores"].is_file()

    event = original_store(paths["database"]).list_events()[0]

    assert event.execution_status == "completed"
    assert event.exit_code == 0


def test_scoring_registration_failure_preserves_untracked_report(
    cli,
    paths,
    monkeypatch,
    capsys,
):
    """Falha de registro preserva relatorio sem identidade confirmada."""
    from credit_risk_monitoring.observability.publication import (
        PublicationRollbackError,
    )

    mock_inference(cli, monkeypatch, make_result())

    def fail_register(self, path):
        if path == paths["report"]:
            raise OSError("simulated identity capture failure")

        return original_register(self, path)

    original_register = cli.PublicationTracker.register

    monkeypatch.setattr(
        cli.PublicationTracker,
        "register",
        fail_register,
    )

    with pytest.raises(
        PublicationRollbackError,
        match="artefatos sem identidade confirmada",
    ):
        cli.run_observed_cli(arguments(cli, paths, with_scores=True))

    captured = capsys.readouterr()

    assert "APPROVED:" not in captured.out
    assert paths["report"].is_file()
    assert not paths["scores"].exists()

    event = SQLiteEventStore(paths["database"]).list_events()[0]

    assert event.execution_status == "failed"
    assert event.exit_code == 1


def test_scoring_process_sanitizes_operational_failure(tmp_path):
    """Processo real retorna Exit 1 sem expor detalhe sensivel."""
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    script = project_root / "scripts" / "score_batch.py"

    # Arquivo inexistente para provocar erro operacional
    # durante uma execucao instrumentada.
    missing_input = tmp_path / "sensitive-customer-input.csv"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input",
            str(missing_input),
            "--batch-id",
            "operational-error-test",
            "--model",
            str(tmp_path / "model.joblib"),
            "--report-output",
            str(tmp_path / "report.json"),
            "--events-db",
            str(tmp_path / "events.sqlite"),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "OPERATIONAL_ERROR:" in completed.stderr
    assert str(missing_input) not in completed.stderr
    assert not (tmp_path / "report.json").exists()

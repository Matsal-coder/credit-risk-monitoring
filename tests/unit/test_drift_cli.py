"""Testes de argumentos e protecao de caminhos da CLI."""

import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT_PATH = Path("scripts/monitor_drift.py")


@pytest.fixture(scope="module")
def cli_module():
    """Carrega a CLI sem executar seu ponto de entrada."""
    spec = importlib.util.spec_from_file_location(
        "monitor_drift_cli",
        SCRIPT_PATH,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


@pytest.fixture
def valid_paths(tmp_path):
    """Cria arquivos pequenos para validar somente caminhos."""
    reference = tmp_path / "reference.csv"
    production = tmp_path / "production.csv"
    model = tmp_path / "model.joblib"

    for path in (reference, production, model):
        path.write_text("test", encoding="utf-8")

    return {
        "reference": reference,
        "production": production,
        "model": model,
        "json_output": tmp_path / "report.json",
        "html_output": tmp_path / "report.html",
    }


def test_parser_accepts_simulation(cli_module):
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "--reference",
            "reference.csv",
            "--batch-id",
            "test-batch",
            "--json-output",
            "report.json",
            "--html-output",
            "report.html",
            "simulate",
            "--production-prepared",
            "test.csv",
            "--scenario",
            "strong",
            "--seed",
            "642",
        ]
    )

    assert args.mode == "simulate"
    assert args.scenario == "strong"
    assert args.seed == 642


def test_parser_accepts_external_monitoring(cli_module):
    parser = cli_module.build_parser()

    args = parser.parse_args(
        [
            "--reference",
            "reference.csv",
            "--batch-id",
            "external-batch",
            "--json-output",
            "report.json",
            "--html-output",
            "report.html",
            "monitor",
            "--production-raw",
            "production.csv",
        ]
    )

    assert args.mode == "monitor"
    assert args.production_raw == Path("production.csv")


def test_parser_rejects_invalid_scenario(cli_module):
    parser = cli_module.build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(
            [
                "--reference",
                "reference.csv",
                "--batch-id",
                "test",
                "--json-output",
                "report.json",
                "--html-output",
                "report.html",
                "simulate",
                "--production-prepared",
                "test.csv",
                "--scenario",
                "unknown",
            ]
        )

    assert exc.value.code == 2


def test_validate_paths_accepts_valid_paths(
    cli_module,
    valid_paths,
):
    cli_module.validate_paths(**valid_paths)


def test_validate_paths_rejects_missing_input(
    cli_module,
    valid_paths,
):
    valid_paths["production"].unlink()

    with pytest.raises(ValueError, match="inexistente"):
        cli_module.validate_paths(**valid_paths)


def test_validate_paths_rejects_input_overwrite(
    cli_module,
    valid_paths,
):
    valid_paths["json_output"] = valid_paths["reference"]

    with pytest.raises(ValueError, match="coincide"):
        cli_module.validate_paths(**valid_paths)


def test_validate_paths_rejects_same_output(
    cli_module,
    valid_paths,
):
    valid_paths["html_output"] = valid_paths["json_output"]

    with pytest.raises(ValueError, match="diferentes"):
        cli_module.validate_paths(**valid_paths)


def test_validate_paths_rejects_existing_output(
    cli_module,
    valid_paths,
):
    destination = valid_paths["json_output"]
    destination.write_text("original", encoding="utf-8")

    with pytest.raises(FileExistsError):
        cli_module.validate_paths(**valid_paths)

    assert destination.read_text(encoding="utf-8") == "original"


def test_validate_paths_rejects_missing_output_directory(
    cli_module,
    valid_paths,
):
    valid_paths["html_output"] = (
        valid_paths["reference"].parent / "nonexistent" / "report.html"
    )

    with pytest.raises(ValueError, match="Diretorio"):
        cli_module.validate_paths(**valid_paths)


def test_validate_paths_rejects_resolved_input_alias(
    cli_module,
    valid_paths,
):
    """Um caminho alternativo nao pode sobrescrever uma entrada."""
    reference = valid_paths["reference"]

    valid_paths["json_output"] = reference.parent / "subdir" / ".." / reference.name

    (reference.parent / "subdir").mkdir()

    with pytest.raises(ValueError, match="coincide"):
        cli_module.validate_paths(**valid_paths)


@pytest.fixture
def cli_args(valid_paths):
    return argparse.Namespace(
        reference=valid_paths["reference"],
        production_raw=valid_paths["production"],
        model=valid_paths["model"],
        json_output=valid_paths["json_output"],
        html_output=valid_paths["html_output"],
        batch_id="cli-operational-test",
        mode="monitor",
    )


@pytest.fixture
def mocked_inputs(cli_module, monkeypatch):
    """Evita carregar CSVs reais nos testes de fluxo."""
    monkeypatch.setattr(
        cli_module.pd,
        "read_csv",
        lambda *args, **kwargs: object(),
    )


def test_cli_rejected_batch_returns_code_2(
    cli_module,
    cli_args,
    mocked_inputs,
    monkeypatch,
):
    result = SimpleNamespace(
        batch_id="cli-operational-test",
        scenario_id="external",
        approved=False,
        inference=SimpleNamespace(
            status="rejected",
            total_rows=8,
            scored_rows=0,
        ),
        drift=None,
        snapshot=None,
    )

    monkeypatch.setattr(
        cli_module,
        "monitor_production_batch",
        lambda *args, **kwargs: result,
    )

    def forbidden_export(*args, **kwargs):
        raise AssertionError("Exportacao nao deveria executar.")

    monkeypatch.setattr(
        cli_module,
        "save_monitoring_json",
        forbidden_export,
    )
    monkeypatch.setattr(
        cli_module,
        "save_monitoring_html",
        forbidden_export,
    )

    exit_code = cli_module.run_cli(cli_args)

    assert exit_code == 2
    assert not cli_args.json_output.exists()
    assert not cli_args.html_output.exists()


def test_cli_approved_batch_creates_both_reports(
    cli_module,
    cli_args,
    mocked_inputs,
    monkeypatch,
):
    result = SimpleNamespace(
        batch_id="cli-operational-test",
        scenario_id="external",
        approved=True,
        inference=SimpleNamespace(
            status="approved",
            total_rows=8,
            scored_rows=8,
        ),
        drift=SimpleNamespace(
            features_analyzed=16,
            features_drifted=2,
            drift_share=0.125,
            drift_detected=True,
        ),
        snapshot=object(),
    )

    monkeypatch.setattr(
        cli_module,
        "monitor_production_batch",
        lambda *args, **kwargs: result,
    )

    def fake_json(result, path):
        path.write_text('{"status":"approved"}', encoding="utf-8")
        return path

    def fake_html(result, path):
        path.write_text("<html>report</html>", encoding="utf-8")
        return path

    monkeypatch.setattr(
        cli_module,
        "save_monitoring_json",
        fake_json,
    )
    monkeypatch.setattr(
        cli_module,
        "save_monitoring_html",
        fake_html,
    )

    exit_code = cli_module.run_cli(cli_args)

    assert exit_code == 0
    assert cli_args.json_output.is_file()
    assert cli_args.html_output.is_file()


def test_cli_rolls_back_json_when_html_fails(
    cli_module,
    cli_args,
    mocked_inputs,
    monkeypatch,
):
    result = SimpleNamespace(
        batch_id="cli-operational-test",
        scenario_id="external",
        approved=True,
        inference=SimpleNamespace(
            status="approved",
            total_rows=8,
            scored_rows=8,
        ),
        drift=SimpleNamespace(
            features_analyzed=16,
            features_drifted=2,
            drift_share=0.125,
            drift_detected=True,
        ),
        snapshot=object(),
    )

    monkeypatch.setattr(
        cli_module,
        "monitor_production_batch",
        lambda *args, **kwargs: result,
    )

    def fake_json(result, path):
        path.write_text("temporary json", encoding="utf-8")
        return path

    def failing_html(result, path):
        raise RuntimeError("Simulated HTML failure.")

    monkeypatch.setattr(
        cli_module,
        "save_monitoring_json",
        fake_json,
    )
    monkeypatch.setattr(
        cli_module,
        "save_monitoring_html",
        failing_html,
    )

    with pytest.raises(RuntimeError, match="Simulated HTML failure"):
        cli_module.run_cli(cli_args)

    assert not cli_args.json_output.exists()
    assert not cli_args.html_output.exists()


def test_cli_main_returns_code_1_on_operational_failure(
    cli_module,
    monkeypatch,
):
    def failing_run_cli(args):
        raise FileNotFoundError("Missing input.")

    monkeypatch.setattr(
        cli_module,
        "run_cli",
        failing_run_cli,
    )

    exit_code = cli_module.main(
        [
            "--reference",
            "reference.csv",
            "--batch-id",
            "test",
            "--json-output",
            "report.json",
            "--html-output",
            "report.html",
            "monitor",
            "--production-raw",
            "production.csv",
        ]
    )

    assert exit_code == 1


def test_cli_rejects_approved_result_without_snapshot(
    cli_module,
    cli_args,
    mocked_inputs,
    monkeypatch,
):
    result = SimpleNamespace(
        batch_id="cli-operational-test",
        scenario_id="external",
        approved=True,
        inference=SimpleNamespace(
            status="approved",
            total_rows=8,
            scored_rows=8,
        ),
        drift=object(),
        snapshot=None,
    )

    monkeypatch.setattr(
        cli_module,
        "monitor_production_batch",
        lambda *args, **kwargs: result,
    )

    with pytest.raises(RuntimeError, match="resultados completos"):
        cli_module.run_cli(cli_args)

    assert not cli_args.json_output.exists()
    assert not cli_args.html_output.exists()


def test_cli_removes_partial_json_when_export_fails(
    cli_module,
    cli_args,
    mocked_inputs,
    monkeypatch,
):
    """Falha de escrita real remove JSON parcial."""
    from credit_risk_monitoring.drift import reporting

    result = SimpleNamespace(
        batch_id="cli-operational-test",
        scenario_id="external",
        approved=True,
        inference=SimpleNamespace(
            status="approved",
            total_rows=8,
            scored_rows=8,
        ),
        drift=SimpleNamespace(
            features_analyzed=16,
            features_drifted=2,
            drift_share=0.125,
            drift_detected=True,
        ),
        snapshot=object(),
    )

    monkeypatch.setattr(
        cli_module,
        "monitor_production_batch",
        lambda *args, **kwargs: result,
    )

    # Isola a serializacao dos detalhes do monitoramento.
    # A funcao save_monitoring_json continua sendo real.
    monkeypatch.setattr(
        reporting,
        "build_monitoring_payload",
        lambda result: {"status": "approved"},
    )

    original_open = Path.open

    class FailingWriter:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            self.handle.__enter__()
            return self

        def __exit__(self, *args):
            return self.handle.__exit__(*args)

        def write(self, content):
            self.handle.write(content[:10])
            raise OSError("Simulated partial JSON write failure.")

    def failing_open(path, *args, **kwargs):
        handle = original_open(path, *args, **kwargs)

        if path == cli_args.json_output and args and args[0] == "x":
            return FailingWriter(handle)

        return handle

    monkeypatch.setattr(Path, "open", failing_open)

    def forbidden_html(*args, **kwargs):
        raise AssertionError("HTML nao pode executar apos falha no JSON.")

    monkeypatch.setattr(
        cli_module,
        "save_monitoring_html",
        forbidden_html,
    )

    with pytest.raises(
        OSError,
        match="Simulated partial JSON write failure",
    ):
        cli_module.run_cli(cli_args)

    assert not cli_args.json_output.exists(), (
        "Arquivo JSON parcial permaneceu apos falha."
    )
    assert not cli_args.html_output.exists()

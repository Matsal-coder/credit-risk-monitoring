"""Testes do ponto de entrada local do exporter."""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "serve_metrics.py"


@pytest.fixture
def cli():
    spec = importlib.util.spec_from_file_location(
        "serve_metrics_test_module",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_requires_database_argument(cli):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args([])

    assert exc.value.code == 2


@pytest.mark.parametrize("port", ["0", "65536", "abc", "-1"])
def test_rejects_invalid_port(cli, port):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["--events-db", "events.sqlite3", "--port", port])

    assert exc.value.code == 2


def test_missing_database_does_not_start_server(cli, tmp_path, monkeypatch):
    server = Mock()
    monkeypatch.setattr(cli.uvicorn, "run", server)

    with pytest.raises(FileNotFoundError):
        cli.main(["--events-db", str(tmp_path / "missing.sqlite3")])

    server.assert_not_called()


def test_server_uses_loopback_and_configured_port(cli, tmp_path, monkeypatch):
    database = tmp_path / "events.sqlite3"
    database.touch()

    app = object()
    server = Mock()

    monkeypatch.setattr(cli, "create_app", lambda path: app)
    monkeypatch.setattr(cli.uvicorn, "run", server)

    assert (
        cli.main(
            [
                "--events-db",
                str(database),
                "--port",
                "8765",
            ]
        )
        == 0
    )

    server.assert_called_once_with(
        app,
        host="127.0.0.1",
        port=8765,
        log_level="info",
        access_log=False,
        reload=False,
        workers=1,
    )


def test_default_host_is_loopback(cli):
    """Execucao local permanece restrita a localhost."""
    args = cli.build_parser().parse_args(["--events-db", "events.sqlite3"])

    assert args.host == "127.0.0.1"


def test_rejects_unapproved_host(cli):
    """Enderecos arbitrarios nao sao aceitos."""
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(
            [
                "--events-db",
                "events.sqlite3",
                "--host",
                "192.168.1.10",
            ]
        )

    assert exc.value.code == 2


def test_docker_host_is_explicit(cli, tmp_path, monkeypatch):
    """Container exige configuracao explicita para todas as interfaces."""
    database = tmp_path / "events.sqlite3"
    database.touch()

    app = object()
    server = Mock()

    monkeypatch.setattr(cli, "create_app", lambda path: app)
    monkeypatch.setattr(cli.uvicorn, "run", server)

    assert (
        cli.main(
            [
                "--events-db",
                str(database),
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ]
        )
        == 0
    )

    server.assert_called_once_with(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=False,
        reload=False,
        workers=1,
    )

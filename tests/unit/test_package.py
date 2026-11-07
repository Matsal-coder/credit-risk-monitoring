"""Testes mínimos de integridade do pacote."""

from importlib import import_module


def test_package_is_importable() -> None:
    """Verifica se o pacote pode ser importado."""
    package = import_module("credit_risk_monitoring")

    assert package.__name__ == "credit_risk_monitoring"

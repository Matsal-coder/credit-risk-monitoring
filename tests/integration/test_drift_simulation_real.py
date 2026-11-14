"""Integracao da simulacao com particoes reais do Home Credit."""

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from credit_risk_monitoring.drift.simulation import (
    reconstruct_raw_batch,
    simulate_production_batch,
)
from credit_risk_monitoring.quality.validation import validate_batch

REFERENCE_PATH = Path("data/processed/reference.csv")
TEST_PATH = Path("data/processed/test.csv")


def file_hash(path: Path) -> str:
    """Calcula SHA-256 sem alterar o arquivo."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


@pytest.fixture(scope="module")
def real_partitions():
    """Carrega particoes locais preservando hashes originais."""
    if not REFERENCE_PATH.is_file() or not TEST_PATH.is_file():
        pytest.skip("Particoes reais nao disponiveis localmente.")

    hashes_before = {
        "reference": file_hash(REFERENCE_PATH),
        "test": file_hash(TEST_PATH),
    }

    reference = pd.read_csv(REFERENCE_PATH)
    production = pd.read_csv(TEST_PATH)

    yield reference, production

    assert file_hash(REFERENCE_PATH) == hashes_before["reference"]
    assert file_hash(TEST_PATH) == hashes_before["test"]


def test_reference_and_production_are_disjoint(
    real_partitions,
) -> None:
    reference, production = real_partitions

    assert len(reference) == 30751
    assert len(production) == 46127

    reference_ids = set(reference["SK_ID_CURR"])
    production_ids = set(production["SK_ID_CURR"])

    assert len(reference_ids) == len(reference)
    assert len(production_ids) == len(production)
    assert reference_ids.isdisjoint(production_ids)


@pytest.mark.parametrize(
    ("scenario", "expected_changed"),
    [
        ("control", 0),
        ("moderate", 23063),
        ("strong", 46127),
    ],
)
def test_real_production_simulation(
    real_partitions,
    scenario: str,
    expected_changed: int,
) -> None:
    _, production = real_partitions

    original = reconstruct_raw_batch(production)

    result = simulate_production_batch(
        production,
        scenario,
        seed=642,
    )

    simulated = result.raw_batch

    assert result.total_rows == 46127
    assert result.changed_rows == expected_changed

    assert "TARGET" not in simulated.columns
    assert "DAYS_EMPLOYED_SENTINEL" not in simulated.columns

    validation = validate_batch(
        simulated,
        stage="raw_inference",
        batch_id=f"integration-{scenario}",
    )

    assert validation.approved

    changed_credit = simulated["AMT_CREDIT"].ne(original["AMT_CREDIT"])

    changed_income = simulated["AMT_INCOME_TOTAL"].ne(original["AMT_INCOME_TOTAL"])

    pd.testing.assert_series_equal(
        changed_credit,
        changed_income,
        check_names=False,
    )

    assert int(changed_credit.sum()) == expected_changed

    unchanged_columns = [
        column
        for column in original.columns
        if column
        not in (
            "AMT_CREDIT",
            "AMT_INCOME_TOTAL",
        )
    ]

    pd.testing.assert_frame_equal(
        simulated[unchanged_columns],
        original[unchanged_columns],
    )


def test_real_simulation_is_reproducible(
    real_partitions,
) -> None:
    _, production = real_partitions

    first = simulate_production_batch(
        production,
        "moderate",
        seed=642,
    )

    second = simulate_production_batch(
        production,
        "moderate",
        seed=642,
    )

    pd.testing.assert_frame_equal(
        first.raw_batch,
        second.raw_batch,
    )

    assert first.to_dict() == second.to_dict()

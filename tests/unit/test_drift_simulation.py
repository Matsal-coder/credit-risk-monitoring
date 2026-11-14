"""Testes unitarios do simulador de producao."""

import pandas as pd
import pytest

from credit_risk_monitoring.drift.simulation import (
    reconstruct_raw_batch,
    simulate_production_batch,
)
from credit_risk_monitoring.quality.validation import (
    validate_batch,
)


@pytest.fixture
def prepared_sample() -> pd.DataFrame:
    """Amostra sintetica compativel com o contrato."""
    return pd.DataFrame(
        {
            "SK_ID_CURR": [100001, 100002],
            "AMT_CREDIT": [150000.0, 250000.0],
            "AMT_INCOME_TOTAL": [90000.0, 120000.0],
            "AMT_ANNUITY": [12000.0, 18000.0],
            "AMT_GOODS_PRICE": [140000.0, 230000.0],
            "EXT_SOURCE_2": [0.45, 0.65],
            "EXT_SOURCE_3": [0.35, 0.55],
            "DAYS_BIRTH": [-12000, -16000],
            "DAYS_EMPLOYED": [float("nan"), -2000.0],
            "DAYS_REGISTRATION": [-3000.0, -4500.0],
            "CNT_CHILDREN": [0, 1],
            "CNT_FAM_MEMBERS": [2.0, 3.0],
            "NAME_INCOME_TYPE": ["Working", "Pensioner"],
            "NAME_EDUCATION_TYPE": [
                "Higher education",
                "Secondary / secondary special",
            ],
            "FLAG_OWN_CAR": ["Y", "N"],
            "FLAG_OWN_REALTY": ["Y", "Y"],
            "NAME_CONTRACT_TYPE": [
                "Cash loans",
                "Cash loans",
            ],
            "DAYS_EMPLOYED_SENTINEL": [1, 0],
        }
    )


def test_reconstruction_restores_sentinel(
    prepared_sample: pd.DataFrame,
) -> None:
    raw = reconstruct_raw_batch(prepared_sample)

    assert raw.loc[0, "DAYS_EMPLOYED"] == 365243.0
    assert raw.loc[1, "DAYS_EMPLOYED"] == -2000.0
    assert "DAYS_EMPLOYED_SENTINEL" not in raw.columns


def test_reconstruction_removes_target(
    prepared_sample: pd.DataFrame,
) -> None:
    prepared_sample["TARGET"] = [0, 1]

    raw = reconstruct_raw_batch(prepared_sample)

    assert "TARGET" not in raw.columns
    assert len(raw) == 2


def test_reconstruction_preserves_original(
    prepared_sample: pd.DataFrame,
) -> None:
    original = prepared_sample.copy(deep=True)

    reconstruct_raw_batch(prepared_sample)

    pd.testing.assert_frame_equal(prepared_sample, original)


def test_reconstruction_produces_valid_raw_batch(
    prepared_sample: pd.DataFrame,
) -> None:
    raw = reconstruct_raw_batch(prepared_sample)

    result = validate_batch(
        raw,
        stage="raw_inference",
        batch_id="synthetic-reconstruction",
    )

    assert result.approved


def test_reconstruction_rejects_missing_column(
    prepared_sample: pd.DataFrame,
) -> None:
    invalid = prepared_sample.drop(columns=["AMT_CREDIT"])

    with pytest.raises(ValueError):
        reconstruct_raw_batch(invalid)


def test_reconstruction_rejects_invalid_indicator(
    prepared_sample: pd.DataFrame,
) -> None:
    invalid = prepared_sample.copy()
    invalid["DAYS_EMPLOYED_SENTINEL"] = [2, 0]

    with pytest.raises(ValueError):
        reconstruct_raw_batch(invalid)


def test_reconstruction_rejects_inconsistent_sentinel(
    prepared_sample: pd.DataFrame,
) -> None:
    invalid = prepared_sample.copy()
    invalid.loc[0, "DAYS_EMPLOYED"] = -100.0

    with pytest.raises(ValueError):
        reconstruct_raw_batch(invalid)


def test_control_preserves_values(
    prepared_sample: pd.DataFrame,
) -> None:
    result = simulate_production_batch(
        prepared_sample,
        "control",
    )

    expected = reconstruct_raw_batch(prepared_sample)

    pd.testing.assert_frame_equal(result.raw_batch, expected)

    assert result.changed_rows == 0
    assert result.total_rows == 2


def test_moderate_changes_selected_rows(
    prepared_sample: pd.DataFrame,
) -> None:
    result = simulate_production_batch(
        prepared_sample,
        "moderate",
        seed=642,
    )

    original = reconstruct_raw_batch(prepared_sample)
    simulated = result.raw_batch

    changed = simulated["AMT_CREDIT"].ne(original["AMT_CREDIT"])

    assert changed.sum() == 1
    assert result.changed_rows == 1

    pd.testing.assert_series_equal(
        changed,
        simulated["AMT_INCOME_TOTAL"].ne(original["AMT_INCOME_TOTAL"]),
        check_names=False,
    )

    assert (
        simulated.loc[changed, "AMT_CREDIT"].to_numpy()
        == original.loc[changed, "AMT_CREDIT"].to_numpy() * 1.10
    ).all()

    assert (
        simulated.loc[changed, "AMT_INCOME_TOTAL"].to_numpy()
        == original.loc[changed, "AMT_INCOME_TOTAL"].to_numpy() * 0.90
    ).all()


def test_strong_changes_all_rows(
    prepared_sample: pd.DataFrame,
) -> None:
    result = simulate_production_batch(
        prepared_sample,
        "strong",
    )

    original = reconstruct_raw_batch(prepared_sample)

    assert result.changed_rows == 2

    pd.testing.assert_series_equal(
        result.raw_batch["AMT_CREDIT"],
        original["AMT_CREDIT"] * 1.25,
        check_names=True,
    )

    pd.testing.assert_series_equal(
        result.raw_batch["AMT_INCOME_TOTAL"],
        original["AMT_INCOME_TOTAL"] * 0.80,
        check_names=True,
    )


@pytest.mark.parametrize(
    "scenario_id",
    ["control", "moderate", "strong"],
)
def test_simulated_batches_pass_quality_contract(
    prepared_sample: pd.DataFrame,
    scenario_id: str,
) -> None:
    result = simulate_production_batch(
        prepared_sample,
        scenario_id,
    )

    validation = validate_batch(
        result.raw_batch,
        stage="raw_inference",
        batch_id=f"test-{scenario_id}",
    )

    assert validation.approved


def test_simulation_is_deterministic(
    prepared_sample: pd.DataFrame,
) -> None:
    first = simulate_production_batch(
        prepared_sample,
        "moderate",
        seed=642,
    )

    second = simulate_production_batch(
        prepared_sample,
        "moderate",
        seed=642,
    )

    pd.testing.assert_frame_equal(
        first.raw_batch,
        second.raw_batch,
    )

    assert first.to_dict() == second.to_dict()


def test_simulation_preserves_input(
    prepared_sample: pd.DataFrame,
) -> None:
    original = prepared_sample.copy(deep=True)

    simulate_production_batch(
        prepared_sample,
        "strong",
    )

    pd.testing.assert_frame_equal(
        prepared_sample,
        original,
    )


def test_simulation_rejects_unknown_scenario(
    prepared_sample: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="desconhecido"):
        simulate_production_batch(
            prepared_sample,
            "unknown",
        )


def test_simulation_rejects_invalid_seed(
    prepared_sample: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="Seed"):
        simulate_production_batch(
            prepared_sample,
            "moderate",
            seed=-1,
        )


def test_simulation_metadata_has_no_individual_data(
    prepared_sample: pd.DataFrame,
) -> None:
    result = simulate_production_batch(
        prepared_sample,
        "moderate",
    )

    metadata = result.to_dict()

    assert "raw_batch" not in metadata
    assert "SK_ID_CURR" not in metadata
    assert "TARGET" not in metadata
    assert metadata["scenario_id"] == "moderate"
    assert metadata["changed_rows"] == 1


def test_moderate_rejects_insufficient_eligible_rows(
    prepared_sample: pd.DataFrame,
) -> None:
    """Nao contabiliza como alterada uma linha sem renda."""
    invalid = prepared_sample.copy()
    invalid["AMT_INCOME_TOTAL"] = [
        float("nan"),
        float("nan"),
    ]

    with pytest.raises(
        ValueError,
        match="Registros elegiveis insuficientes",
    ):
        simulate_production_batch(
            invalid,
            "moderate",
            seed=642,
        )


def test_simulation_rejects_nonfinite_transformation(
    prepared_sample: pd.DataFrame,
) -> None:
    """Transformacoes nao podem produzir infinito."""
    invalid = prepared_sample.copy()

    # Valor finito de entrada que ultrapassa float64
    # quando multiplicado por 1.25.
    invalid["AMT_CREDIT"] = [1.7e308, 1.7e308]

    with pytest.raises(
        ValueError,
        match="Valores invalidos apos transformacao",
    ):
        simulate_production_batch(
            invalid,
            "strong",
            seed=642,
        )

"""Testes da analise diagnostica agregada de fairness."""

import json

import numpy as np
import pandas as pd
import pytest

from credit_risk_monitoring.data.preparation import MODEL_FEATURES
from scripts.analyze_fairness import (
    aggregate_metrics,
    build_age_groups,
    build_fairness_report,
    confusion_counts,
    evaluate_groups,
    safe_rate,
    save_report,
)


def test_safe_rate_handles_zero_and_insufficient_support():
    assert safe_rate(2, 4) == 0.5
    assert safe_rate(0, 4) == 0.0
    assert safe_rate(0, 0) is None
    assert safe_rate(2, 10, minimum=20) is None


def test_confusion_counts_and_rates():
    y_true = np.array([0, 0, 0, 1, 1, 1])
    y_pred = np.array([0, 1, 0, 1, 0, 1])

    counts = confusion_counts(y_true, y_pred)

    assert counts == {"tn": 2, "fp": 1, "fn": 1, "tp": 2}

    metrics = aggregate_metrics(
        y_true,
        y_pred,
        min_denominator=1,
    )

    assert metrics["n"] == 6
    assert metrics["actual_positive"] == 3
    assert metrics["actual_negative"] == 3
    assert metrics["predicted_positive"] == 3
    assert metrics["prevalence"] == pytest.approx(0.5)
    assert metrics["predicted_positive_rate"] == pytest.approx(0.5)
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall_tpr"] == pytest.approx(2 / 3)
    assert metrics["fpr"] == pytest.approx(1 / 3)


def test_conditional_rates_are_null_when_support_is_insufficient():
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 1, 1, 0])

    metrics = aggregate_metrics(
        y_true,
        y_pred,
        min_denominator=3,
    )

    assert metrics["prevalence"] == 0.5
    assert metrics["predicted_positive_rate"] == 0.5
    assert metrics["precision"] is None
    assert metrics["recall_tpr"] is None
    assert metrics["fpr"] is None


def test_age_group_boundaries_and_missing_values():
    ages = pd.Series(
        [
            -29 * 365.25,
            -30 * 365.25,
            -44 * 365.25,
            -45 * 365.25,
            -59 * 365.25,
            -60 * 365.25,
            None,
            100,
        ]
    )

    groups = build_age_groups(ages).tolist()

    assert groups == [
        "under_30",
        "30_to_44",
        "30_to_44",
        "45_to_59",
        "45_to_59",
        "60_plus",
        "MISSING",
        "MISSING",
    ]


def test_small_groups_are_suppressed():
    labels = pd.Series(["A", "A", "B", "B", "B"])
    y_true = np.array([0, 1, 0, 1, 0])
    y_pred = np.array([0, 1, 1, 1, 0])

    groups = evaluate_groups(
        labels,
        y_true,
        y_pred,
        min_group_size=3,
        min_denominator=1,
    )

    assert len(groups) == 2

    assert groups[0] == {
        "group": "B",
        "n": 3,
        "status": "complementary_suppression",
        "metrics": None,
    }

    assert groups[1] == {
        "group": "SUPPRESSED_GROUPS",
        "n": 2,
        "status": "small_groups_combined",
        "metrics": None,
    }


def test_group_evaluation_rejects_incompatible_dimensions():
    with pytest.raises(ValueError, match="Dimensoes inconsistentes"):
        evaluate_groups(
            pd.Series(["A", "B"]),
            np.array([0]),
            np.array([0]),
        )


def make_synthetic_test_data():
    """Cria entradas artificiais sem utilizar registros reais."""
    n = 120

    test = pd.DataFrame(
        {feature: np.zeros(n, dtype=float) for feature in MODEL_FEATURES}
    )

    test["SK_ID_CURR"] = np.arange(100000, 100000 + n)
    test["TARGET"] = np.tile([0, 1], n // 2)
    test["DAYS_BIRTH"] = np.full(n, -40 * 365.25)
    test["NAME_EDUCATION_TYPE"] = ["Higher education"] * n
    test["NAME_INCOME_TYPE"] = ["Working"] * n

    probabilities = np.tile([0.1, 0.9], n // 2)

    return test, probabilities


def test_report_is_aggregated_without_individual_data():
    test, probabilities = make_synthetic_test_data()

    report = build_fairness_report(
        test,
        probabilities,
        threshold=0.5,
    )

    assert report["dataset"] == "test"
    assert report["overall"]["n"] == 120
    assert report["overall"]["confusion_matrix"] == {
        "tn": 60,
        "fp": 0,
        "fn": 0,
        "tp": 60,
    }

    assert set(report["groups"]) == {
        "age_group",
        "education",
        "income_type",
    }

    serialized = json.dumps(report)

    assert "SK_ID_CURR" not in serialized
    assert "probabilities" not in serialized
    assert "row_index" not in serialized
    assert "100000" not in serialized


@pytest.mark.parametrize(
    "probabilities,threshold",
    [
        (np.array([0.5]), 0.5),
        (np.full(120, np.nan), 0.5),
        (np.full(120, 1.5), 0.5),
        (np.full(120, 0.5), -0.1),
        (np.full(120, 0.5), 1.1),
    ],
)
def test_report_rejects_invalid_scores_or_threshold(
    probabilities,
    threshold,
):
    test, _ = make_synthetic_test_data()

    with pytest.raises(ValueError):
        build_fairness_report(
            test,
            probabilities,
            threshold=threshold,
        )


def test_save_report_restricts_output_and_prevents_overwrite(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()

    payload = {
        "analysis": "diagnostic_group_fairness",
        "overall": {"n": 120},
    }

    destination = artifacts / "fairness.json"

    result = save_report(payload, destination)

    assert result == destination
    assert json.loads(destination.read_text(encoding="utf-8")) == payload

    with pytest.raises(FileExistsError):
        save_report(payload, destination)

    with pytest.raises(ValueError, match="artifacts"):
        save_report(payload, tmp_path / "outside.json")


def test_multiple_small_groups_are_combined_without_names():
    labels = pd.Series(["Rare A", "Rare B", "Common", "Common", "Common"])
    y_true = np.array([0, 1, 0, 1, 0])
    y_pred = np.array([0, 1, 0, 1, 0])

    groups = evaluate_groups(
        labels,
        y_true,
        y_pred,
        min_group_size=3,
        min_denominator=1,
    )

    assert sum(group["n"] for group in groups) == 5
    assert len(groups) == 2

    assert groups[0] == {
        "group": "Common",
        "n": 3,
        "status": "complementary_suppression",
        "metrics": None,
    }

    assert groups[1] == {
        "group": "SUPPRESSED_GROUPS",
        "n": 2,
        "status": "small_groups_combined",
        "metrics": None,
    }

    assert all(group["group"] not in {"Rare A", "Rare B"} for group in groups)


def test_suppressed_confusion_matrix_is_not_reconstructable():
    """A matriz suprimida nao deve ser obtida por simples subtracao."""
    labels = pd.Series(["Common A"] * 110 + ["Common B"] * 110 + ["Rare"] * 10)

    y_true = np.tile([0, 1], 115)
    y_pred = np.roll(y_true, 1)

    groups = evaluate_groups(
        labels,
        y_true,
        y_pred,
        min_group_size=100,
        min_denominator=1,
    )

    overall = confusion_counts(y_true, y_pred)

    visible = [group for group in groups if group["metrics"] is not None]

    residual = {
        key: overall[key]
        - sum(group["metrics"]["confusion_matrix"][key] for group in visible)
        for key in ("tn", "fp", "fn", "tp")
    }

    rare_mask = labels.eq("Rare").to_numpy()
    rare_counts = confusion_counts(
        y_true[rare_mask],
        y_pred[rare_mask],
    )

    assert residual != rare_counts


def test_no_complementary_suppression_without_small_groups():
    """Dimensoes sem grupos raros preservam as metricas."""
    labels = pd.Series(["A"] * 120 + ["B"] * 130)

    y_true = np.tile([0, 1], 125)
    y_pred = y_true.copy()

    groups = evaluate_groups(
        labels,
        y_true,
        y_pred,
        min_group_size=100,
    )

    assert len(groups) == 2
    assert all(group["status"] == "evaluated" for group in groups)
    assert all(group["metrics"] is not None for group in groups)

    assert sum(group["n"] for group in groups) == len(labels)


def test_complementary_suppression_selects_largest_group():
    """O maior grupo e escolhido como supressao complementar."""
    labels = pd.Series(["A"] * 120 + ["B"] * 180 + ["C"] * 150 + ["Rare"] * 10)

    y_true = np.tile([0, 1], 230)
    y_pred = y_true.copy()

    groups = evaluate_groups(
        labels,
        y_true,
        y_pred,
        min_group_size=100,
    )

    by_name = {group["group"]: group for group in groups}

    assert by_name["B"]["status"] == "complementary_suppression"
    assert by_name["B"]["metrics"] is None
    assert by_name["B"]["n"] == 180

    assert by_name["A"]["status"] == "evaluated"
    assert by_name["C"]["status"] == "evaluated"

    assert by_name["SUPPRESSED_GROUPS"]["n"] == 10
    assert by_name["SUPPRESSED_GROUPS"]["metrics"] is None

    assert "Rare" not in by_name


def test_complementary_suppression_tiebreak_is_deterministic():
    """Empate entre maiores grupos e resolvido pelo nome."""
    labels = pd.Series(["B"] * 110 + ["A"] * 110 + ["Rare"] * 10)

    y_true = np.tile([0, 1], 115)
    y_pred = y_true.copy()

    groups = evaluate_groups(
        labels,
        y_true,
        y_pred,
        min_group_size=100,
    )

    by_name = {group["group"]: group for group in groups}

    assert by_name["A"]["status"] == "complementary_suppression"
    assert by_name["B"]["status"] == "evaluated"


def test_all_small_groups_have_no_published_metrics():
    """Sem grupo elegivel, nenhuma matriz por grupo e publicada."""
    labels = pd.Series(["Rare A"] * 10 + ["Rare B"] * 15)

    y_true = np.array([0, 1] * 12 + [0])
    y_pred = y_true.copy()

    groups = evaluate_groups(
        labels,
        y_true,
        y_pred,
        min_group_size=100,
    )

    assert groups == [
        {
            "group": "SUPPRESSED_GROUPS",
            "n": 25,
            "status": "small_groups_combined",
            "metrics": None,
        }
    ]


def test_public_report_prevents_direct_suppressed_matrix_recovery():
    """Relatorio completo nao isola a matriz rara por subtracao."""
    test, probabilities = make_synthetic_test_data()

    # Mantem 120 registros e introduz uma categoria rara
    # em escolaridade e tipo de renda.
    test["NAME_EDUCATION_TYPE"] = ["Higher education"] * 110 + ["Rare education"] * 10
    test["NAME_INCOME_TYPE"] = ["Working"] * 112 + ["Rare income"] * 8

    report = build_fairness_report(
        test,
        probabilities,
        threshold=0.5,
    )

    overall = report["overall"]["confusion_matrix"]

    for dimension in ("education", "income_type"):
        groups = report["groups"][dimension]

        visible = [group for group in groups if group["metrics"] is not None]

        assert visible == []

        complementary = [
            group for group in groups if group["status"] == "complementary_suppression"
        ]

        suppressed = [
            group for group in groups if group["status"] == "small_groups_combined"
        ]

        assert len(complementary) == 1
        assert len(suppressed) == 1

        assert complementary[0]["metrics"] is None
        assert suppressed[0]["metrics"] is None

        # A matriz global permanece disponivel, mas nenhum
        # detalhamento dessa dimensao permite isolar o grupo raro.
        assert sum(overall.values()) == 120

        assert complementary[0]["n"] + suppressed[0]["n"] == report["overall"]["n"]

    # A dimensao etaria nao contem grupo raro e preserva
    # sua avaliacao convencional.
    assert all(
        group["status"] == "evaluated" for group in report["groups"]["age_group"]
    )

    serialized = json.dumps(report)

    assert "Rare education" not in serialized
    assert "Rare income" not in serialized
    assert "SK_ID_CURR" not in serialized

"""Contratos do dashboard Grafana versionado."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = ROOT / "infra/grafana/dashboards/operations-overview.json"

DATASOURCE_UID = "credit-risk-prometheus"
DASHBOARD_UID = "credit-risk-operations"

EXPECTED_PANEL_IDS = set(range(1, 9))

EXPECTED_EXPRESSIONS = {
    1: "sum(credit_risk_executions_count)",
    2: ('sum(credit_risk_executions_count{execution_status="failed"})'),
    3: "sum(credit_risk_quality_violations_count)",
    4: "sum(credit_risk_drift_detected_count)",
    5: ("sum by (pipeline, execution_status) (credit_risk_executions_count)"),
    6: (
        "sum by (pipeline) "
        "(credit_risk_execution_duration_seconds_sum) / "
        "sum by (pipeline) "
        "(credit_risk_execution_duration_seconds_count)"
    ),
    7: "credit_risk_running_executions",
    8: 'up{job="credit-risk-exporter"}',
}


@pytest.fixture(scope="module")
def dashboard():
    return json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))


def test_dashboard_has_stable_identity(dashboard):
    assert dashboard["uid"] == DASHBOARD_UID
    assert dashboard["title"]
    assert dashboard["refresh"] == "15s"


def test_dashboard_has_eight_unique_panels(dashboard):
    ids = [panel["id"] for panel in dashboard["panels"]]

    assert len(ids) == 8
    assert set(ids) == EXPECTED_PANEL_IDS


def test_all_panels_use_provisioned_datasource(dashboard):
    for panel in dashboard["panels"]:
        assert panel["datasource"]["uid"] == DATASOURCE_UID

        for target in panel["targets"]:
            assert target["datasource"]["uid"] == DATASOURCE_UID


@pytest.mark.parametrize(
    ("panel_id", "expected_expression"),
    sorted(EXPECTED_EXPRESSIONS.items()),
)
def test_panel_promql_contract(
    dashboard,
    panel_id,
    expected_expression,
):
    panel = next(item for item in dashboard["panels"] if item["id"] == panel_id)

    assert panel["targets"][0]["expr"] == expected_expression


def test_stat_panels_use_instant_queries(dashboard):
    for panel in dashboard["panels"]:
        if panel["id"] in {1, 2, 3, 4}:
            assert panel["type"] == "stat"
            assert panel["targets"][0]["instant"] is True


def test_dashboard_contains_no_embedded_credentials(dashboard):
    contents = json.dumps(dashboard).lower()

    assert "password" not in contents
    assert "api_key" not in contents
    assert "sk_id_curr" not in contents

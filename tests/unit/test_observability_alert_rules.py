"""Contratos de configuracao dos alertas operacionais Prometheus."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PROMETHEUS_DIR = ROOT / "infra" / "prometheus"
RULES_PATH = PROMETHEUS_DIR / "alert_rules.yml"
RULE_TESTS_PATH = PROMETHEUS_DIR / "alert_rules.test.yml"
CONFIG_PATH = PROMETHEUS_DIR / "prometheus.yml"
COMPOSE_PATH = ROOT / "compose.yaml"

EXPECTED_ALERTS = {
    "CreditRiskDriftDetected": {
        "metric": "credit_risk_drift_detected_count",
        "severity": "warning",
        "category": "drift",
    },
    "CreditRiskOperationalFailure": {
        "metric": "credit_risk_executions_count",
        "severity": "critical",
        "category": "operational",
    },
    "CreditRiskQualityViolation": {
        "metric": "credit_risk_quality_violations_count",
        "severity": "warning",
        "category": "quality",
    },
}


@pytest.fixture(scope="module")
def rules():
    return yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def prometheus_config():
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def compose_config():
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rule_tests():
    return yaml.safe_load(RULE_TESTS_PATH.read_text(encoding="utf-8"))


def test_alert_rules_have_expected_group(rules):
    groups = rules["groups"]

    assert len(groups) == 1
    assert groups[0]["name"] == "credit-risk-operational-alerts"
    assert groups[0]["interval"] == "15s"


def test_exactly_three_alerts_are_configured(rules):
    configured = [rule["alert"] for group in rules["groups"] for rule in group["rules"]]

    assert len(configured) == 3
    assert set(configured) == set(EXPECTED_ALERTS)


@pytest.mark.parametrize(
    "alert_name",
    sorted(EXPECTED_ALERTS),
)
def test_alert_contract(rules, alert_name):
    alert = next(
        item
        for group in rules["groups"]
        for item in group["rules"]
        if item["alert"] == alert_name
    )

    expected = EXPECTED_ALERTS[alert_name]
    expression = alert["expr"].strip()

    assert expected["metric"] in expression
    assert "delta(" in expression
    assert "[3m]" in expression
    assert expression.endswith("> 0")

    assert alert["labels"]["severity"] == expected["severity"]
    assert alert["labels"]["category"] == expected["category"]

    assert alert.get("for", "0m") in ("0m", "0s")
    assert alert.get("keep_firing_for", "0m") in ("0m", "0s")

    assert alert["annotations"]["summary"]
    assert alert["annotations"]["description"]


def test_alerts_do_not_use_counter_functions(rules):
    for group in rules["groups"]:
        for rule in group["rules"]:
            expression = rule["expr"].lower()

            assert "rate(" not in expression
            assert "increase(" not in expression
            assert "irate(" not in expression


def test_alerts_do_not_expose_sensitive_labels(rules):
    forbidden = {
        "batch_id",
        "execution_id",
        "sk_id_curr",
        "customer_id",
        "error_message",
        "file_path",
    }

    for group in rules["groups"]:
        for rule in group["rules"]:
            labels = set(rule["labels"])
            assert not forbidden.intersection(labels)


def test_prometheus_loads_versioned_rules(prometheus_config):
    assert "/etc/prometheus/alert_rules.yml" in prometheus_config["rule_files"]

    assert prometheus_config["global"]["scrape_interval"] == "15s"
    assert prometheus_config["global"]["evaluation_interval"] == "15s"


def test_compose_mounts_alert_rules_read_only(compose_config):
    prometheus = compose_config["services"]["prometheus"]
    volumes = prometheus["volumes"]

    matching = [
        volume
        for volume in volumes
        if isinstance(volume, dict)
        and volume.get("target") == "/etc/prometheus/alert_rules.yml"
    ]

    assert len(matching) == 1
    assert matching[0]["source"] == "./infra/prometheus/alert_rules.yml"
    assert matching[0]["read_only"] is True


def test_prometheus_uses_pinned_image(compose_config):
    assert (
        compose_config["services"]["prometheus"]["image"] == "prom/prometheus:v3.16.0"
    )


def test_rule_tests_reference_real_rules(rule_tests):
    assert "alert_rules.yml" in rule_tests["rule_files"]
    assert rule_tests["evaluation_interval"] == "15s"


def test_all_alerts_have_temporal_tests(rule_tests):
    tested = {
        item["alertname"]
        for scenario in rule_tests["tests"]
        for item in scenario["alert_rule_test"]
    }

    assert tested == set(EXPECTED_ALERTS)


@pytest.mark.parametrize(
    "alert_name",
    sorted(EXPECTED_ALERTS),
)
def test_each_alert_has_firing_and_inactive_cases(
    rule_tests,
    alert_name,
):
    evaluations = [
        evaluation
        for scenario in rule_tests["tests"]
        for evaluation in scenario["alert_rule_test"]
        if evaluation["alertname"] == alert_name
    ]

    assert any(item["exp_alerts"] for item in evaluations)
    assert any(item["exp_alerts"] == [] for item in evaluations)

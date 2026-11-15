"""Testes dos adaptadores de resultados operacionais."""

from datetime import timedelta

import pytest

from credit_risk_monitoring.drift.monitoring import MonitoringResult
from credit_risk_monitoring.drift.results import DriftSummary
from credit_risk_monitoring.modeling.inference import InferenceResult
from credit_risk_monitoring.observability.adapters import (
    build_failure_event,
    build_monitoring_event,
    build_scoring_event,
)
from credit_risk_monitoring.observability.events import start_event
from credit_risk_monitoring.quality.results import (
    QualityViolation,
    ValidationResult,
)


def make_inference(
    *,
    batch_id="batch-a",
    approved=True,
):
    violations = (
        ()
        if approved
        else (
            QualityViolation(
                column="AMT_CREDIT",
                rule="positive_credit",
                count=3,
            ),
        )
    )

    validation = ValidationResult(
        batch_id=batch_id,
        stage="raw_inference",
        status="approved" if approved else "rejected",
        total_rows=10,
        violations=violations,
    )

    return InferenceResult(
        batch_id=batch_id,
        status="approved" if approved else "rejected",
        total_rows=10,
        validations=(validation,),
        threshold=0.14 if approved else None,
        probabilities=(0.2,) * 10 if approved else (),
        predictions=(1,) * 10 if approved else (),
    )


def make_monitoring(
    *,
    approved=True,
    drifted=False,
    batch_id="batch-a",
    scenario_id="control",
):
    drift = None

    if approved:
        drift = DriftSummary(
            batch_id=batch_id,
            scenario_id=scenario_id,
            reference_rows=20,
            production_rows=10,
            features_analyzed=16,
            features_drifted=2 if drifted else 0,
            drift_share=0.125 if drifted else 0.0,
            drift_detected=drifted,
            feature_results=(),
        )

    return MonitoringResult(
        batch_id=batch_id,
        scenario_id=scenario_id,
        inference=make_inference(
            batch_id=batch_id,
            approved=approved,
        ),
        drift=drift,
    )


def end_values(initial):
    return {
        "finished_at": initial.started_at + timedelta(seconds=2),
        "duration_seconds": 2.0,
    }


def test_scoring_approved():
    initial = start_event("batch-a", "scoring", "not_applicable")

    event = build_scoring_event(
        initial,
        make_inference(),
        **end_values(initial),
    )

    assert event.execution_status == "completed"
    assert event.exit_code == 0
    assert event.scored_rows == 10
    assert event.drift_status == "not_evaluated"


def test_scoring_rejected():
    initial = start_event("batch-a", "scoring", "not_applicable")

    event = build_scoring_event(
        initial,
        make_inference(approved=False),
        **end_values(initial),
    )

    assert event.exit_code == 2
    assert event.scored_rows == 0
    assert event.quality_violations == 3


def test_monitoring_control():
    initial = start_event("batch-a", "monitoring", "control")

    event = build_monitoring_event(
        initial,
        make_monitoring(),
        **end_values(initial),
    )

    assert event.exit_code == 0
    assert event.drift_status == "not_detected"
    assert event.features_drifted == 0


def test_monitoring_strong_drift():
    initial = start_event("batch-a", "monitoring", "strong")

    event = build_monitoring_event(
        initial,
        make_monitoring(
            drifted=True,
            scenario_id="strong",
        ),
        **end_values(initial),
    )

    assert event.exit_code == 0
    assert event.drift_status == "detected"
    assert event.features_drifted == 2
    assert event.drift_share == 0.125


def test_monitoring_quality_rejection():
    initial = start_event("batch-a", "monitoring", "external")

    event = build_monitoring_event(
        initial,
        make_monitoring(
            approved=False,
            scenario_id="external",
        ),
        **end_values(initial),
    )

    assert event.exit_code == 2
    assert event.scored_rows == 0
    assert event.quality_violations == 3
    assert event.drift_status == "not_evaluated"


def test_failure_before_pipeline_result():
    initial = start_event("batch-a", "monitoring", "external")

    event = build_failure_event(
        initial,
        FileNotFoundError("/private/customer.csv"),
        **end_values(initial),
    )

    assert event.exit_code == 1
    assert event.quality_status == "not_evaluated"
    assert event.error_type == "FileNotFoundError"
    assert "/private/" not in str(event.to_dict())


def test_failure_after_monitoring_result():
    initial = start_event("batch-a", "monitoring", "strong")

    event = build_failure_event(
        initial,
        OSError("Falha no relatorio HTML"),
        partial_result=make_monitoring(
            drifted=True,
            scenario_id="strong",
        ),
        **end_values(initial),
    )

    assert event.execution_status == "failed"
    assert event.exit_code == 1
    assert event.quality_status == "approved"
    assert event.drift_status == "detected"
    assert event.scored_rows == 10
    assert event.error_type == "OSError"


def test_failure_after_scoring_result():
    initial = start_event("batch-a", "scoring", "not_applicable")

    event = build_failure_event(
        initial,
        OSError("Falha na exportacao"),
        partial_result=make_inference(),
        **end_values(initial),
    )

    assert event.execution_status == "failed"
    assert event.scored_rows == 10
    assert event.drift_status == "not_evaluated"


def test_mismatched_batch_is_rejected():
    initial = start_event("batch-a", "monitoring", "control")

    with pytest.raises(ValueError, match="batch_id"):
        build_monitoring_event(
            initial,
            make_monitoring(batch_id="batch-b"),
            **end_values(initial),
        )


def test_mismatched_scenario_is_rejected():
    initial = start_event("batch-a", "monitoring", "control")

    with pytest.raises(ValueError, match="scenario_id"):
        build_monitoring_event(
            initial,
            make_monitoring(scenario_id="strong"),
            **end_values(initial),
        )


def test_mismatched_pipeline_is_rejected():
    initial = start_event("batch-a", "scoring", "not_applicable")

    with pytest.raises(ValueError, match="Pipeline"):
        build_monitoring_event(
            initial,
            make_monitoring(),
            **end_values(initial),
        )


def test_approved_monitoring_requires_drift():
    initial = start_event("batch-a", "monitoring", "control")

    result = MonitoringResult(
        batch_id="batch-a",
        scenario_id="control",
        inference=make_inference(),
        drift=None,
    )

    with pytest.raises(ValueError, match="sem resultado de drift"):
        build_monitoring_event(
            initial,
            result,
            **end_values(initial),
        )

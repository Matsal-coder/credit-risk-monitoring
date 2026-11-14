"""Testes da exportacao JSON do monitoramento."""

import json
from types import SimpleNamespace

import numpy as np
import pytest

from credit_risk_monitoring.drift.reporting import (
    build_monitoring_payload,
    save_monitoring_json,
)


@pytest.fixture
def approved_result():
    inference = SimpleNamespace(
        scored_rows=4,
        probabilities=(0.1, 0.2, 0.3, 0.4),
        predictions=(0, 0, 1, 1),
        threshold=0.25,
    )

    return SimpleNamespace(
        approved=True,
        drift=object(),
        inference=inference,
        to_dict=lambda: {
            "batch_id": "test-report",
            "scenario_id": "strong",
            "execution_status": "completed",
            "quality_status": "approved",
            "drift": {
                "features_analyzed": 2,
                "features_drifted": 1,
            },
        },
    )


def test_build_aggregated_prediction_summary(approved_result):
    payload = build_monitoring_payload(approved_result)

    summary = payload["prediction_summary"]

    assert summary["scored_rows"] == 4
    assert summary["mean_default_probability"] == pytest.approx(0.25)
    assert summary["predicted_defaults"] == 2
    assert summary["positive_prediction_rate"] == 0.5
    assert summary["model_threshold"] == 0.25


def test_json_export_creates_file(tmp_path, approved_result):
    destination = tmp_path / "monitoring.json"

    saved = save_monitoring_json(approved_result, destination)

    assert saved == destination
    assert destination.is_file()

    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["prediction_summary"]["predicted_defaults"] == 2


def test_json_does_not_expose_individual_predictions(
    tmp_path,
    approved_result,
):
    destination = tmp_path / "monitoring.json"

    save_monitoring_json(approved_result, destination)

    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert "probabilities" not in payload
    assert "predictions" not in payload
    assert "SK_ID_CURR" not in payload
    assert "TARGET" not in payload


def test_json_does_not_overwrite_existing_file(
    tmp_path,
    approved_result,
):
    destination = tmp_path / "existing.json"
    destination.write_text("original", encoding="utf-8")

    with pytest.raises(FileExistsError):
        save_monitoring_json(approved_result, destination)

    assert destination.read_text(encoding="utf-8") == "original"


def test_rejected_monitoring_cannot_export(tmp_path, approved_result):
    approved_result.approved = False

    with pytest.raises(ValueError, match="nao aprovado"):
        save_monitoring_json(
            approved_result,
            tmp_path / "rejected.json",
        )

    assert not (tmp_path / "rejected.json").exists()


def test_export_requires_existing_directory(
    tmp_path,
    approved_result,
):
    destination = tmp_path / "missing" / "monitoring.json"

    with pytest.raises(ValueError, match="Diretorio"):
        save_monitoring_json(approved_result, destination)

    assert not destination.exists()


def test_json_accepts_numpy_integer_predictions(
    tmp_path,
    approved_result,
):
    """Garante serializacao de agregados vindos do NumPy."""
    approved_result.inference.predictions = (
        np.int64(0),
        np.int64(0),
        np.int64(1),
        np.int64(1),
    )

    destination = tmp_path / "numpy-predictions.json"

    save_monitoring_json(
        approved_result,
        destination,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))

    summary = payload["prediction_summary"]

    assert summary["predicted_defaults"] == 2
    assert type(summary["predicted_defaults"]) is int
    assert destination.is_file()


def test_reporting_normalizes_validation_tuples(
    approved_result,
) -> None:
    original_to_dict = approved_result.to_dict

    def payload_with_tuple():
        payload = original_to_dict()
        payload["inference"] = {
            "validations": [
                {"status": "approved", "violations": ()},
                {"status": "approved", "violations": ()},
            ]
        }
        return payload

    approved_result.to_dict = payload_with_tuple

    payload = build_monitoring_payload(approved_result)

    validations = payload["inference"]["validations"]

    assert len(validations) == 2
    assert all(type(item["violations"]) is list for item in validations)

    encoded = json.dumps(payload, allow_nan=False)
    assert json.loads(encoded) == payload


def test_html_export_creates_file(
    tmp_path,
    approved_result,
) -> None:
    from credit_risk_monitoring.drift.reporting import (
        save_monitoring_html,
    )

    class FakeSnapshot:
        def save_html(self, path: str) -> None:
            from pathlib import Path

            Path(path).write_text(
                "<html><body>Test report</body></html>",
                encoding="utf-8",
            )

    approved_result.snapshot = FakeSnapshot()

    destination = tmp_path / "monitoring.html"

    saved = save_monitoring_html(
        approved_result,
        destination,
    )

    assert saved == destination
    assert destination.is_file()
    assert "Test report" in destination.read_text(encoding="utf-8")


def test_html_export_does_not_overwrite(
    tmp_path,
    approved_result,
) -> None:
    from credit_risk_monitoring.drift.reporting import (
        save_monitoring_html,
    )

    class FakeSnapshot:
        def save_html(self, path: str) -> None:
            from pathlib import Path

            Path(path).write_text(
                "<html>new report</html>",
                encoding="utf-8",
            )

    approved_result.snapshot = FakeSnapshot()

    destination = tmp_path / "existing.html"
    destination.write_text(
        "original content",
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError):
        save_monitoring_html(
            approved_result,
            destination,
        )

    assert destination.read_text(encoding="utf-8") == "original content"


def test_rejected_monitoring_cannot_export_html(
    tmp_path,
    approved_result,
) -> None:
    from credit_risk_monitoring.drift.reporting import (
        save_monitoring_html,
    )

    approved_result.approved = False
    approved_result.snapshot = object()

    destination = tmp_path / "rejected.html"

    with pytest.raises(ValueError, match="nao aprovado"):
        save_monitoring_html(
            approved_result,
            destination,
        )

    assert not destination.exists()


def test_html_requires_snapshot(
    tmp_path,
    approved_result,
) -> None:
    from credit_risk_monitoring.drift.reporting import (
        save_monitoring_html,
    )

    approved_result.snapshot = None

    with pytest.raises(ValueError, match="Snapshot"):
        save_monitoring_html(
            approved_result,
            tmp_path / "missing-snapshot.html",
        )


def test_html_generation_failure_does_not_create_output(
    tmp_path,
    approved_result,
) -> None:
    from credit_risk_monitoring.drift.reporting import (
        save_monitoring_html,
    )

    class FailingSnapshot:
        def save_html(self, path: str) -> None:
            raise RuntimeError("HTML generation failed.")

    approved_result.snapshot = FailingSnapshot()

    destination = tmp_path / "failed.html"

    with pytest.raises(RuntimeError, match="generation failed"):
        save_monitoring_html(
            approved_result,
            destination,
        )

    assert not destination.exists()

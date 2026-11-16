"""Testes do rastreamento e compensacao de publicacoes."""

import pytest

from credit_risk_monitoring.observability.publication import (
    PublicationRollbackError,
    PublicationTracker,
)


def test_rollback_removes_registered_artifacts(tmp_path):
    first = tmp_path / "report.json"
    second = tmp_path / "scores.csv"

    tracker = PublicationTracker()

    first.write_text("report", encoding="utf-8")
    tracker.register(first)

    second.write_text("scores", encoding="utf-8")
    tracker.register(second)

    tracker.rollback()

    assert not first.exists()
    assert not second.exists()
    assert tracker.artifacts == []


def test_rollback_preserves_replaced_artifact(tmp_path):
    path = tmp_path / "report.json"
    replacement = tmp_path / "replacement.json"

    path.write_text("original", encoding="utf-8")

    tracker = PublicationTracker()
    tracker.register(path)

    replacement.write_text("replacement", encoding="utf-8")
    replacement.replace(path)

    with pytest.raises(
        PublicationRollbackError,
        match="Identidade",
    ):
        tracker.rollback()

    assert path.read_text(encoding="utf-8") == "replacement"


def test_rollback_preserves_modified_artifact(tmp_path):
    path = tmp_path / "report.json"
    path.write_text("original", encoding="utf-8")

    tracker = PublicationTracker()
    tracker.register(path)

    path.write_text(
        "modified content with different length",
        encoding="utf-8",
    )

    with pytest.raises(
        PublicationRollbackError,
        match="Identidade",
    ):
        tracker.rollback()

    assert path.read_text(encoding="utf-8").startswith("modified content")


def test_rollback_accepts_missing_artifact(tmp_path):
    path = tmp_path / "report.json"
    path.write_text("temporary", encoding="utf-8")

    tracker = PublicationTracker()
    tracker.register(path)

    path.unlink()

    tracker.rollback()

    assert not path.exists()


def test_rollback_does_not_delete_unregistered_file(tmp_path):
    registered = tmp_path / "report.json"
    unrelated = tmp_path / "unrelated.json"

    registered.write_text("registered", encoding="utf-8")
    unrelated.write_text("preserve", encoding="utf-8")

    tracker = PublicationTracker()
    tracker.register(registered)

    tracker.rollback()

    assert not registered.exists()
    assert unrelated.read_text(encoding="utf-8") == "preserve"


def test_duplicate_registration_is_rejected(tmp_path):
    path = tmp_path / "report.json"
    path.write_text("report", encoding="utf-8")

    tracker = PublicationTracker()
    tracker.register(path)

    with pytest.raises(
        PublicationRollbackError,
        match="registrado",
    ):
        tracker.register(path)


def test_clear_preserves_files(tmp_path):
    path = tmp_path / "report.json"
    path.write_text("report", encoding="utf-8")

    tracker = PublicationTracker()
    tracker.register(path)
    tracker.clear()

    assert tracker.artifacts == []
    assert path.read_text(encoding="utf-8") == "report"


def test_modified_artifact_blocks_all_deletions(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    tracker = PublicationTracker()

    first.write_text("original", encoding="utf-8")
    tracker.register(first)

    second.write_text("second", encoding="utf-8")
    tracker.register(second)

    first.write_text(
        "modified content with different size",
        encoding="utf-8",
    )

    with pytest.raises(PublicationRollbackError):
        tracker.rollback()

    assert first.exists()
    assert second.exists()


def test_missing_artifact_is_removed_from_tracker(tmp_path):
    path = tmp_path / "missing.json"
    path.write_text("temporary", encoding="utf-8")

    tracker = PublicationTracker()
    tracker.register(path)

    path.unlink()

    tracker.rollback()

    assert tracker.artifacts == []


def test_unlink_failure_preserves_artifact_record(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "report.json"
    path.write_text("important", encoding="utf-8")

    tracker = PublicationTracker()
    tracker.register(path)

    original_unlink = type(path).unlink

    def failing_unlink(self, *args, **kwargs):
        if self == path:
            raise PermissionError("simulated deletion failure")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(
        type(path),
        "unlink",
        failing_unlink,
    )

    with pytest.raises(
        PublicationRollbackError,
        match="Falha durante compensacao",
    ):
        tracker.rollback()

    assert path.exists()
    assert len(tracker.artifacts) == 1
    assert tracker.artifacts[0].path == path

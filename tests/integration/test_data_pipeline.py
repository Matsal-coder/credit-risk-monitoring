"""Testes de integracao da preparacao de dados."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from credit_risk_monitoring.data.preparation import (
    ID_COLUMN,
    MODEL_FEATURES,
    TARGET_COLUMN,
    load_dataset,
    prepare_features,
    split_dataset,
)


@pytest.fixture
def synthetic_csv(tmp_path):
    """Gera um CSV sintetico representativo."""

    n = 200

    df = pd.DataFrame(
        {
            "SK_ID_CURR": range(100000, 100000 + n),
            "TARGET": [0] * 160 + [1] * 40,
            "AMT_CREDIT": [100000.0] * n,
            "AMT_INCOME_TOTAL": [50000.0] * n,
            "AMT_ANNUITY": [10000.0] * n,
            "AMT_GOODS_PRICE": [90000.0] * n,
            "EXT_SOURCE_2": [0.5] * n,
            "EXT_SOURCE_3": [0.6] * n,
            "DAYS_BIRTH": [-12000] * n,
            "DAYS_EMPLOYED": [-1000] * (n - 1) + [365243],
            "DAYS_REGISTRATION": [-2000.0] * n,
            "CNT_CHILDREN": [1] * n,
            "CNT_FAM_MEMBERS": [3.0] * n,
            "NAME_INCOME_TYPE": ["Working"] * n,
            "NAME_EDUCATION_TYPE": ["Higher education"] * n,
            "FLAG_OWN_CAR": ["N"] * n,
            "FLAG_OWN_REALTY": ["Y"] * n,
            "NAME_CONTRACT_TYPE": ["Cash loans"] * n,
        }
    )

    path = tmp_path / "synthetic_credit.csv"
    df.to_csv(path, index=False)

    return path, df


def test_complete_data_flow(synthetic_csv):
    path, source = synthetic_csv

    loaded = load_dataset(path)
    prepared = prepare_features(loaded)
    partitions = split_dataset(prepared)

    assert len(loaded) == len(source)
    assert len(prepared) == len(source)

    assert list(prepared.columns) == [
        ID_COLUMN,
        TARGET_COLUMN,
        *MODEL_FEATURES,
    ]

    assert sum(map(len, partitions.values())) == len(source)

    output_ids = pd.concat(
        [part[ID_COLUMN] for part in partitions.values()],
        ignore_index=True,
    )

    assert output_ids.is_unique
    assert set(output_ids) == set(source[ID_COLUMN])

    for partition in partitions.values():
        assert list(partition.columns) == list(prepared.columns)


def test_complete_flow_is_reproducible(synthetic_csv):
    path, _ = synthetic_csv

    first = split_dataset(prepare_features(load_dataset(path)))
    second = split_dataset(prepare_features(load_dataset(path)))

    for name in first:
        pd.testing.assert_frame_equal(
            first[name],
            second[name],
            check_exact=True,
        )


def test_missing_csv_is_rejected(tmp_path):
    nonexistent = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        load_dataset(nonexistent)


def test_malformed_csv_is_rejected(tmp_path):
    path = tmp_path / "invalid.csv"
    path.write_text("INVALID,TARGET\n1,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Colunas obrigatorias"):
        load_dataset(path)


def test_sentinel_does_not_change_target(synthetic_csv):
    path, _ = synthetic_csv

    loaded = load_dataset(path)
    prepared = prepare_features(loaded)

    pd.testing.assert_series_equal(
        loaded[TARGET_COLUMN],
        prepared[TARGET_COLUMN],
    )

    assert prepared["DAYS_EMPLOYED_SENTINEL"].sum() == 1
    assert prepared["DAYS_EMPLOYED"].isna().sum() == 1


def test_dataset_artifact_generation(synthetic_csv, tmp_path):
    """Valida persistencia, manifesto e reproducibilidade."""

    source_path, source_df = synthetic_csv

    project_root = Path(__file__).resolve().parents[2]
    script = project_root / "scripts" / "prepare_dataset.py"

    output_dir = tmp_path / "processed"
    manifest_path = tmp_path / "data_manifest.json"

    command = [
        sys.executable,
        str(script),
        "--input",
        str(source_path),
        "--output-dir",
        str(output_dir),
        "--manifest",
        str(manifest_path),
    ]

    subprocess.run(
        command,
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["source"]["rows"] == len(source_df)
    assert manifest["preparation"]["random_state"] == 42
    assert len(manifest["preparation"]["model_features"]) == 17

    expected_names = {
        "train",
        "validation",
        "test",
        "reference",
    }

    assert set(manifest["partitions"]) == expected_names

    all_ids = []
    first_hashes = {}

    for name, info in manifest["partitions"].items():
        path = output_dir / info["filename"]

        assert path.is_file()

        data = pd.read_csv(path)
        assert len(data) == info["rows"]

        if name == "reference":
            assert "TARGET" not in data.columns
        else:
            assert "TARGET" in data.columns

        all_ids.extend(data["SK_ID_CURR"].tolist())

        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        assert file_hash == info["sha256"]
        first_hashes[name] = file_hash

    assert len(all_ids) == len(source_df)
    assert len(set(all_ids)) == len(source_df)

    # Segunda execucao com entradas e parametros identicos.
    subprocess.run(
        command,
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )

    second_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for name, info in second_manifest["partitions"].items():
        assert info["sha256"] == first_hashes[name]


def test_artifacts_verification_success(synthetic_csv, tmp_path):
    """Verificador aceita artefatos validos."""

    source_path, _ = synthetic_csv
    root = Path(__file__).resolve().parents[2]

    output_dir = tmp_path / "processed"
    manifest_path = tmp_path / "manifest.json"

    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "prepare_dataset.py"),
            "--input",
            str(source_path),
            "--output-dir",
            str(output_dir),
            "--manifest",
            str(manifest_path),
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "verify_dataset.py"),
            "--manifest",
            str(manifest_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "VERIFICACAO APROVADA" in result.stdout


@pytest.mark.parametrize("failure", ["tampered", "missing"])
def test_artifacts_verification_rejects_invalid(
    synthetic_csv,
    tmp_path,
    failure,
):
    """Rejeita arquivos alterados ou ausentes."""

    source_path, _ = synthetic_csv
    root = Path(__file__).resolve().parents[2]

    output_dir = tmp_path / "processed"
    manifest_path = tmp_path / "manifest.json"

    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "prepare_dataset.py"),
            "--input",
            str(source_path),
            "--output-dir",
            str(output_dir),
            "--manifest",
            str(manifest_path),
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    train_path = output_dir / "train.csv"

    if failure == "tampered":
        with train_path.open("a", encoding="utf-8") as file:
            file.write("\n")
    else:
        train_path.unlink()

    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "verify_dataset.py"),
            "--manifest",
            str(manifest_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "VERIFICACAO REPROVADA" in result.stderr

    if failure == "tampered":
        assert "Hash SHA-256 divergente" in result.stderr
    else:
        assert "Particao nao encontrada" in result.stderr

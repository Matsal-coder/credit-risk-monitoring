"""Deteccao de drift utilizando Evidently AI."""

import math
from dataclasses import dataclass

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset

SUPPORTED_PVALUE_METHODS = frozenset(
    {
        "K-S p_value",
        "chi-square p_value",
        "Z-test p_value",
    }
)

SUPPORTED_DISTANCE_METHODS = frozenset(
    {
        "Wasserstein distance (normed)",
        "Jensen-Shannon distance",
    }
)


@dataclass(frozen=True)
class FeatureDriftResult:
    """Resultado estatistico agregado de uma feature."""

    feature: str
    method: str
    score: float
    threshold: float
    drift_detected: bool

    def to_dict(self) -> dict:
        """Serializa o resultado com tipos nativos do Python."""
        return {
            "feature": self.feature,
            "method": self.method,
            "score": float(self.score),
            "threshold": float(self.threshold),
            "drift_detected": bool(self.drift_detected),
        }


def extract_feature_drift(
    metrics: list[dict],
    expected_features: tuple[str, ...],
) -> tuple[FeatureDriftResult, ...]:
    """Extrai metricas de drift do Evidently 0.7.23.

    P-values: valores abaixo do threshold indicam drift.
    Distancias: valores acima do threshold indicam drift.
    """
    if not expected_features or len(set(expected_features)) != len(expected_features):
        raise ValueError("Features esperadas invalidas.")

    extracted: dict[str, FeatureDriftResult] = {}

    for metric in metrics:
        config = metric.get("config", {})

        if config.get("type") != "evidently:metric_v2:ValueDrift":
            continue

        feature = config.get("column")
        method = config.get("method")
        threshold = config.get("threshold")
        score = metric.get("value")

        if feature not in expected_features:
            raise ValueError("Feature inesperada no resultado de drift.")

        if feature in extracted:
            raise ValueError("Resultado de drift duplicado.")

        is_pvalue = method in SUPPORTED_PVALUE_METHODS
        is_distance = method in SUPPORTED_DISTANCE_METHODS

        if not is_pvalue and not is_distance:
            raise ValueError("Metodo estatistico nao suportado.")

        if (
            isinstance(score, bool)
            or not isinstance(score, (float, int))
            or not math.isfinite(score)
            or score < 0
        ):
            raise ValueError("Score estatistico invalido.")

        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (float, int))
            or not math.isfinite(threshold)
        ):
            raise ValueError("Threshold estatistico invalido.")

        if is_pvalue:
            if score > 1 or not 0 < threshold < 1:
                raise ValueError("P-value ou threshold invalido.")

            detected = score < threshold

        else:
            if threshold <= 0:
                raise ValueError("Threshold de distancia invalido.")

            detected = score > threshold

        extracted[feature] = FeatureDriftResult(
            feature=feature,
            method=method,
            score=float(score),
            threshold=float(threshold),
            drift_detected=bool(detected),
        )

    if set(extracted) != set(expected_features):
        raise ValueError("Resultados de drift incompletos.")

    return tuple(extracted[name] for name in expected_features)


def run_evidently_drift(
    reference: pd.DataFrame,
    production: pd.DataFrame,
    features: tuple[str, ...],
) -> tuple[object, tuple[FeatureDriftResult, ...]]:
    """Compara distribuicoes numericas e categoricas."""
    if not features or len(set(features)) != len(features):
        raise ValueError("Features de monitoramento invalidas.")

    if reference.empty or production.empty:
        raise ValueError("Datasets de comparacao nao podem ser vazios.")

    if not reference.columns.is_unique or not production.columns.is_unique:
        raise ValueError("Nomes de colunas duplicados.")

    if not set(features).issubset(reference.columns) or not set(features).issubset(
        production.columns
    ):
        raise ValueError("Features ausentes nos datasets.")

    for feature in features:
        ref_col = reference[feature]
        prod_col = production[feature]

        ref_numeric = pd.api.types.is_numeric_dtype(ref_col)
        prod_numeric = pd.api.types.is_numeric_dtype(prod_col)

        if ref_numeric != prod_numeric:
            raise ValueError(f"Tipos incompatíveis na feature {feature}.")

        if not ref_numeric:
            ref_categorical = pd.api.types.is_string_dtype(ref_col) or isinstance(
                ref_col.dtype, pd.CategoricalDtype
            )

            prod_categorical = pd.api.types.is_string_dtype(prod_col) or isinstance(
                prod_col.dtype, pd.CategoricalDtype
            )

            if not ref_categorical or not prod_categorical:
                raise ValueError(f"Tipo categorico nao suportado: {feature}.")

    report = Report(
        [
            DataDriftPreset(columns=list(features)),
        ]
    )

    snapshot = report.run(
        current_data=production.loc[:, list(features)].copy(),
        reference_data=reference.loc[:, list(features)].copy(),
    )

    metrics = snapshot.dict().get("metrics", [])

    results = extract_feature_drift(metrics, features)

    return snapshot, results

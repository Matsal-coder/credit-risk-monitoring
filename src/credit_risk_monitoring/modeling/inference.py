"""Inferencia de credito com barreira bloqueante de qualidade."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from sklearn.utils.validation import check_is_fitted

from credit_risk_monitoring.data.inference import (
    prepare_inference_features,
)
from credit_risk_monitoring.data.preparation import MODEL_FEATURES
from credit_risk_monitoring.quality.results import ValidationResult
from credit_risk_monitoring.quality.validation import validate_batch

DEFAULT_MODEL_PATH = Path("artifacts/baseline_model.joblib")

InferenceStatus = Literal["approved", "rejected"]


@dataclass(frozen=True)
class InferenceResult:
    """Resultado de um lote submetido a inferencia."""

    batch_id: str
    status: InferenceStatus
    total_rows: int
    validations: tuple[ValidationResult, ...]
    threshold: float | None = None
    probabilities: tuple[float, ...] = ()
    predictions: tuple[int, ...] = ()

    @property
    def approved(self) -> bool:
        """Indica se houve inferencia autorizada."""
        return self.status == "approved"

    @property
    def scored_rows(self) -> int:
        """Quantidade de registros efetivamente pontuados."""
        return len(self.probabilities)

    def to_dict(self, *, include_scores: bool = False) -> dict:
        """Exporta resultado operacional sem identificadores pessoais."""
        output = {
            "batch_id": self.batch_id,
            "status": self.status,
            "total_rows": self.total_rows,
            "scored_rows": self.scored_rows,
            "threshold": self.threshold,
            "validations": [result.to_dict() for result in self.validations],
        }

        if include_scores:
            output["probabilities"] = list(self.probabilities)
            output["predictions"] = list(self.predictions)

        return output


def load_baseline_model(
    model_path: Path = DEFAULT_MODEL_PATH,
) -> tuple[object, float]:
    """Carrega e verifica o baseline persistido localmente.

    Utilizar somente artefatos confiaveis gerados pelo projeto.
    """
    artifact = joblib.load(model_path)

    if not isinstance(artifact, dict):
        raise ValueError("Estrutura do artefato invalida.")

    if not {"pipeline", "metadata"}.issubset(artifact):
        raise ValueError("Artefato sem pipeline ou metadata.")

    model = artifact["pipeline"]
    metadata = artifact["metadata"]

    if not isinstance(metadata, dict):
        raise ValueError("Metadata do modelo invalido.")

    if metadata.get("model_type") != "LogisticRegression":
        raise ValueError("Tipo de baseline inesperado.")

    if metadata.get("model_features") != list(MODEL_FEATURES):
        raise ValueError("Features incompatíveis com o baseline.")

    if metadata.get("feature_count") != len(MODEL_FEATURES):
        raise ValueError("Quantidade de features incompatível.")

    threshold_value = metadata.get("threshold")

    if isinstance(threshold_value, (bool, str)):
        raise ValueError("Threshold invalido no artefato.")

    try:
        threshold = float(threshold_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Threshold invalido no artefato.") from exc

    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Threshold fora do intervalo permitido.")

    check_is_fitted(model)

    classes = np.asarray(model.classes_)

    if not np.array_equal(classes, np.array([0, 1])):
        raise ValueError("Classes do baseline incompatíveis.")

    return model, threshold


def run_quality_gated_inference(
    df: pd.DataFrame,
    batch_id: str,
    *,
    model_path: Path = DEFAULT_MODEL_PATH,
) -> InferenceResult:
    """Valida ambos os estagios antes de executar predict_proba.

    Lotes rejeitados nao carregam o modelo e nao geram scores.
    Falhas operacionais inesperadas sao propagadas.
    """
    raw_validation = validate_batch(
        df,
        stage="raw_inference",
        batch_id=batch_id,
    )

    if not raw_validation.approved:
        return InferenceResult(
            batch_id=batch_id,
            status="rejected",
            total_rows=len(df),
            validations=(raw_validation,),
        )

    prepared = prepare_inference_features(df)

    prepared_validation = validate_batch(
        prepared,
        stage="prepared_inference",
        batch_id=batch_id,
    )

    validations = (raw_validation, prepared_validation)

    if not prepared_validation.approved:
        return InferenceResult(
            batch_id=batch_id,
            status="rejected",
            total_rows=len(df),
            validations=validations,
        )

    # Somente apos os dois contratos serem aprovados.
    model, threshold = load_baseline_model(model_path)

    features = prepared.loc[:, MODEL_FEATURES]

    probabilities = np.asarray(
        model.predict_proba(features),
        dtype=float,
    )

    if probabilities.shape != (len(prepared), 2):
        raise ValueError("Formato de probabilidades invalido.")

    if not np.isfinite(probabilities).all():
        raise ValueError("Probabilidades nao finitas.")

    if ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Probabilidades fora de [0, 1].")

    if not np.allclose(
        probabilities.sum(axis=1),
        1.0,
        rtol=0,
        atol=1e-8,
    ):
        raise ValueError("Probabilidades de classe inconsistentes.")

    positive_scores = probabilities[:, 1]
    predictions = (positive_scores >= threshold).astype(int)

    return InferenceResult(
        batch_id=batch_id,
        status="approved",
        total_rows=len(prepared),
        validations=validations,
        threshold=threshold,
        probabilities=tuple(float(score) for score in positive_scores),
        predictions=tuple(int(prediction) for prediction in predictions),
    )

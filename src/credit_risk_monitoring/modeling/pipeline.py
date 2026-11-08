"""Construcao do pipeline de preprocessamento e modelo baseline."""

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from credit_risk_monitoring.data.preparation import (
    CATEGORICAL_FEATURES,
    DERIVED_FEATURES,
    NUMERIC_FEATURES,
)

NUMERIC_PIPELINE = (
    ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
    ("scaler", StandardScaler()),
)

CATEGORICAL_PIPELINE = (
    (
        "imputer",
        SimpleImputer(
            strategy="most_frequent",
            keep_empty_features=True,
        ),
    ),
    (
        "encoder",
        OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=True,
        ),
    ),
)


def build_preprocessor() -> ColumnTransformer:
    """Constroi transformacoes sem ajusta-las aos dados."""

    numeric = Pipeline(NUMERIC_PIPELINE)
    categorical = Pipeline(CATEGORICAL_PIPELINE)

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric, list(NUMERIC_FEATURES)),
            ("categorical", categorical, list(CATEGORICAL_FEATURES)),
            ("indicator", "passthrough", list(DERIVED_FEATURES)),
        ],
        remainder="drop",
        sparse_threshold=0.3,
    )


def build_baseline_pipeline(
    *,
    class_weight: str | None = None,
    random_state: int = 42,
) -> Pipeline:
    """Constroi o baseline sem treinar o modelo."""

    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    solver="lbfgs",
                    class_weight=class_weight,
                    random_state=random_state,
                ),
            ),
        ]
    )

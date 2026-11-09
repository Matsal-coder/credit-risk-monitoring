"""Contratos Pandera para lotes de inferencia de credito."""

import pandas as pd
import pandera.pandas as pa

from credit_risk_monitoring.data.preparation import (
    CATEGORICAL_FEATURES,
    DERIVED_FEATURES,
    ID_COLUMN,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
)

RAW_FEATURES = (*NUMERIC_FEATURES, *CATEGORICAL_FEATURES)

RAW_INFERENCE_COLUMNS = (ID_COLUMN, *RAW_FEATURES)
PREPARED_INFERENCE_COLUMNS = (ID_COLUMN, *MODEL_FEATURES)


def _numeric_column(
    *,
    nullable: bool = True,
    checks: list[pa.Check] | None = None,
) -> pa.Column:
    """Coluna numerica sem conversao silenciosa de tipos."""
    return pa.Column(
        float,
        checks=checks,
        nullable=nullable,
        coerce=False,
    )


def _integer_column(
    *,
    nullable: bool = False,
    checks: list[pa.Check] | None = None,
    unique: bool = False,
) -> pa.Column:
    """Coluna inteira com verificacao explicita."""
    return pa.Column(
        int,
        checks=checks,
        nullable=nullable,
        unique=unique,
        coerce=False,
    )


def _categorical_column(
    *,
    nullable: bool = True,
    checks: list[pa.Check] | None = None,
) -> pa.Column:
    """Coluna categorica com ausencia permitida."""
    return pa.Column(
        str,
        checks=checks,
        nullable=nullable,
        coerce=False,
    )


def _base_columns() -> dict[str, pa.Column]:
    """Define colunas originais de entrada para inferencia."""
    columns = {
        ID_COLUMN: _integer_column(unique=True),
    }

    for feature in NUMERIC_FEATURES:
        if feature in ("DAYS_BIRTH", "CNT_CHILDREN"):
            columns[feature] = _integer_column(
                nullable=False,
            )
        else:
            columns[feature] = _numeric_column()

    for feature in CATEGORICAL_FEATURES:
        columns[feature] = _categorical_column()

    return columns


def _semantic_checks(
    *,
    prepared: bool,
) -> dict[str, list[pa.Check]]:
    """Regras semanticas apropriadas ao Home Credit."""
    checks = {
        "AMT_CREDIT": [
            pa.Check.gt(0, name="positive_credit"),
        ],
        "AMT_INCOME_TOTAL": [
            pa.Check.gt(0, name="positive_income"),
        ],
        "AMT_ANNUITY": [
            pa.Check.gt(0, name="positive_annuity"),
        ],
        "AMT_GOODS_PRICE": [
            pa.Check.gt(0, name="positive_goods_price"),
        ],
        "EXT_SOURCE_2": [
            pa.Check.in_range(0, 1, name="external_score_range"),
        ],
        "EXT_SOURCE_3": [
            pa.Check.in_range(0, 1, name="external_score_range"),
        ],
        "DAYS_BIRTH": [
            pa.Check.lt(0, name="negative_birth_days"),
        ],
        "DAYS_REGISTRATION": [
            pa.Check.le(0, name="nonpositive_registration_days"),
        ],
        "CNT_CHILDREN": [
            pa.Check.ge(0, name="nonnegative_children"),
        ],
        "CNT_FAM_MEMBERS": [
            pa.Check.ge(1, name="positive_family_members"),
        ],
        "FLAG_OWN_CAR": [
            pa.Check.isin(["Y", "N"], name="ownership_flag_domain"),
        ],
        "FLAG_OWN_REALTY": [
            pa.Check.isin(["Y", "N"], name="ownership_flag_domain"),
        ],
        "NAME_CONTRACT_TYPE": [
            pa.Check.isin(
                ["Cash loans", "Revolving loans"],
                name="contract_type_domain",
            ),
        ],
    }

    if prepared:
        checks["DAYS_EMPLOYED"] = [
            pa.Check.le(0, name="prepared_employment_days"),
        ]
    else:
        checks["DAYS_EMPLOYED"] = [
            pa.Check(
                lambda s: (s <= 0) | (s == 365243),
                name="raw_employment_days",
            ),
        ]

    return checks


def _build_columns(
    *,
    prepared: bool,
) -> dict[str, pa.Column]:
    """Combina tipos, nulidade e regras semanticas."""
    columns = _base_columns()
    checks = _semantic_checks(prepared=prepared)

    for name, rules in checks.items():
        original = columns[name]
        columns[name] = pa.Column(
            original.dtype,
            checks=rules,
            nullable=original.nullable,
            coerce=False,
        )

    if prepared:
        columns[DERIVED_FEATURES[0]] = pa.Column(
            None,
            checks=[
                pa.Check(
                    lambda s: pd.api.types.is_integer_dtype(s) and s.isin([0, 1]).all(),
                    name="valid_employment_indicator",
                ),
            ],
            nullable=False,
        )

    return columns


def build_raw_inference_schema() -> pa.DataFrameSchema:
    """Contrato para lote bruto sem TARGET."""
    return pa.DataFrameSchema(
        columns=_build_columns(prepared=False),
        checks=[
            pa.Check(
                lambda df: len(df) > 0,
                name="nonempty_batch",
            ),
        ],
        strict=True,
        unique_column_names=True,
        coerce=False,
        name="raw_inference",
    )


def build_prepared_inference_schema() -> pa.DataFrameSchema:
    """Contrato para features prontas para o modelo."""
    return pa.DataFrameSchema(
        columns=_build_columns(prepared=True),
        checks=[
            pa.Check(
                lambda df: len(df) > 0,
                name="nonempty_batch",
            ),
            pa.Check(
                lambda df: (
                    (df["DAYS_EMPLOYED_SENTINEL"] != 1) | df["DAYS_EMPLOYED"].isna()
                ).all(),
                name="sentinel_consistency",
            ),
        ],
        strict=True,
        unique_column_names=True,
        coerce=False,
        name="prepared_inference",
    )


RAW_INFERENCE_SCHEMA = build_raw_inference_schema()
PREPARED_INFERENCE_SCHEMA = build_prepared_inference_schema()

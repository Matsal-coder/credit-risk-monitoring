"""Execucao dos contratos e agregacao segura de violacoes."""

import pandas as pd
from pandera.errors import SchemaError, SchemaErrors

from credit_risk_monitoring.quality.contracts import (
    PREPARED_INFERENCE_SCHEMA,
    RAW_INFERENCE_SCHEMA,
)
from credit_risk_monitoring.quality.results import (
    QualityViolation,
    ValidationResult,
    ValidationStage,
)

SCHEMAS = {
    "raw_inference": RAW_INFERENCE_SCHEMA,
    "prepared_inference": PREPARED_INFERENCE_SCHEMA,
}

# Identificadores seguros e conhecidos das regras.
KNOWN_RULES = frozenset(
    {
        "positive_credit",
        "positive_income",
        "positive_annuity",
        "positive_goods_price",
        "external_score_range",
        "negative_birth_days",
        "nonpositive_registration_days",
        "nonnegative_children",
        "positive_family_members",
        "ownership_flag_domain",
        "contract_type_domain",
        "raw_employment_days",
        "prepared_employment_days",
        "valid_employment_indicator",
        "nonempty_batch",
        "sentinel_consistency",
        "column_in_dataframe",
        "column_in_schema",
        "field_uniqueness",
        "dataframe_column_labels_unique",
        "not_nullable",
    }
)


def _safe_column(value: object, allowed: set[str]) -> str:
    """Impede divulgacao de nomes inesperados de colunas."""
    if isinstance(value, str) and value in allowed:
        return value
    return "_schema"


def _safe_rule(value: object) -> str:
    """Normaliza identificadores conhecidos sem expor valores."""
    if not isinstance(value, str):
        return "schema_violation"

    rule_aliases = {
        "greater_than(0)": "positive_value",
        "greater_than_or_equal_to(0)": "nonnegative_value",
        "greater_than_or_equal_to(1)": "minimum_one",
        "less_than(0)": "negative_value",
        "less_than_or_equal_to(0)": "nonpositive_value",
        "in_range(0, 1)": "external_score_range",
    }

    if value in rule_aliases:
        return rule_aliases[value]

    if value in KNOWN_RULES:
        return value

    return "schema_violation"


def _aggregate_failures(
    error: SchemaError | SchemaErrors,
    allowed_columns: set[str],
) -> tuple[QualityViolation, ...]:
    """Agrega falhas por coluna e regra, sem valores individuais."""
    counts: dict[tuple[str, str], int] = {}

    column_rules = {
        ("AMT_CREDIT", "positive_value"): "positive_credit",
        ("AMT_INCOME_TOTAL", "positive_value"): "positive_income",
        ("AMT_ANNUITY", "positive_value"): "positive_annuity",
        ("AMT_GOODS_PRICE", "positive_value"): "positive_goods_price",
        ("DAYS_BIRTH", "negative_value"): "negative_birth_days",
        ("DAYS_REGISTRATION", "nonpositive_value"): ("nonpositive_registration_days"),
        ("CNT_CHILDREN", "nonnegative_value"): "nonnegative_children",
        ("CNT_FAM_MEMBERS", "minimum_one"): "positive_family_members",
    }

    if isinstance(error, SchemaErrors):
        failures = error.failure_cases
    else:
        failures = getattr(error, "failure_cases", None)

    if isinstance(failures, pd.DataFrame) and not failures.empty:
        for _, failure in failures.iterrows():
            column = _safe_column(
                failure.get("column"),
                allowed_columns,
            )
            rule = _safe_rule(failure.get("check"))
            rule = column_rules.get((column, rule), rule)

            key = (column, rule)
            counts[key] = counts.get(key, 0) + 1
    else:
        counts[("_schema", "schema_violation")] = 1

    return tuple(
        QualityViolation(
            column=column,
            rule=rule,
            count=count,
        )
        for (column, rule), count in sorted(counts.items())
    )


def validate_batch(
    df: pd.DataFrame,
    stage: ValidationStage,
    batch_id: str,
) -> ValidationResult:
    """Valida lote sem executar inferencia.

    Falhas de qualidade retornam status rejected.
    Erros operacionais inesperados sao propagados.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("O lote deve ser um pandas DataFrame.")

    if stage not in SCHEMAS:
        raise ValueError("Estagio de validacao desconhecido.")

    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id deve ser uma string nao vazia.")

    schema = SCHEMAS[stage]
    allowed_columns = set(schema.columns)

    try:
        schema.validate(df, lazy=True)
    except (SchemaError, SchemaErrors) as error:
        return ValidationResult(
            batch_id=batch_id,
            stage=stage,
            status="rejected",
            total_rows=len(df),
            violations=_aggregate_failures(
                error,
                allowed_columns,
            ),
        )

    return ValidationResult(
        batch_id=batch_id,
        stage=stage,
        status="approved",
        total_rows=len(df),
    )

"""Estruturas de resultado da validacao de qualidade."""

from dataclasses import asdict, dataclass, field
from typing import Literal

ValidationStatus = Literal["approved", "rejected"]
ValidationStage = Literal["raw_inference", "prepared_inference"]


@dataclass(frozen=True)
class QualityViolation:
    """Violacao agregada, sem dados individuais de clientes."""

    column: str
    rule: str
    count: int
    severity: str = "error"


@dataclass(frozen=True)
class ValidationResult:
    """Resultado estruturado de um contrato de qualidade."""

    batch_id: str
    stage: ValidationStage
    status: ValidationStatus
    total_rows: int
    violations: tuple[QualityViolation, ...] = field(
        default_factory=tuple,
    )

    @property
    def approved(self) -> bool:
        """Indica se o lote passou integralmente na validacao."""
        return self.status == "approved"

    @property
    def violation_count(self) -> int:
        """Total de ocorrencias reportadas pelos contratos."""
        return sum(item.count for item in self.violations)

    def to_dict(self) -> dict:
        """Converte o resultado para formato serializavel em JSON."""
        return asdict(self)

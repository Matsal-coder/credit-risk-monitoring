"""Persistencia transacional de eventos operacionais em SQLite."""

import json
import sqlite3
from collections.abc import Generator
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path

from credit_risk_monitoring.observability.events import OperationalEvent

DEFAULT_STORE_PATH = Path("artifacts/observability/events.sqlite3")

EVENT_FIELDS = frozenset(OperationalEvent.__dataclass_fields__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS operational_events (
    execution_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    execution_status TEXT NOT NULL
        CHECK (execution_status IN ('running', 'completed', 'failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_started
ON operational_events (started_at, execution_id);

CREATE INDEX IF NOT EXISTS idx_events_batch
ON operational_events (batch_id);
"""


class EventStoreError(RuntimeError):
    """Erro de integridade ou transicao do armazenamento."""


def _serialize(event: OperationalEvent) -> str:
    return json.dumps(
        event.to_dict(),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _deserialize(payload: str) -> OperationalEvent:
    """Reconstrui o contrato e revalida os campos armazenados."""
    try:
        values = json.loads(payload)

        if not isinstance(values, dict) or set(values) != EVENT_FIELDS:
            raise ValueError("Campos persistidos incompatíveis.")

        values["started_at"] = datetime.fromisoformat(values["started_at"])

        if values["finished_at"] is not None:
            values["finished_at"] = datetime.fromisoformat(values["finished_at"])

        return OperationalEvent(**values)

    except (TypeError, ValueError, KeyError) as exc:
        raise EventStoreError("Evento persistido invalido.") from exc


class SQLiteEventStore:
    """Repositorio local de tentativas operacionais."""

    def __init__(self, path: Path = DEFAULT_STORE_PATH) -> None:
        self.path = Path(path)

        if not self.path.parent.is_dir():
            raise ValueError("Diretorio do banco inexistente.")

        with self._connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self.path,
            timeout=10.0,
        )
        connection.row_factory = sqlite3.Row

        with closing(connection):
            with connection:
                yield connection

    @staticmethod
    def _read_event(row: sqlite3.Row) -> OperationalEvent:
        event = _deserialize(row["payload"])

        if (
            event.execution_id != row["execution_id"]
            or event.batch_id != row["batch_id"]
            or event.execution_status != row["execution_status"]
            or event.started_at.isoformat() != row["started_at"]
            or (
                event.finished_at.isoformat() if event.finished_at is not None else None
            )
            != row["finished_at"]
        ):
            raise EventStoreError("Indices e payload do evento divergentes.")

        return event

    def start(self, event: OperationalEvent) -> None:
        """Registra uma tentativa inicial de maneira idempotente."""
        if event.execution_status != "running":
            raise ValueError("start exige evento running.")

        serialized = _serialize(event)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                """
                SELECT * FROM operational_events
                WHERE execution_id = ?
                """,
                (event.execution_id,),
            ).fetchone()

            if existing is not None:
                previous = self._read_event(existing)

                if previous != event:
                    raise EventStoreError("execution_id ja utilizado por outro estado.")
                return

            connection.execute(
                """
                INSERT INTO operational_events (
                    execution_id,
                    batch_id,
                    execution_status,
                    started_at,
                    finished_at,
                    payload
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.execution_id,
                    event.batch_id,
                    event.execution_status,
                    event.started_at.isoformat(),
                    None,
                    serialized,
                ),
            )

    def finish(self, event: OperationalEvent) -> None:
        """Finaliza a tentativa sem sobrescrever estado terminal."""
        if event.execution_status not in ("completed", "failed"):
            raise ValueError("finish exige evento terminal.")

        serialized = _serialize(event)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                """
                SELECT * FROM operational_events
                WHERE execution_id = ?
                """,
                (event.execution_id,),
            ).fetchone()

            if existing is None:
                raise EventStoreError("Tentativa nao iniciada no armazenamento.")

            previous = self._read_event(existing)

            if previous == event:
                return

            if previous.execution_status != "running":
                raise EventStoreError("Evento terminal nao pode ser alterado.")

            if (
                previous.batch_id != event.batch_id
                or previous.pipeline != event.pipeline
                or previous.scenario_id != event.scenario_id
                or previous.started_at != event.started_at
            ):
                raise EventStoreError("Identidade da tentativa foi alterada.")

            updated = connection.execute(
                """
                UPDATE operational_events
                SET execution_status = ?,
                    finished_at = ?,
                    payload = ?
                WHERE execution_id = ?
                  AND execution_status = 'running'
                """,
                (
                    event.execution_status,
                    event.finished_at.isoformat(),
                    serialized,
                    event.execution_id,
                ),
            )

            if updated.rowcount != 1:
                raise EventStoreError("Transicao de estado nao realizada.")

    def get(self, execution_id: str) -> OperationalEvent | None:
        """Consulta uma tentativa por identificador."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM operational_events
                WHERE execution_id = ?
                """,
                (execution_id,),
            ).fetchone()

        return self._read_event(row) if row is not None else None

    def list_events(
        self,
        *,
        batch_id: str | None = None,
        limit: int = 100,
    ) -> list[OperationalEvent]:
        """Lista tentativas da mais recente para a mais antiga."""
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 1000
        ):
            raise ValueError("limit deve estar entre 1 e 1000.")

        query = """
            SELECT * FROM operational_events
        """
        parameters: list[str | int] = []

        if batch_id is not None:
            query += " WHERE batch_id = ?"
            parameters.append(batch_id)

        query += """
            ORDER BY started_at DESC, execution_id DESC
            LIMIT ?
        """
        parameters.append(limit)

        with self._connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [self._read_event(row) for row in rows]

    def count(self) -> int:
        """Retorna o numero de tentativas distintas persistidas."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM operational_events"
            ).fetchone()

        return int(row[0])

    def iter_events(
        self,
        *,
        chunk_size: int = 500,
    ) -> Generator[OperationalEvent]:
        """Percorre todo o historico com validacao e memoria limitada."""
        if (
            isinstance(chunk_size, bool)
            or not isinstance(chunk_size, int)
            or not 1 <= chunk_size <= 10000
        ):
            raise ValueError("chunk_size deve estar entre 1 e 10000.")

        with self._connect() as connection:
            # Mantem uma visao consistente durante a leitura.
            connection.execute("BEGIN")

            cursor = connection.execute(
                """
                SELECT *
                FROM operational_events
                ORDER BY started_at ASC, execution_id ASC
                """
            )

            while True:
                rows = cursor.fetchmany(chunk_size)

                if not rows:
                    break

                for row in rows:
                    yield self._read_event(row)

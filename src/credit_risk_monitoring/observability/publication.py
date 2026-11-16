"""Rastreamento conservador de artefatos publicados."""

import stat
from dataclasses import dataclass, field
from pathlib import Path


class PublicationRollbackError(RuntimeError):
    """Compensacao nao concluida com seguranca."""


@dataclass(frozen=True)
class PublishedArtifact:
    """Identidade observada apos a criacao do arquivo."""

    path: Path
    device: int
    inode: int
    size: int
    modified_ns: int

    @classmethod
    def capture(cls, path: Path) -> "PublishedArtifact":
        """Captura identidade sem seguir links simbolicos."""
        path = Path(path)
        metadata = path.lstat()

        if not stat.S_ISREG(metadata.st_mode):
            raise PublicationRollbackError("Artefato publicado nao e arquivo regular.")

        return cls(
            path=path,
            device=metadata.st_dev,
            inode=metadata.st_ino,
            size=metadata.st_size,
            modified_ns=metadata.st_mtime_ns,
        )

    def matches(self) -> bool:
        """Compara identidade e metadados atuais."""
        current = self.capture(self.path)

        return (
            self.device == current.device
            and self.inode == current.inode
            and self.size == current.size
            and self.modified_ns == current.modified_ns
        )


@dataclass
class PublicationTracker:
    """Registra artefatos para compensacao de melhor esforco."""

    artifacts: list[PublishedArtifact] = field(default_factory=list)

    def register(self, path: Path) -> None:
        """Registra um arquivo apos sua criacao completa."""
        path = Path(path)

        if any(
            artifact.path.resolve() == path.resolve() for artifact in self.artifacts
        ):
            raise PublicationRollbackError("Artefato ja registrado nesta tentativa.")

        self.artifacts.append(PublishedArtifact.capture(path))

    def clear(self) -> None:
        """Descarta registros, sem modificar arquivos."""
        self.artifacts.clear()

    def rollback(self) -> None:
        """Compensa artefatos com identidade compativel.

        Valida todos os arquivos antes de iniciar exclusoes.
        Nao garante atomicidade entre verificacao e unlink.
        """
        removable: list[PublishedArtifact] = []
        missing: list[PublishedArtifact] = []

        try:
            for artifact in reversed(self.artifacts):
                try:
                    if not artifact.matches():
                        raise PublicationRollbackError(
                            "Identidade de artefato alterada."
                        )

                    removable.append(artifact)

                except FileNotFoundError:
                    missing.append(artifact)

        except PublicationRollbackError:
            raise

        except OSError as exc:
            raise PublicationRollbackError(
                "Nao foi possivel verificar os artefatos."
            ) from exc

        # Os arquivos ausentes ja nao precisam ser compensados.
        for artifact in missing:
            self.artifacts.remove(artifact)

        for artifact in removable:
            try:
                artifact.path.unlink()

            except OSError as exc:
                raise PublicationRollbackError(
                    "Falha durante compensacao de artefatos."
                ) from exc

            self.artifacts.remove(artifact)

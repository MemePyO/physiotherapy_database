"""Database lifecycle service.

Owns database initialization, integrity checks, schema metadata and the
connection used by the repository layer.  UI code must not import ``db``
directly; it talks to this service instead.
"""

import db


class DatabaseService:
    """Facade over the database lifecycle operations."""

    def path(self) -> str:
        return db.db_path()

    def init(self) -> None:
        db.init_db()

    def checkpoint(self) -> None:
        db.checkpoint()

    def check_integrity(self) -> bool:
        return db.check_integrity()

    def schema_version(self) -> int:
        return db.get_schema_version()

    @property
    def expected_schema_version(self) -> int:
        return db.SCHEMA_VERSION

    def connection(self):
        """Return a raw connection for SQL the repository does not expose."""
        return db._get_conn()


_service = None


def get_database_service() -> DatabaseService:
    global _service
    if _service is None:
        _service = DatabaseService()
    return _service

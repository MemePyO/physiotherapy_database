"""Migration manager service."""

import logging

logger = logging.getLogger(__name__)


class MigrationManager:
    def __init__(self, conn):
        self.conn = conn

    def current_version(self):
        try:
            return int(self.conn.execute("PRAGMA user_version").fetchone()[0] or 0)
        except Exception:
            return 0

    def apply(self, target=None):
        from data.migrations import MIGRATIONS, set_version

        current = self.current_version()
        applied = []
        for v in sorted(MIGRATIONS.keys()):
            if v <= current:
                continue
            if target is not None and v > target:
                break
            desc, fn = MIGRATIONS[v]
            try:
                logger.info("Applying migration %d: %s", v, desc)
                fn(self.conn)
                set_version(self.conn, v)
                applied.append(v)
            except Exception as e:
                logger.error("Migration %d failed: %s", v, e)
                raise
        return applied

    def validate(self, expected_tables=None):
        from data.migrations import validate_schema

        return validate_schema(self.conn, expected_tables)

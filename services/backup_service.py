"""Backup and restore service.

Wraps the SQLite backup API, integrity verification and the pre-operation
safety copies so UI code never touches the database file directly.
"""

import shutil

import db


class BackupService:
    """Create, verify and restore database backups."""

    def backup_to(self, dest: str) -> bool:
        return db.backup_to(dest)

    def verify(self, path: str):
        return db.verify_backup(path)

    def pre_operation(self, label: str = "op") -> None:
        db.pre_operation_backup(label)

    def checkpoint(self) -> None:
        db.checkpoint()

    def restore_from(self, src: str) -> None:
        """Replace the live database with *src* and reinitialize the schema."""
        self.pre_operation("restore")
        self.checkpoint()
        shutil.copy2(src, db.db_path())
        db.init_db()


_service = None


def get_backup_service() -> BackupService:
    global _service
    if _service is None:
        _service = BackupService()
    return _service

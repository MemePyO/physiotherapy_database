"""Patient history/audit service."""

import db


class HistoryService:
    """Record and query field-level change history for a patient."""

    def add(self, patient_id, field, old_value, new_value):
        db.add_history(patient_id, field, old_value, new_value)

    def list(self, patient_id, limit=200):
        return db.list_history(patient_id, limit=limit)

    def clear(self, patient_id):
        db.delete_history(patient_id)


_service = None


def get_history_service() -> HistoryService:
    global _service
    if _service is None:
        _service = HistoryService()
    return _service

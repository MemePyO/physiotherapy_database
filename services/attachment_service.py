"""Attachment service.

Wraps file storage and the attachment metadata repository so UI code does
not touch the database or the attachment folder directly.
"""

import db


class AttachmentService:
    """Attach, list, fetch and remove patient files."""

    def add(self, patient_id, source_path):
        return db.add_attachment(patient_id, source_path)

    def list(self, patient_id):
        return db.list_attachments(patient_id)

    def get(self, attachment_id):
        return db.get_attachment(attachment_id)

    def delete(self, attachment_id):
        db.delete_attachment(attachment_id)


_service = None


def get_attachment_service() -> AttachmentService:
    global _service
    if _service is None:
        _service = AttachmentService()
    return _service

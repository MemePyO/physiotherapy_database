"""Service layer for the Physiotherapy Patient Database.

UI code depends on these services; services depend on the ``db`` repository.
"""

from .appointment_service import AppointmentService, get_appointment_service
from .attachment_service import AttachmentService, get_attachment_service
from .backup_service import BackupService, get_backup_service
from .database_service import DatabaseService, get_database_service
from .export_service import export_csv, export_pdf, export_word
from .history_service import HistoryService, get_history_service
from .patient_service import PatientService, get_patient_service
from .physio_service import PhysioService, get_physio_service
from .validation_service import (
    ValidationResult,
    validate_patient,
    validate_session,
    validate_time,
    validate_vas,
)

__all__ = [
    "AppointmentService",
    "get_appointment_service",
    "AttachmentService",
    "get_attachment_service",
    "BackupService",
    "get_backup_service",
    "DatabaseService",
    "get_database_service",
    "HistoryService",
    "get_history_service",
    "PatientService",
    "get_patient_service",
    "PhysioService",
    "get_physio_service",
    "ValidationResult",
    "validate_patient",
    "validate_session",
    "validate_vas",
    "validate_time",
    "export_csv",
    "export_pdf",
    "export_word",
]

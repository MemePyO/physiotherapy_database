"""Appointment scheduling service."""

import db


class AppointmentService:
    """List, create, update and delete appointments."""

    def list(self, start=None, end=None):
        return db.list_appointments(start=start, end=end)

    def add(self, patient_id, dt, duration_min=30, status="scheduled", notes=""):
        return db.add_appointment(
            patient_id, dt, duration_min=duration_min, status=status, notes=notes
        )

    def update(self, appointment_id, **fields):
        db.update_appointment(appointment_id, **fields)

    def delete(self, appointment_id):
        db.delete_appointment(appointment_id)


_service = None


def get_appointment_service() -> AppointmentService:
    global _service
    if _service is None:
        _service = AppointmentService()
    return _service

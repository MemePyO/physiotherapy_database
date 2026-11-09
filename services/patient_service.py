"""Patient service layer: business logic for patient management.

UI code should talk to this service instead of calling db.* directly.
"""
import db
import utils
from services.validation_service import validate_patient


class PatientService:
    def __init__(self):
        pass

    def list_patients(self, sort_by="name", sort_dir="asc", query=None):
        patients = db.get_all_patients(sort_by=sort_by, sort_dir=sort_dir)
        if query:
            q = query.strip().lower()
            patients = [p for p in patients if q in (p.get("name") or "").lower()
                        or q in (p.get("localitate") or "").lower()
                        or q in (p.get("diagnostic") or "").lower()]
        return patients

    def get_patient(self, patient_id=None, name=None):
        return db.get_patient(patient_id=patient_id, name=name)

    def create_patient(self, name, localitate="", sex="", dob="", diagnostic="",
                       objective="", evaluation="", observation="", nr_zile="",
                       decision_date=""):
        validation = validate_patient(name, dob, sex, localitate)
        if not validation.ok():
            return None, validation
        pid = db.add_patient(name, localitate, nr_zile=nr_zile,
                             decision_date=decision_date, sex=sex, dob=dob)
        db.update_patient(pid, diagnostic=diagnostic, objective=objective,
                          evaluation=evaluation, observation=observation)
        return pid, validation

    def update_patient(self, patient_id, **fields):
        name = fields.get("name")
        if name is not None:
            v = validate_patient(name, fields.get("dob", ""), fields.get("sex", ""),
                                 fields.get("localitate", ""))
            if not v.ok():
                return v
        db.update_patient(patient_id, **fields)
        return None

    def delete_patient(self, patient_id):
        return db.delete_patient(patient_id)

    def restore_patient(self, deleted_row_id):
        return db.restore_deleted(deleted_row_id)

    def list_deleted(self):
        return db.list_deleted()

    def get_patient_names(self):
        return db.get_patient_names()

    def get_localities(self):
        return db.get_localities()

    def ensure_patient_exists(self, name):
        return db.ensure_patient_exists(name)


# Module-level singleton for convenience
_service = None


def get_patient_service():
    global _service
    if _service is None:
        _service = PatientService()
    return _service
"""Form validation service with inline feedback support."""


class ValidationResult:
    def __init__(self):
        self.errors = {}  # field -> message

    def add(self, field, message):
        self.errors[field] = message

    def ok(self):
        return len(self.errors) == 0

    def __bool__(self):
        return self.ok()


def validate_patient(name, dob="", sex="", locality=""):
    r = ValidationResult()
    if not (name or "").strip():
        r.add("name", "Patient name is required.")
    if dob and not _valid_date(dob):
        r.add("dob", "Invalid date (use DD.MM.YYYY).")
    if sex and sex not in ("", "M", "F"):
        r.add("sex", "Sex must be M, F, or empty.")
    if locality and len(locality) > 100:
        r.add("locality", "Locality too long (max 100).")
    return r


def validate_session(date, duration=30, pain_before=0, pain_after=0):
    r = ValidationResult()
    if not date or not _valid_date(date):
        r.add("date", "Invalid date (use DD.MM.YYYY).")
    try:
        d = int(duration)
        if d < 1 or d > 600:
            r.add("duration", "Duration must be 1-600 minutes.")
    except (ValueError, TypeError):
        r.add("duration", "Duration must be a number.")
    for field, val in (("pain_before", pain_before), ("pain_after", pain_after)):
        try:
            v = float(val)
            if v < 0 or v > 10:
                r.add(field, "VAS must be 0-10.")
        except (ValueError, TypeError):
            r.add(field, "VAS must be a number.")
    return r


def validate_vas(value):
    r = ValidationResult()
    try:
        v = float(value)
        if v < 0 or v > 10:
            r.add("value", "VAS must be 0-10.")
    except (ValueError, TypeError):
        r.add("value", "VAS must be a number.")
    return r


def validate_time(text):
    r = ValidationResult()
    try:
        parts = text.strip().replace(".", ":").split(":")
        if len(parts) != 2:
            raise ValueError
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
    except (ValueError, TypeError):
        r.add("time", "Invalid time (use HH:MM).")
    return r


def _valid_date(text):
    try:
        import datetime

        datetime.datetime.strptime(text.strip(), "%d.%m.%Y")
        return True
    except (ValueError, TypeError):
        return False

"""Patient database module using SQLite."""
import json
import os
import sys
import sqlite3
from datetime import datetime

import log
logger = log.get_logger(__name__)


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _now():
    return datetime.now().strftime("%d.%m.%Y %H:%M")


MAX_NAME_LEN = 200
MAX_TEXT_LEN = 50000
MAX_LOCALITY_LEN = 100


def db_path() -> str:
    return os.path.join(_base_dir(), "patients.db")


def pre_operation_backup(label: str = "op") -> None:
    """Copy the current DB to backup/ before a destructive operation."""
    try:
        import shutil, datetime
        folder = os.path.join(_base_dir(), "backup")
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(folder, "pre_%s_%s.db" % (label, stamp))
        shutil.copy2(db_path(), dest)
    except Exception as e:
        logger.warning("pre_operation_backup failed: %s", e)


def _get_conn() -> 'sqlite3.Connection':
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except Exception as e:
        logger.debug("WAL mode unavailable: %s", e)
    return conn


from contextlib import contextmanager

@contextmanager
def _conn():
    """Context manager that guarantees the connection is closed."""
    conn = _get_conn()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _ensure_column(conn, table: str, column: str, decl: str) -> None:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        conn.commit()


def init_db() -> None:
    """Initialize database schema and migrate from patients.json if exists."""
    # Pre-migration backup for safety
    pre_migration_backup()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            localitate TEXT DEFAULT '',
            nr_zile TEXT DEFAULT '',
            decision_date TEXT DEFAULT '',
            diagnostic TEXT DEFAULT '',
            objective TEXT DEFAULT '',
            evaluation TEXT DEFAULT '',
            observation TEXT DEFAULT '',
            sex TEXT DEFAULT '',
            dob TEXT DEFAULT '',
            patient_code TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deleted_patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            name TEXT,
            localitate TEXT DEFAULT '',
            diagnostic TEXT DEFAULT '',
            objective TEXT DEFAULT '',
            evaluation TEXT DEFAULT '',
            observation TEXT DEFAULT '',
            sex TEXT DEFAULT '',
            dob TEXT DEFAULT '',
            patient_code TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            deleted_at TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            size INTEGER DEFAULT 0,
            added_at TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patient_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            field TEXT NOT NULL,
            old_value TEXT DEFAULT '',
            new_value TEXT DEFAULT '',
            changed_at TEXT DEFAULT ''
        )
    """)

    for stmt in (
        "CREATE TABLE IF NOT EXISTS treatment_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL, diagnosis_code TEXT DEFAULT '', body_region TEXT DEFAULT '', side TEXT DEFAULT '', prescribed_sessions INTEGER DEFAULT 0, start_date TEXT DEFAULT '', end_date TEXT DEFAULT '', goals TEXT DEFAULT '', contraindications TEXT DEFAULT '', notes TEXT DEFAULT '', created_at TEXT DEFAULT '', updated_at TEXT DEFAULT '')",
        "CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL, plan_id INTEGER, session_no INTEGER DEFAULT 1, date TEXT DEFAULT '', duration_min INTEGER DEFAULT 30, modalities TEXT DEFAULT '', exercises TEXT DEFAULT '', pain_before REAL DEFAULT 0, pain_after REAL DEFAULT 0, notes TEXT DEFAULT '', status TEXT DEFAULT 'done', created_at TEXT DEFAULT '', updated_at TEXT DEFAULT '')",
        "CREATE TABLE IF NOT EXISTS appointments (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL, datetime TEXT DEFAULT '', duration_min INTEGER DEFAULT 30, status TEXT DEFAULT 'scheduled', notes TEXT DEFAULT '', created_at TEXT DEFAULT '')",
        "CREATE TABLE IF NOT EXISTS outcome_measures (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL, measure TEXT DEFAULT 'VAS', value REAL DEFAULT 0, date TEXT DEFAULT '', notes TEXT DEFAULT '', created_at TEXT DEFAULT '')",
        "CREATE TABLE IF NOT EXISTS exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL, name TEXT DEFAULT '', sets INTEGER DEFAULT 3, reps INTEGER DEFAULT 10, hold_sec INTEGER DEFAULT 0, frequency TEXT DEFAULT '', notes TEXT DEFAULT '', assigned_date TEXT DEFAULT '', created_at TEXT DEFAULT '')",
    ):
        cur.execute(stmt)

    _ensure_column(conn, "patients", "created_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "patients", "updated_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "patients", "sex", "TEXT DEFAULT ''")
    _ensure_column(conn, "patients", "dob", "TEXT DEFAULT ''")
    _ensure_column(conn, "patients", "patient_code", "TEXT DEFAULT ''")
    _ensure_column(conn, "deleted_patients", "sex", "TEXT DEFAULT ''")
    _ensure_column(conn, "deleted_patients", "dob", "TEXT DEFAULT ''")
    _ensure_column(conn, "deleted_patients", "patient_code", "TEXT DEFAULT ''")

    conn.commit()

    migrate_from_json(conn)
    conn.commit()
    conn.close()

    # Integrity check (non-fatal: log result)
    try:
        ok = check_integrity()
        if not ok:
            logger.warning("Database integrity check FAILED")
    except Exception as e:
        logger.warning("Integrity check error: %s", e)


def check_integrity() -> bool:
    """Run PRAGMA integrity_check and foreign_key_check."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        res = cur.fetchone()
        ok = (res is not None and str(res[0]).lower() == "ok")
        cur.execute("PRAGMA foreign_key_check")
        fk_issues = cur.fetchall()
        conn.close()
        if fk_issues:
            logger.warning("Foreign key issues: %s", fk_issues)
            ok = False
        return ok
    except Exception as e:
        logger.warning("check_integrity failed: %s", e)
        return False


def migrate_from_json(conn) -> None:
    """Migrate patient names from patients.json to database."""
    json_path = os.path.join(_base_dir(), "patients.json")
    if not os.path.exists(json_path):
        return

    try:
        with open(json_path, encoding="utf-8") as f:
            names = json.load(f)
    except Exception as e:
        logger.warning("migrate_from_json failed: %s", e)
        return

    if not isinstance(names, list):
        return

    cur = conn.cursor()
    for name in names:
        name_str = str(name).strip()
        if not name_str:
            continue
        try:
            cur.execute("INSERT OR IGNORE INTO patients (name, sex, dob, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (name_str, "", "", _now(), _now()))
        except Exception:
            continue

    conn.commit()

    try:
        os.replace(json_path, json_path + ".migrated")
    except OSError:
        pass


def add_patient(name: str, localitate: str = "", nr_zile: str = "", decision_date: str = "", sex: str = "", dob: str = "") -> int:
    """Add a new patient to the database."""
    name_str = str(name).strip()
    if not name_str:
        raise ValueError("Patient name is required")
    if len(name_str) > MAX_NAME_LEN:
        raise ValueError("Patient name too long (max %d)" % MAX_NAME_LEN)
    if len(localitate or "") > MAX_LOCALITY_LEN:
        raise ValueError("Locality too long")
    conn = _get_conn()
    cur = conn.cursor()
    # generate patient code
    cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM patients")
    next_id = cur.fetchone()[0]
    code = "PP-%04d" % next_id
    try:
        cur.execute(
            "INSERT INTO patients (name, localitate, nr_zile, decision_date, sex, dob, patient_code, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name_str, localitate, nr_zile, decision_date, sex, dob, code, _now(), _now())
        )
        conn.commit()
        patient_id = cur.lastrowid
        conn.close()
        return patient_id
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("Patient already exists")
    except Exception as e:
        conn.close()
        raise


def get_patient(patient_id: int | None = None, name: str | None = None) -> dict | None:
    """Get a patient by ID or name."""
    conn = _get_conn()
    cur = conn.cursor()
    if patient_id is not None:
        cur.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    elif name is not None:
        cur.execute("SELECT * FROM patients WHERE LOWER(name) = LOWER(?)", (name.strip(),))
    else:
        conn.close()
        return None
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


SORT_COLUMNS = {
    "nr": "id",
    "name": "name",
    "localitate": "localitate",
    "diagnostic": "diagnostic",
    "updated": "updated_at",
    "created": "created_at",
}


def get_all_patients(sort_by: str = "name", sort_dir: str = "asc") -> list[dict]:
    """Get all patients, optionally sorted."""
    col = SORT_COLUMNS.get(sort_by, "name")
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM patients ORDER BY {col} {direction}")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_patient(patient_id: int, name=None, localitate=None, nr_zile=None, decision_date=None, diagnostic=None, objective=None, evaluation=None, observation=None, sex=None, dob=None) -> None:
    """Update patient information and record history for changed fields."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    old_row = cur.fetchone()
    old = dict(old_row) if old_row else {}

    provided = {}
    if name is not None:
        name = str(name).strip()
        if not name:
            raise ValueError("Patient name is required")
        if len(name) > MAX_NAME_LEN:
            raise ValueError("Patient name too long (max %d)" % MAX_NAME_LEN)
        provided["name"] = name
    if localitate is not None:
        if len(localitate) > MAX_LOCALITY_LEN:
            raise ValueError("Locality too long")
        provided["localitate"] = localitate
    for _f, _v in (("diagnostic", diagnostic), ("objective", objective),
                    ("evaluation", evaluation), ("observation", observation)):
        if _v is not None and len(_v) > MAX_TEXT_LEN:
            raise ValueError("%s too long (max %d)" % (_f, MAX_TEXT_LEN))
    if nr_zile is not None:
        provided["nr_zile"] = nr_zile
    if decision_date is not None:
        provided["decision_date"] = decision_date
    if diagnostic is not None:
        provided["diagnostic"] = diagnostic
    if objective is not None:
        provided["objective"] = objective
    if evaluation is not None:
        provided["evaluation"] = evaluation
    if observation is not None:
        provided["observation"] = observation
    if sex is not None:
        provided["sex"] = sex
    if dob is not None:
        provided["dob"] = dob

    if not provided:
        conn.close()
        return

    updates = []
    params = []
    for f, v in provided.items():
        updates.append(f"{f} = ?")
        params.append(v)
    updates.append("updated_at = ?")
    params.append(_now())
    params.append(patient_id)
    try:
        cur.execute(f"UPDATE patients SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("Patient name already exists")

    now = _now()
    for f, v in provided.items():
        old_val = old.get(f, "")
        if old_val is None:
            old_val = ""
        new_val = v if v is not None else ""
        if str(old_val) != str(new_val):
            try:
                cur.execute("INSERT INTO patient_history (patient_id, field, old_value, new_value, changed_at) VALUES (?, ?, ?, ?, ?)",
                            (patient_id, f, str(old_val), str(new_val), now))
            except Exception as e:
                logger.warning("history insert failed: %s", e)
    conn.commit()
    conn.close()


def delete_patient(patient_id: int) -> int | None:
    """Soft-delete: move patient into deleted_patients for undo. Returns deleted_patients row id."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    d = dict(row)
    try:
        cur.execute("""
            INSERT INTO deleted_patients (patient_id, name, localitate, diagnostic, objective, evaluation, observation, sex, dob, patient_code, created_at, updated_at, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (d.get('id'), d.get('name'), d.get('localitate', ''), d.get('diagnostic', ''),
              d.get('objective', ''), d.get('evaluation', ''), d.get('observation', ''),
              d.get('sex', ''), d.get('dob', ''), d.get('patient_code', ''),
              d.get('created_at', ''), d.get('updated_at', ''), _now()))
        deleted_row_id = cur.lastrowid
        cur.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
        return deleted_row_id
    finally:
        conn.close()


def list_deleted() -> list[dict]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deleted_patients ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def restore_deleted(deleted_row_id: int) -> int | None:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deleted_patients WHERE id = ?", (deleted_row_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    d = dict(row)
    try:
        cur.execute("""
            INSERT INTO patients (name, localitate, diagnostic, objective, evaluation, observation, sex, dob, patient_code, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (d.get('name'), d.get('localitate', ''), d.get('diagnostic', ''),
              d.get('objective', ''), d.get('evaluation', ''), d.get('observation', ''),
              d.get('sex', ''), d.get('dob', ''), d.get('patient_code', ''),
              d.get('created_at', '') or _now(), _now()))
        pid = cur.lastrowid
        cur.execute("DELETE FROM deleted_patients WHERE id = ?", (deleted_row_id,))
        conn.commit()
        conn.close()
        return pid
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("Patient name already exists")


def get_patient_names() -> list[str]:
    """Get all patient names for autocomplete."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM patients ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [row['name'] for row in rows]


def get_localities() -> list[str]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT localitate FROM patients WHERE localitate != '' ORDER BY localitate")
    rows = cur.fetchall()
    conn.close()
    return [row['localitate'] for row in rows]


def ensure_patient_exists(name: str) -> int | None:
    """Ensure a patient exists in the database, create if not."""
    name_str = str(name).strip()
    if not name_str:
        return None
    patient = get_patient(name=name_str)
    if patient:
        return patient['id']
    try:
        return add_patient(name_str)
    except Exception as e:
        logger.debug("add_patient failed, retrying lookup: %s", e)
        patient = get_patient(name=name_str)
        return patient['id'] if patient else None


def get_diagnostic(patient_id: int) -> str:
    p = get_patient(patient_id=patient_id)
    return p.get('diagnostic', '') if p else ''


def get_objective(patient_id: int) -> str:
    p = get_patient(patient_id=patient_id)
    return p.get('objective', '') if p else ''


def get_evaluation(patient_id: int) -> str:
    p = get_patient(patient_id=patient_id)
    return p.get('evaluation', '') if p else ''


def get_observation(patient_id: int) -> str:
    p = get_patient(patient_id=patient_id)
    return p.get('observation', '') if p else ''



def attachments_dir() -> str:
    return os.path.join(_base_dir(), "attachments")


def _patient_attach_folder(patient_id: int) -> str:
    folder = os.path.join(attachments_dir(), str(patient_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def add_attachment(patient_id: int, source_path: str) -> int:
    import shutil
    if not source_path or not os.path.exists(source_path):
        raise ValueError("File not found")
    size = os.path.getsize(source_path)
    if size > 50 * 1024 * 1024:
        raise ValueError("File too large (max 50 MB)")
    folder = _patient_attach_folder(patient_id)
    base = os.path.basename(source_path)
    # sanitize filename: strip path traversal and control chars
    base = base.replace("..", "_").replace(os.sep, "_").replace("/", "_").replace("\\", "_")
    if not base or base in (".", ".."):
        raise ValueError("Invalid filename")
    dest = os.path.join(folder, base)
    if os.path.exists(dest):
        stem, ext = os.path.splitext(base)
        i = 1
        while os.path.exists(os.path.join(folder, "%s_%d%s" % (stem, i, ext))):
            i += 1
        dest = os.path.join(folder, "%s_%d%s" % (stem, i, ext))
    # containment check
    if os.path.commonpath([os.path.abspath(folder), os.path.abspath(dest)]) != os.path.abspath(folder):
        raise ValueError("Invalid destination path")
    shutil.copy2(source_path, dest)
    size = os.path.getsize(dest)
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO attachments (patient_id, filename, stored_path, size, added_at) VALUES (?, ?, ?, ?, ?)",
                (patient_id, os.path.basename(dest), dest, size, _now()))
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def list_attachments(patient_id: int) -> list[dict]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attachments WHERE patient_id = ? ORDER BY id DESC", (patient_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attachment(att_id: int) -> dict | None:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attachments WHERE id = ?", (att_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_attachment(att_id: int) -> None:
    att = get_attachment(att_id)
    if not att:
        return
    try:
        if att.get("stored_path") and os.path.exists(att["stored_path"]):
            os.remove(att["stored_path"])
    except OSError:
        pass
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM attachments WHERE id = ?", (att_id,))
    conn.commit()
    conn.close()


def add_history(patient_id: int, field: str, old_value, new_value) -> None:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO patient_history (patient_id, field, old_value, new_value, changed_at) VALUES (?, ?, ?, ?, ?)",
                (patient_id, field, str(old_value or ""), str(new_value or ""), _now()))
    conn.commit()
    conn.close()


def delete_history(patient_id: int) -> None:
    """Remove all history/audit entries for a patient."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM patient_history WHERE patient_id = ?", (patient_id,))
    conn.commit()
    conn.close()


def list_history(patient_id: int, limit: int = 200) -> list[dict]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patient_history WHERE patient_id = ? ORDER BY id DESC LIMIT ?", (patient_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def verify_backup(path: str) -> tuple[bool, object]:
    """Verify a backup db file is readable and has patients table."""
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM patients")
        n = cur.fetchone()[0]
        conn.close()
        return True, n
    except Exception as e:
        return False, str(e)

def pre_migration_backup() -> str | None:
    """Create a backup of patients.db before schema migration, if it exists."""
    dbp = db_path()
    if not os.path.exists(dbp):
        return None
    import shutil, datetime
    folder = os.path.join(os.path.dirname(dbp), "backup")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(folder, "pre_migration_" + stamp + ".db")
    try:
        shutil.copy2(dbp, dest)
        return dest
    except Exception as e:
        logger.warning("pre_migration_backup failed: %s", e)
        return None
# --- physiotherapy helpers ---


BODY_REGIONS = ["Cervical", "Thoracic", "Lumbar", "Shoulder", "Elbow", "Wrist/Hand",
                "Hip", "Knee", "Ankle/Foot", "Other"]
SIDES = ["Left", "Right", "Bilateral", "N/A"]
MODALITIES = ["Ultrasound", "TENS", "Manual therapy", "Exercise", "Heat", "Cold", "Laser", "Traction"]
SESSION_STATUSES = ["scheduled", "done", "cancelled", "no-show"]
OUTCOME_MEASURES = ["VAS", "NRS"]


def get_plan(patient_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM treatment_plans WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_plan(patient_id, **fields):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM treatment_plans WHERE patient_id = ?", (patient_id,))
    row = cur.fetchone()
    now = _now()
    cols = ["diagnosis_code", "body_region", "side", "prescribed_sessions", "start_date", "end_date",
            "goals", "contraindications", "notes"]
    vals = [fields.get(c) for c in cols]
    if row:
        pid = row["id"]
        updates = ", ".join("%s = ?" % c for c in cols) + ", updated_at = ?"
        cur.execute("UPDATE treatment_plans SET %s WHERE id = ?" % updates, vals + [now, pid])
    else:
        cur.execute(
            "INSERT INTO treatment_plans (patient_id, diagnosis_code, body_region, side, prescribed_sessions, "
            "start_date, end_date, goals, contraindications, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [patient_id] + vals + [now, now])
        pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def list_sessions(patient_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sessions WHERE patient_id = ? ORDER BY date DESC, id DESC", (patient_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_session(patient_id, **fields):
    conn = _get_conn()
    cur = conn.cursor()
    now = _now()
    cur.execute(
        "INSERT INTO sessions (patient_id, plan_id, session_no, date, duration_min, modalities, exercises, "
        "pain_before, pain_after, notes, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (patient_id, fields.get("plan_id"), fields.get("session_no", 1), fields.get("date", ""),
         fields.get("duration_min", 30), fields.get("modalities", ""), fields.get("exercises", ""),
         fields.get("pain_before", 0), fields.get("pain_after", 0), fields.get("notes", ""),
         fields.get("status", "done"), now, now))
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def update_session(session_id, **fields):
    conn = _get_conn()
    cur = conn.cursor()
    now = _now()
    cols = ["plan_id", "session_no", "date", "duration_min", "modalities", "exercises",
            "pain_before", "pain_after", "notes", "status"]
    updates = []
    params = []
    for c in cols:
        if c in fields and fields[c] is not None:
            updates.append("%s = ?" % c)
            params.append(fields[c])
    if not updates:
        conn.close()
        return
    updates.append("updated_at = ?")
    params.append(now)
    params.append(session_id)
    cur.execute("UPDATE sessions SET %s WHERE id = ?" % ", ".join(updates), params)
    conn.commit()
    conn.close()


def delete_session(session_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def list_appointments(start=None, end=None):
    conn = _get_conn()
    cur = conn.cursor()
    if start and end:
        cur.execute("SELECT * FROM appointments WHERE datetime >= ? AND datetime <= ? ORDER BY datetime", (start, end))
    else:
        cur.execute("SELECT * FROM appointments ORDER BY datetime")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_appointment(patient_id, dt, duration_min=30, status="scheduled", notes=""):
    conn = _get_conn()
    cur = conn.cursor()
    now = _now()
    cur.execute("INSERT INTO appointments (patient_id, datetime, duration_min, status, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (patient_id, dt, duration_min, status, notes, now))
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def update_appointment(app_id, **fields):
    conn = _get_conn()
    cur = conn.cursor()
    cols = ["datetime", "duration_min", "status", "notes"]
    updates = []
    params = []
    for c in cols:
        if c in fields and fields[c] is not None:
            updates.append("%s = ?" % c)
            params.append(fields[c])
    if not updates:
        conn.close()
        return
    params.append(app_id)
    cur.execute("UPDATE appointments SET %s WHERE id = ?" % ", ".join(updates), params)
    conn.commit()
    conn.close()


def delete_appointment(app_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointments WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def list_outcomes(patient_id, measure=None):
    conn = _get_conn()
    cur = conn.cursor()
    if measure:
        cur.execute("SELECT * FROM outcome_measures WHERE patient_id = ? AND measure = ? ORDER BY date", (patient_id, measure))
    else:
        cur.execute("SELECT * FROM outcome_measures WHERE patient_id = ? ORDER BY date", (patient_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_outcome(patient_id, measure, value, date, notes=""):
    conn = _get_conn()
    cur = conn.cursor()
    now = _now()
    cur.execute("INSERT INTO outcome_measures (patient_id, measure, value, date, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (patient_id, measure, value, date, notes, now))
    conn.commit()
    oid = cur.lastrowid
    conn.close()
    return oid


def delete_outcome(oid):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM outcome_measures WHERE id = ?", (oid,))
    conn.commit()
    conn.close()


def list_exercises(patient_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM exercises WHERE patient_id = ? ORDER BY id", (patient_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_exercise(patient_id, **fields):
    conn = _get_conn()
    cur = conn.cursor()
    now = _now()
    cur.execute(
        "INSERT INTO exercises (patient_id, name, sets, reps, hold_sec, frequency, notes, assigned_date, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (patient_id, fields.get("name", ""), fields.get("sets", 3), fields.get("reps", 10),
         fields.get("hold_sec", 0), fields.get("frequency", ""), fields.get("notes", ""),
         fields.get("assigned_date", ""), now))
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def update_exercise(eid, **fields):
    conn = _get_conn()
    cur = conn.cursor()
    cols = ["name", "sets", "reps", "hold_sec", "frequency", "notes", "assigned_date"]
    updates = []
    params = []
    for c in cols:
        if c in fields and fields[c] is not None:
            updates.append("%s = ?" % c)
            params.append(fields[c])
    if not updates:
        conn.close()
        return
    params.append(eid)
    cur.execute("UPDATE exercises SET %s WHERE id = ?" % ", ".join(updates), params)
    conn.commit()
    conn.close()


def delete_exercise(eid):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM exercises WHERE id = ?", (eid,))
    conn.commit()
    conn.close()

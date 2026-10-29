"""Patient database module using SQLite."""
import json
import os
import sqlite3
from datetime import datetime

import log
logger = log.get_logger(__name__)


def _now():
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def db_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "patients.db")


def _get_conn() -> 'sqlite3.Connection':
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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


def migrate_from_json(conn) -> None:
    """Migrate patient names from patients.json to database."""
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patients.json")
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
        provided["name"] = str(name).strip()
    if localitate is not None:
        provided["localitate"] = localitate
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
            except Exception:
                pass
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
    except Exception:
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
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "attachments")


def _patient_attach_folder(patient_id: int) -> str:
    folder = os.path.join(attachments_dir(), str(patient_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def add_attachment(patient_id: int, source_path: str) -> int:
    import shutil
    if not source_path or not os.path.exists(source_path):
        raise ValueError("File not found")
    folder = _patient_attach_folder(patient_id)
    base = os.path.basename(source_path)
    dest = os.path.join(folder, base)
    if os.path.exists(dest):
        stem, ext = os.path.splitext(base)
        i = 1
        while os.path.exists(os.path.join(folder, "%s_%d%s" % (stem, i, ext))):
            i += 1
        dest = os.path.join(folder, "%s_%d%s" % (stem, i, ext))
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
    except Exception:
        return None

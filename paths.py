"""Writable data directory and single-instance lock management.

All mutable application data (database, logs, settings, backups, attachments)
lives under a per-user data directory instead of beside the executable, so the
app works even when installed in a read-only location such as Program Files.
"""

import os
import sys


def _is_frozen():
    return getattr(sys, "frozen", False)


def app_data_dir() -> str:
    """Return the per-user writable data directory, creating it if needed."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
    path = os.path.join(base, "PhysioDatabase")
    os.makedirs(path, exist_ok=True)
    return path


def migrate_legacy_data(legacy_dir: str) -> None:
    """One-time copy of data from the old exe-adjacent location."""
    import shutil

    if not os.path.isdir(legacy_dir):
        return
    # only migrate if the new location is empty
    new_dir = app_data_dir()
    marker = os.path.join(new_dir, ".migrated")
    if os.path.exists(marker):
        return
    for name in ("patients.db", "settings.json"):
        src = os.path.join(legacy_dir, name)
        dst = os.path.join(new_dir, name)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass
    for sub in ("backup", "attachments"):
        src = os.path.join(legacy_dir, sub)
        dst = os.path.join(new_dir, sub)
        if os.path.isdir(src) and not os.path.exists(dst):
            try:
                shutil.copytree(src, dst)
            except Exception:
                pass
    try:
        with open(marker, "w") as fh:
            fh.write("ok")
    except Exception:
        pass


class SingleInstanceManager:
    """Best-effort single-instance lock using a lock file."""

    def __init__(self, name: str = "PhysioDatabase"):
        self.name = name
        self.lock_path = os.path.join(app_data_dir(), name + ".lock")
        self._handle = None
        self.acquired = False

    def acquire(self) -> bool:
        try:
            # Try exclusive create
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            self._handle = os.fdopen(fd, "w")
            self._handle.write(str(os.getpid()))
            self._handle.flush()
            self.acquired = True
            return True
        except FileExistsError:
            # Check if the owning process is still alive
            try:
                with open(self.lock_path) as fh:
                    pid = int(fh.read().strip())
                # On Windows, os.kill(pid, 0) works for signaling
                os.kill(pid, 0)
                # process alive -> not acquired
                return False
            except (ValueError, OSError, ProcessLookupError):
                # stale lock -> remove and retry
                try:
                    os.remove(self.lock_path)
                except OSError:
                    pass
                return self.acquire()
        except Exception:
            return True  # fail open

    def release(self) -> None:
        try:
            if self._handle is not None:
                self._handle.close()
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except Exception:
            pass
        self.acquired = False

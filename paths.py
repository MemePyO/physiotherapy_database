"""Writable data directory and single-instance lock management.

All mutable application data (database, logs, settings, backups, attachments)
lives under a per-user data directory instead of beside the executable, so the
app works even when installed in a read-only location such as Program Files.
"""

import os
import sys
from typing import IO


def _is_frozen():
    return getattr(sys, "frozen", False)


def app_data_dir() -> str:
    """Return the per-user writable data directory, creating it if needed.

    ``PHYSIO_DATA_DIR`` overrides the location.  The override is used by
    portable installs, release smoke tests and CI so they never touch the real
    user profile.
    """
    override = os.environ.get("PHYSIO_DATA_DIR")
    if override:
        path = os.path.abspath(override)
        os.makedirs(path, exist_ok=True)
        return path
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


def _pid_alive(pid: int) -> bool:
    """Return whether *pid* is a live process.

    Windows cannot use ``os.kill(pid, 0)`` for this check: signal 0 maps to
    ``CTRL_C_EVENT`` on that platform and may interrupt the current console
    process group.  Use the Win32 process API instead.
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class SingleInstanceManager:
    """Best-effort single-instance lock using a lock file."""

    def __init__(self, name: str = "PhysioDatabase"):
        self.name = name
        self.lock_path = os.path.join(app_data_dir(), name + ".lock")
        self._handle: IO[str] | None = None
        self.acquired = False

    def acquire(self) -> bool:
        try:
            # Try exclusive create
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            handle = os.fdopen(fd, "w")
            self._handle = handle
            handle.write(str(os.getpid()))
            handle.flush()
            self.acquired = True
            return True
        except FileExistsError:
            # Check if the owning process is still alive
            pid = None
            try:
                with open(self.lock_path) as fh:
                    pid = int(fh.read().strip())
            except (ValueError, OSError):
                pid = None
            try:
                if pid is not None and _pid_alive(pid):
                    return False
            except Exception:
                pass
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

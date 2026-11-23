"""Tests for writable data-directory selection, migration and the lock file."""

import os
import sys

import paths


def test_app_data_dir_windows_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.delenv("PHYSIO_DATA_DIR", raising=False)
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    result = paths.app_data_dir()
    assert result == os.path.join(str(tmp_path), "PhysioDatabase")
    assert os.path.isdir(result)


def test_app_data_dir_windows_falls_back_to_home(monkeypatch, tmp_path):
    monkeypatch.delenv("PHYSIO_DATA_DIR", raising=False)
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    result = paths.app_data_dir()
    assert result.startswith(str(tmp_path))


def test_app_data_dir_darwin(monkeypatch, tmp_path):
    monkeypatch.delenv("PHYSIO_DATA_DIR", raising=False)
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    result = paths.app_data_dir()
    assert result == os.path.join(str(tmp_path), "Library", "Application Support", "PhysioDatabase")


def test_app_data_dir_linux_prefers_xdg(monkeypatch, tmp_path):
    monkeypatch.delenv("PHYSIO_DATA_DIR", raising=False)
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    result = paths.app_data_dir()
    assert result == os.path.join(str(tmp_path / "xdg"), "PhysioDatabase")


def test_migrate_legacy_data_copies_once(monkeypatch, tmp_path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "patients.db").write_text("db", encoding="utf-8")
    (legacy / "settings.json").write_text("{}", encoding="utf-8")
    (legacy / "backup").mkdir()
    (legacy / "backup" / "old.db").write_text("b", encoding="utf-8")
    (legacy / "attachments").mkdir()
    (legacy / "attachments" / "a.txt").write_text("a", encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir()
    monkeypatch.setattr(paths, "app_data_dir", lambda: str(target))

    paths.migrate_legacy_data(str(legacy))

    assert (target / "patients.db").read_text(encoding="utf-8") == "db"
    assert (target / "settings.json").exists()
    assert (target / "backup" / "old.db").exists()
    assert (target / "attachments" / "a.txt").exists()
    assert (target / ".migrated").exists()

    # a second run must not overwrite existing data
    (legacy / "patients.db").write_text("changed", encoding="utf-8")
    paths.migrate_legacy_data(str(legacy))
    assert (target / "patients.db").read_text(encoding="utf-8") == "db"


def test_migrate_legacy_data_ignores_missing_source(monkeypatch, tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    monkeypatch.setattr(paths, "app_data_dir", lambda: str(target))
    paths.migrate_legacy_data(str(tmp_path / "does-not-exist"))
    assert not (target / ".migrated").exists()


def test_single_instance_acquire_release(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "app_data_dir", lambda: str(tmp_path))
    manager = paths.SingleInstanceManager("TestLock")
    assert manager.acquire() is True
    assert os.path.exists(manager.lock_path)

    # a second manager sees the live pid and refuses the lock
    other = paths.SingleInstanceManager("TestLock")
    assert other.acquire() is False

    manager.release()
    assert not os.path.exists(manager.lock_path)
    assert manager.acquired is False

    # after release the lock can be acquired again
    assert other.acquire() is True
    other.release()


def test_single_instance_removes_stale_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "app_data_dir", lambda: str(tmp_path))
    manager = paths.SingleInstanceManager("StaleLock")
    with open(manager.lock_path, "w", encoding="utf-8") as fh:
        fh.write("999999")
    assert manager.acquire() is True
    manager.release()


def test_single_instance_fails_open(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "app_data_dir", lambda: str(tmp_path))

    def _boom(*args, **kwargs):
        raise RuntimeError("no filesystem")

    monkeypatch.setattr(paths.os, "open", _boom)
    manager = paths.SingleInstanceManager("BrokenLock")
    assert manager.acquire() is True


def test_pid_alive_checks_current_and_missing_process():
    assert paths._pid_alive(os.getpid()) is True
    assert paths._pid_alive(999999) is False

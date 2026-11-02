"""The app may prune its own automatic backups, but never safety copies."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main


def _make_file(path, age_seconds):
    with open(path, "wb") as fh:
        fh.write(b"x")
    stamp = time.time() - age_seconds
    os.utime(path, (stamp, stamp))


def test_prune_removes_only_old_app_backups(tmp_path):
    for i in range(5):
        _make_file(tmp_path / ("patients_%d.db" % i), 1000 - i)
    _make_file(tmp_path / "pre_migration_old.db", 9999)
    _make_file(tmp_path / "pre_purge_old.db", 9999)
    _make_file(tmp_path / "notes.txt", 9999)

    main._prune_auto_backups(str(tmp_path), keep=2)

    left = sorted(os.listdir(tmp_path))
    assert "pre_migration_old.db" in left
    assert "pre_purge_old.db" in left
    assert "notes.txt" in left
    patients = [name for name in left if name.startswith("patients_")]
    assert sorted(patients) == ["patients_3.db", "patients_4.db"]

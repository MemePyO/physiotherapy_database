"""Release-hardening checks: headless startup validation and packaging."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(args, env, timeout=180):
    return subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def test_source_self_test_writes_successful_report(tmp_path):
    report = tmp_path / "self_test.json"
    env = os.environ.copy()
    env["PHYSIO_DATA_DIR"] = str(tmp_path / "data")

    completed = _run(
        [sys.executable, "-X", "utf8", "main.py", "--self-test", "--self-test-report", str(report)],
        env,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert report.is_file()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    names = {check["name"] for check in payload["checks"]}
    assert {"Database init", "Schema version", "App assets", "Backup folder"} <= names


def test_run_startup_checks_is_headless_and_passes(fresh_db, tmp_path, monkeypatch):
    import main

    monkeypatch.setenv("PHYSIO_DATA_DIR", str(tmp_path / "data"))
    results = main.run_startup_checks()

    names = {name for name, _ok, _detail in results}
    assert {
        "Database integrity",
        "Schema version",
        "Patients loaded",
        "Settings",
        "App assets",
        "Backup folder",
        "Free disk",
    } <= names
    assert all(ok for _name, ok, _detail in results), results


def test_verify_release_rejects_missing_executable(tmp_path):
    completed = _run(
        [
            sys.executable,
            "-X",
            "utf8",
            "scripts/verify_release.py",
            "--exe",
            str(tmp_path / "missing.exe"),
        ],
        os.environ.copy(),
    )

    assert completed.returncode != 0
    assert "not found" in completed.stdout.lower()

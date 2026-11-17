"""Validate a packaged PhysioDatabase build by running its startup self-test.

Usage::

    python scripts/verify_release.py --exe dist/PhysioDatabase.exe

The executable is launched with ``--self-test`` and a JSON report path.  The
script fails when the executable is missing, does not exit, reports failed
startup checks, or returns a non-zero exit code.  It is used by CI and can be
run locally after ``pyinstaller PhysioDatabase.spec``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _default_exe() -> Path:
    name = "PhysioDatabase.exe" if os.name == "nt" else "PhysioDatabase"
    return Path("dist") / name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", default=str(_default_exe()), help="packaged executable to verify")
    parser.add_argument("--report", default=None, help="where the self-test JSON report is written")
    parser.add_argument("--data-dir", default=None, help="temporary PHYSIO_DATA_DIR for the run")
    parser.add_argument("--timeout", type=float, default=120.0, help="startup timeout in seconds")
    parser.add_argument(
        "--min-size-mb",
        type=float,
        default=1.0,
        help="reject executables smaller than this size (default: 1 MB)",
    )
    args = parser.parse_args(argv)

    exe = Path(args.exe).resolve()
    if not exe.is_file():
        print(f"FAIL: packaged executable not found: {exe}")
        return 2

    size_mb = exe.stat().st_size / (1024.0 * 1024.0)
    if size_mb < args.min_size_mb:
        print(f"FAIL: {exe} is only {size_mb:.2f} MB (expected >= {args.min_size_mb} MB)")
        return 2

    scratch = Path(tempfile.mkdtemp(prefix="physio-release-"))
    report = Path(args.report).resolve() if args.report else scratch / "self_test.json"
    data_dir = Path(args.data_dir).resolve() if args.data_dir else scratch / "data"
    report.parent.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PHYSIO_DATA_DIR"] = str(data_dir)
    command = [str(exe), "--self-test", "--self-test-report", str(report)]

    print(f"Running packaged startup self-test: {exe}")
    try:
        completed = subprocess.run(
            command,
            timeout=args.timeout,
            env=env,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        print(f"FAIL: executable did not finish within {args.timeout:.0f}s")
        return 3
    except OSError as exc:
        print(f"FAIL: could not start executable: {exc}")
        return 3

    if not report.is_file():
        print(f"FAIL: no self-test report written to {report}")
        if completed.stdout.strip():
            print("stdout:\n" + completed.stdout)
        if completed.stderr.strip():
            print("stderr:\n" + completed.stderr)
        return 4

    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"FAIL: invalid self-test report: {exc}")
        return 4

    checks = payload.get("checks", [])
    for check in checks:
        marker = "ok" if check.get("ok") else "FAIL"
        print(f"  [{marker}] {check.get('name')}: {check.get('detail')}")

    ok = bool(payload.get("ok")) and completed.returncode == 0
    if not ok:
        print(
            f"FAIL: self-test did not pass (exit={completed.returncode}, "
            f"report_ok={payload.get('ok')})"
        )
        return 1

    print(f"PASS: packaged application started (version {payload.get('version')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

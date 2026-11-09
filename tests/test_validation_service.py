"""Tests for services/validation_service.py."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.validation_service import (
    validate_patient, validate_session, validate_vas, validate_time,
)


def test_validate_patient_valid():
    r = validate_patient("Ion Popescu", "01.02.1990", "M", "Cluj")
    assert r.ok()
    assert r.errors == {}


def test_validate_patient_empty_name():
    r = validate_patient("")
    assert not r.ok()
    assert "name" in r.errors


def test_validate_patient_invalid_dob():
    r = validate_patient("Ana", "not-a-date")
    assert not r.ok()
    assert "dob" in r.errors


def test_validate_patient_invalid_sex():
    r = validate_patient("Ana", sex="X")
    assert not r.ok()
    assert "sex" in r.errors


def test_validate_session_valid():
    r = validate_session("01.02.2026", 30, 5, 3)
    assert r.ok()


def test_validate_session_invalid_date():
    r = validate_session("bad")
    assert not r.ok()
    assert "date" in r.errors


def test_validate_session_invalid_duration():
    r = validate_session("01.02.2026", "abc")
    assert not r.ok()
    assert "duration" in r.errors

    r2 = validate_session("01.02.2026", 0)
    assert not r2.ok()
    assert "duration" in r2.errors


def test_validate_session_invalid_vas():
    r = validate_session("01.02.2026", 30, 11, 3)
    assert not r.ok()
    assert "pain_before" in r.errors

    r2 = validate_session("01.02.2026", 30, 5, "x")
    assert not r2.ok()
    assert "pain_after" in r2.errors


def test_validate_vas_valid():
    r = validate_vas(7.5)
    assert r.ok()


def test_validate_vas_invalid():
    r = validate_vas(11)
    assert not r.ok()
    assert "value" in r.errors

    r2 = validate_vas("abc")
    assert not r2.ok()
    assert "value" in r2.errors


def test_validate_time_valid():
    r = validate_time("14:30")
    assert r.ok()


def test_validate_time_invalid():
    r = validate_time("25:00")
    assert not r.ok()
    assert "time" in r.errors

    r2 = validate_time("abc")
    assert not r2.ok()
    assert "time" in r2.errors

    r3 = validate_time("14.30")
    assert r3.ok()  # dots accepted
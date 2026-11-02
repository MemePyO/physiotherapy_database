import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
import main


def _fresh_app(monkeypatch, tmp_path):
    d = tempfile.mkdtemp()
    dbfile = os.path.join(d, "test.db")
    monkeypatch.setattr(db, "db_path", lambda: dbfile)
    db.init_db()
    db.add_patient("Ana", "Cluj")
    monkeypatch.setattr(main, "load_settings", lambda: {"ui_theme": "classic", "appearance": "Light", "ui_scale": 1.0})
    main.theme.set_theme("classic")
    main.theme.set_appearance("Light")
    app = main.App()
    app.update()
    return app


def test_live_theme_switch(monkeypatch, tmp_path):
    app = _fresh_app(monkeypatch, tmp_path)
    assert main.theme.active() == "classic"
    app._apply_ui_theme("medidash")
    app.update()
    assert main.theme.active() == "medidash"
    assert main.theme.layout() == "stacked"
    # patient file opens in stacked mode
    pid = db.get_all_patients()[0]["id"]
    app._open_patient_by_id(pid)
    app.update()
    panel = app.patient_panels[pid]
    assert panel.tabview is not None
    assert hasattr(panel, "sections_frame")
    assert hasattr(panel, "plan_entries")
    app._apply_ui_theme("classic")
    app.update()
    assert main.theme.active() == "classic"
    app.destroy()
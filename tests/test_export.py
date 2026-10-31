import sys, os, tempfile, tkinter.filedialog as fd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


def _setup_db(monkeypatch, tmp_path):
    d = tempfile.mkdtemp()
    dbfile = os.path.join(d, "test.db")
    monkeypatch.setattr(db, "db_path", lambda: dbfile)
    db.init_db()
    pid = db.add_patient("Ion Popescu", "Cluj", sex="M", dob="01.02.1990")
    db.update_patient(pid, diagnostic="diag", objective="obj", evaluation="eva", observation="obs")
    return dbfile


def test_export_csv_creates_file(monkeypatch, tmp_path):
    _setup_db(monkeypatch, tmp_path)
    import main
    main.theme.set_theme("classic")
    app = main.App()
    app.update()
    out = str(tmp_path / "out.csv")
    monkeypatch.setattr(fd, "asksaveasfilename", lambda **kw: out)
    app._export_csv()
    app.destroy()
    assert os.path.exists(out) and os.path.getsize(out) > 0


def test_export_excel_creates_file(monkeypatch, tmp_path):
    _setup_db(monkeypatch, tmp_path)
    import main

    class _StubDlg:
        def __init__(self, *a, **k):
            self.result = ["name", "localitate"]

    monkeypatch.setattr(main, "ExportFieldsDialog", _StubDlg)
    monkeypatch.setattr(main.App, "wait_window", lambda self, w: None)
    main.theme.set_theme("classic")
    app = main.App()
    app.update()
    out = str(tmp_path / "out.xlsx")
    monkeypatch.setattr(fd, "asksaveasfilename", lambda **kw: out)
    app._export_excel()
    app.destroy()
    assert os.path.exists(out)


def test_export_pdf_creates_file(monkeypatch, tmp_path):
    _setup_db(monkeypatch, tmp_path)
    import main
    main.theme.set_theme("classic")
    app = main.App()
    app.update()
    out = str(tmp_path / "out.pdf")
    monkeypatch.setattr(fd, "asksaveasfilename", lambda **kw: out)
    app._export_pdf()
    app.destroy()
    assert os.path.exists(out)


def test_export_word_creates_file(monkeypatch, tmp_path):
    _setup_db(monkeypatch, tmp_path)
    import main
    main.theme.set_theme("classic")
    app = main.App()
    app.update()
    out = str(tmp_path / "out.doc")
    monkeypatch.setattr(fd, "asksaveasfilename", lambda **kw: out)
    app._export_word()
    app.destroy()
    assert os.path.exists(out)
"""Themed ttk style checks."""

import theme
from ui import ttk_style


def test_apply_styles_treeview_and_scrollbar(app):
    style = ttk_style.apply(app)
    assert style.lookup("Treeview", "background") == theme.PANEL
    assert style.lookup("Treeview", "fieldbackground") == theme.PANEL
    assert style.lookup("Treeview", "foreground") == theme.TEXT
    assert int(style.lookup("Treeview", "rowheight")) == theme.TABLE_ROW_H
    assert style.lookup("Treeview.Heading", "background") == theme.BG
    assert style.lookup("Treeview.Heading", "foreground") == theme.TEXT
    assert style.lookup("TScrollbar", "troughcolor") == theme.BG
    assert ("selected", theme.SELECTED) in style.map("Treeview", "background")


def test_apply_is_idempotent(app):
    first = ttk_style.apply(app)
    options = ("background", "foreground", "fieldbackground", "rowheight")
    before = {option: first.lookup("Treeview", option) for option in options}
    second = ttk_style.apply(app)
    after = {option: second.lookup("Treeview", option) for option in options}
    assert before == after


def test_treeviews_use_default_styled_class(patient_app):
    app, pid = patient_app
    app._open_patient_by_id(pid)
    app.update()
    panel = app.patient_panels[pid]
    trees = [
        panel.ses_tree,
        panel.hep_tree,
        panel.out_tree,
        panel.attach_tree,
        panel.hist_tree,
    ]
    for tree in trees:
        assert tree.cget("style") in ("", "Treeview")
    style = ttk_style.apply(app)
    assert style.lookup("Treeview", "rowheight")

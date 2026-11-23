"""Tests for scale tracking, geometry clamping and ttk scaling."""

import main
from ui import ttk_style


def test_clamp_geometry_leaves_valid_geometry_alone():
    assert main._clamp_geometry("1200x800+100+100", 1920, 1080) == "1200x800+100+100"


def test_clamp_geometry_limits_size_to_screen():
    assert main._clamp_geometry("2000x1500+100+100", 1920, 1080) == "1920x1080+100+100"


def test_clamp_geometry_pulls_window_back_on_screen():
    assert main._clamp_geometry("1200x800+3000+100", 1920, 1080) == "1200x800+1800+100"
    assert main._clamp_geometry("1200x800-1400+100", 1920, 1080) == "1200x800-1080+100"


def test_clamp_geometry_handles_missing_position_and_garbage():
    assert main._clamp_geometry("1200x800", 1920, 1080) == "1200x800"
    assert main._clamp_geometry("garbage", 1920, 1080) == "garbage"
    assert main._clamp_geometry("", 1920, 1080) == ""


def test_scaled_font_multiplies_size():
    assert ttk_style.scaled_font(("Segoe UI", 11, "bold"), 1.5) == ("Segoe UI", 17, "bold")
    assert ttk_style.scaled_font(("Segoe UI", 11), 1.0) == ("Segoe UI", 11)


def test_ttk_row_height_follows_scale(app):
    ttk_style.apply(app, scale=1.5)
    style = ttk_style.ttk.Style(master=app)
    assert int(style.lookup(ttk_style.TREEVIEW_STYLE, "rowheight")) == int(
        main.theme.TABLE_ROW_H * 1.5 + 0.5
    )
    ttk_style.apply(app, scale=1.0)


def test_ui_scale_is_tracked_and_zoomed(app):
    assert app.current_ui_scale() == 1.0
    app._zoom(1)
    app.update()
    assert app.current_ui_scale() == 1.25
    app._zoom(1)
    app.update()
    assert app.current_ui_scale() == 1.5
    app._zoom(1)
    app.update()
    assert app.current_ui_scale() == 1.5
    app._zoom_reset()
    app.update()
    assert app.current_ui_scale() == 1.0

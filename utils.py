"""Shared helper utilities for the patient database app."""
import os
import re
import unicodedata


def _strip_inline_formatting(text):
    """Return text with **bold** / *italic* markers removed (plain display)."""
    if not text:
        return text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text
def _apply_inline_formatting(widget):
    """Render **bold** and *italic* markdown inline in a CTkTextbox."""
    try:
        tb = getattr(widget, "_textbox", None)
        if tb is None:
            return
    except Exception:
        return

    try:
        import tkinter.font as _tkfont
        base = tb.cget("font")
        f = _tkfont.Font(font=base)
        bold_font = f.copy()
        bold_font.configure(weight="bold")
        italic_font = f.copy()
        italic_font.configure(slant="italic")
        tb.tag_configure("md_bold", font=bold_font)
        tb.tag_configure("md_italic", font=italic_font)
        tb.tag_configure("md_marker", elide=True)
    except Exception:
        pass

    try:
        content = tb.get("1.0", "end-1c")
    except Exception:
        return

    for tag in ("md_bold", "md_italic", "md_marker"):
        try:
            tb.tag_remove(tag, "1.0", "end")
        except Exception:
            pass

    # preserve cursor / selection
    try:
        insert_idx = tb.index("insert")
    except Exception:
        insert_idx = None
    try:
        sel = (tb.index("sel.first"), tb.index("sel.last")) if tb.tag_ranges("sel") else None
    except Exception:
        sel = None

    pattern = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*")
    for m in pattern.finditer(content):
        start = m.start()
        end = m.end()
        if m.group(1) is not None:
            inner_s, inner_e = start + 2, end - 2
            try:
                tb.tag_add("md_bold", "1.0 + %d chars" % inner_s, "1.0 + %d chars" % inner_e)
                tb.tag_add("md_marker", "1.0 + %d chars" % start, "1.0 + %d chars" % (start + 2))
                tb.tag_add("md_marker", "1.0 + %d chars" % (end - 2), "1.0 + %d chars" % end)
            except Exception:
                pass
        else:
            inner_s, inner_e = start + 1, end - 1
            try:
                tb.tag_add("md_italic", "1.0 + %d chars" % inner_s, "1.0 + %d chars" % inner_e)
                tb.tag_add("md_marker", "1.0 + %d chars" % start, "1.0 + %d chars" % (start + 1))
                tb.tag_add("md_marker", "1.0 + %d chars" % (end - 1), "1.0 + %d chars" % end)
            except Exception:
                pass

    try:
        if insert_idx:
            tb.mark_set("insert", insert_idx)
        if sel:
            tb.tag_add("sel", sel[0], sel[1])
    except Exception:
        pass


def _patch_scrollable(sf):
    """Make a CTkScrollableFrame's internal Configure binding safe (no crash on missing event)."""
    def _handler(e=None):
        try:
            canvas = getattr(sf, "_parent_canvas", None)
            if canvas is None:
                return
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
        except Exception:
            pass
    try:
        sf.bind("<Configure>", _handler)
    except Exception:
        pass


def _exists(widget):
    """Safe winfo_exists that never raises on destroyed widgets."""
    try:
        return bool(widget is not None and widget.winfo_exists())
    except Exception:
        return False


def _safe_destroy(widget):
    """Destroy a widget without raising if it (or a child) is already gone."""
    try:
        if _exists(widget):
            widget.destroy()
    except Exception:
        pass


def _safe_configure(widget, **kwargs):
    """Configure a widget without raising if it is already destroyed."""
    try:
        if _exists(widget):
            widget.configure(**kwargs)
    except Exception:
        pass


def _safe_after(widget, ms, callback):
    """Schedule a callback without crashing if the widget is destroyed meanwhile."""
    def _wrapped():
        try:
            if _exists(widget):
                callback()
        except Exception:
            pass
    try:
        return widget.after(ms, _wrapped)
    except Exception:
        return None


def _safe_format(textbox):
    """Apply inline formatting without raising if the widget is gone."""
    try:
        if _exists(textbox):
            _apply_inline_formatting(textbox)
    except Exception:
        pass


def _norm(s):
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _initials(name):
    parts = (name or "").split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][:1] + parts[-1][:1]).upper()


def _validate_dob(text):
    text = (text or "").strip()
    if not text:
        return True
    try:
        import datetime
        datetime.datetime.strptime(text, "%d.%m.%Y")
        return True
    except ValueError:
        return False


def _rtf_escape(text):
    text = str(text)
    text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return text


def _make_simple_pdf(text):
    lines = text.split("\n")
    def esc(t):
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content_lines = ["BT", "/F1 10 Tf", "50 780 Td", "12 TL"]
    for ln in lines:
        content_lines.append("(" + esc(ln[:110]) + ") Tj T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", "replace")
    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n")
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(b"5 0 obj\n<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n")
    out = b"%PDF-1.4\n"
    offsets = []
    for o in objects:
        offsets.append(len(out))
        out += o
    xref_pos = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += b"trailer\n<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
    return out

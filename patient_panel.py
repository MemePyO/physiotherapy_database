"""Embedded patient file panel (dashboard style) with tabbed sections."""
import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog

import customtkinter as ctk

import db
import lang
import theme
import log
import utils
logger = log.get_logger(__name__)


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


def _attach_tooltip(widget, text, owner=None):
    """Show a small in-window tooltip while the mouse hovers over the widget."""
    from tooltip import attach_tooltip
    attach_tooltip(widget, text)


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


class PatientFilePanel(ctk.CTkFrame):
    def __init__(self, master, patient_id, on_close=None, new=False):
        super().__init__(master, fg_color=theme.PANEL, corner_radius=theme.PANEL_RADIUS)
        self.patient_id = None if new else patient_id
        self.on_close_callback = on_close
        self._dirty = False
        self._is_new = bool(new) or (patient_id is None)
        self.header_frame = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        if self._is_new:
            self.patient = {"name": "", "patient_code": "", "dob": "", "sex": "", "localitate": "",
                            "diagnostic": "", "objective": "", "evaluation": "", "observation": "",
                            "updated_at": ""}
        else:
            self.patient = db.get_patient(patient_id=patient_id)
            if not self.patient:
                self.destroy()
                return

        self._build_header()
        self._build_tabs()
        self._build_footer()
        self._schedule_autosave()
        if not self._is_new and theme.layout() != "stacked":
            self._load_attachments()
            self._load_history()

    # ---- header ----
    def _build_header(self):
        if not hasattr(self, "header_frame") or self.header_frame is None:
            self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.header_frame.grid(row=0, column=0, sticky="ew")
        for w in self.header_frame.winfo_children():
            w.destroy()
        frame = self.header_frame
        pad = theme.PANE_PAD if theme.layout() == "stacked" else theme.PADDING
        frame.grid(row=0, column=0, sticky="ew", padx=pad, pady=(pad, 8))
        frame.grid_columnconfigure(1, weight=1)

        av = ctk.CTkLabel(frame, text=_initials(self.patient.get('name', '') or '?'), width=theme.AVATAR_SIZE,
                          height=theme.AVATAR_SIZE, corner_radius=theme.AVATAR_SIZE // 2,
                          fg_color=theme.ACCENT, text_color="white",
                          font=ctk.CTkFont(size=14, weight="bold"))
        av.grid(row=0, column=0, rowspan=4, padx=(0, 12))

        if getattr(self, "_is_new", False):
            # inline editable header
            self.name_entry = ctk.CTkEntry(frame, placeholder_text="Patient name (required)", font=ctk.CTkFont(size=16, weight="bold"))
            self.name_entry.grid(row=0, column=1, sticky="ew", pady=(0, 2))
            self.name_entry.insert(0, self.patient.get('name', '') or '')

            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.grid(row=1, column=1, sticky="ew", pady=(0, 2))
            ctk.CTkLabel(row, text="Code:", font=theme.FONT_SMALL, text_color=theme.MUTED).pack(side="left")
            self.code_label = ctk.CTkLabel(row, text="auto", font=theme.FONT_SMALL, text_color=theme.MUTED)
            self.code_label.pack(side="left", padx=(4, 12))
            ctk.CTkLabel(row, text="DOB (DD.MM.YYYY):", font=theme.FONT_SMALL, text_color=theme.MUTED).pack(side="left")
            self.dob_entry = ctk.CTkEntry(row, width=110, placeholder_text="DD.MM.YYYY")
            self.dob_entry.pack(side="left", padx=(4, 12))
            self.dob_entry.insert(0, self.patient.get('dob', '') or '')
            ctk.CTkLabel(row, text="Sex:", font=theme.FONT_SMALL, text_color=theme.MUTED).pack(side="left")
            self.sex_menu = ctk.CTkOptionMenu(row, values=["", "M", "F"], width=70)
            self.sex_menu.pack(side="left", padx=(4, 12))
            self.sex_menu.set(self.patient.get('sex', '') or "")

            loc_row = ctk.CTkFrame(frame, fg_color="transparent")
            loc_row.grid(row=2, column=1, sticky="ew", pady=(0, 2))
            ctk.CTkLabel(loc_row, text="Locality:", font=theme.FONT_SMALL, text_color=theme.MUTED).pack(side="left")
            self.loc_entry = ctk.CTkEntry(loc_row, placeholder_text="Locality")
            self.loc_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
            self.loc_entry.insert(0, self.patient.get('localitate', '') or '')

            diag = self.patient.get('diagnostic', '') or ''
            first_line = diag.split(chr(10))[0].strip() if diag else ''
            main_diag = utils._strip_inline_formatting(first_line) if first_line else 'NA'
            diag_lbl = ctk.CTkLabel(frame, text="Diagnostic: " + main_diag, font=theme.FONT_BOLD, text_color=theme.ACCENT)
            diag_lbl.grid(row=3, column=1, sticky="w")
            self.diag_header_label = diag_lbl

            self.modified_label = ctk.CTkLabel(frame, text="Not saved yet", font=theme.FONT_SMALL, text_color=theme.MUTED)
            self.modified_label.grid(row=4, column=1, sticky="w", pady=(2, 0))

            btns = ctk.CTkFrame(frame, fg_color="transparent")
            btns.grid(row=0, column=2, rowspan=5, sticky="ne")
            ctk.CTkButton(btns, text="Cancel", width=70, fg_color="#6b7280", hover_color="#4b5563",
                          command=self._cancel_new).pack(side="top", padx=2, pady=2)
            return

        # existing patient header (unchanged)
        name_lbl = ctk.CTkLabel(frame, text=self.patient['name'], font=ctk.CTkFont(size=16, weight="bold"),
                                text_color=theme.TEXT)
        name_lbl.grid(row=0, column=1, sticky="w")
        self.name_label = name_lbl

        dob = self.patient.get('dob', '') or 'NA'
        sex = self.patient.get('sex', '') or 'NA'
        loc = self.patient.get('localitate', '') or 'NA'
        code = self.patient.get('patient_code', '') or 'NA'
        info_text = f"Code: {code}   |   DOB: {dob}   |   Sex: {sex}   |   Locality: {loc}"
        info_lbl = ctk.CTkLabel(frame, text=info_text, font=theme.FONT_SUB, text_color=theme.MUTED)
        info_lbl.grid(row=1, column=1, sticky="w")
        self.info_label = info_lbl

        diag = self.patient.get('diagnostic', '') or ''
        first_line = diag.split(chr(10))[0].strip() if diag else ''
        main_diag = utils._strip_inline_formatting(first_line) if first_line else 'NA'
        diag_lbl = ctk.CTkLabel(frame, text="Diagnostic: " + main_diag, font=theme.FONT_BOLD, text_color=theme.ACCENT)
        diag_lbl.grid(row=2, column=1, sticky="w")
        self.diag_header_label = diag_lbl

        self.modified_label = ctk.CTkLabel(frame, text="Last modified: " + (self.patient.get('updated_at') or 'NA'),
                                          font=theme.FONT_SMALL, text_color=theme.MUTED)
        self.modified_label.grid(row=3, column=1, sticky="w", pady=(2, 0))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.grid(row=0, column=2, rowspan=4, sticky="e")
        ctk.CTkButton(btns, text="Edit", width=70, fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK,
                      command=self._edit_patient_info).pack(side="left", padx=2)

    def _refresh_header_info(self):
        if getattr(self, "_is_new", False):
            # update diag label from textbox content
            try:
                txt = getattr(self, "diagnostic_text", None)
                if txt is not None:
                    val = txt.get("1.0", "end-1c").split(chr(10))[0].strip()
                    self.diag_header_label.configure(text="Diagnostic: " + (utils._strip_inline_formatting(val) if val else "NA"))
            except Exception:
                pass
            return
        code = self.patient.get('patient_code', '') or 'NA'
        dob = self.patient.get('dob', '') or 'NA'
        sex = self.patient.get('sex', '') or 'NA'
        loc = self.patient.get('localitate', '') or 'NA'
        try:
            self.info_label.configure(text=f"Code: {code}   |   DOB: {dob}   |   Sex: {sex}   |   Locality: {loc}")
        except Exception:
            pass
        diag = self.patient.get('diagnostic', '') or ''
        first_line = diag.split(chr(10))[0].strip() if diag else ''
        main_diag = utils._strip_inline_formatting(first_line) if first_line else 'NA'
        try:
            self.diag_header_label.configure(text="Diagnostic: " + main_diag)
        except Exception:
            pass

    # ---- tabs ----
    def _build_tabs(self):
        if theme.layout() == "stacked":
            self._build_stacked()
            return
        self.tabview = ctk.CTkTabview(self, fg_color=theme.PANEL)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=theme.PADDING, pady=(0, 8))

        sections = [("diagnostic", "Diagnostic", theme.SEC_DIAG),
                    ("objective", "Obiectiv", theme.SEC_OBJ),
                    ("evaluation", "Evaluare", theme.SEC_EVAL),
                    ("observation", "Observa\u021bie", theme.SEC_OBS)]
        self.texts = {}
        self.count_labels = {}
        for field, title, color in sections:
            tab = self.tabview.add(title)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(1, weight=1)
            tb = ctk.CTkFrame(tab, fg_color="transparent")
            tb.grid(row=0, column=0, sticky="ew", pady=(4, 4))
            tooltips = {
                "bold": "Bold: wrap the selection in ** **",
                "italic": "Italic: wrap the selection in * *",
                "bullet": "Insert a bullet (\u2022) at the start of the current line",
                "number": "Insert a numbered item (1.) at the start of the current line",
            }
            for label, cmd_prefix in [("B", "bold"), ("I", "italic"), ("\u2022", "bullet"), ("1.", "number")]:
                b = ctk.CTkButton(tb, text=label, width=34, height=26, fg_color=theme.ACCENT,
                                  hover_color=theme.ACCENT_DARK, font=theme.FONT_BOLD,
                                  command=lambda p=cmd_prefix, f=field: self._toolbar_action(f, p))
                b.pack(side="left", padx=2)
                _attach_tooltip(b, tooltips[cmd_prefix])
            cnt = ctk.CTkLabel(tb, text="", text_color=theme.MUTED, font=theme.FONT_SMALL)
            cnt.pack(side="right", padx=6)
            self.count_labels[field] = cnt

            txt = ctk.CTkTextbox(tab, corner_radius=0, border_width=1, border_color=theme.BORDER,
                                 fg_color=theme.PANEL, text_color=theme.TEXT, font=theme.FONT_BODY)
            txt.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
            val = self.patient.get(field, '') or ''
            txt.insert("1.0", val)
            utils._apply_inline_formatting(txt)
            txt.bind("<KeyRelease>", lambda e, f=field, t=txt: (self._on_text_change(f, t), self.mark_dirty(),
                                                               self._schedule_format(t)))
            setattr(self, field + "_text", txt)
            self._update_count(field, txt)
            self.texts[field] = txt

        # Attachments tab
        att_tab = self.tabview.add("Attachments")
        att_tab.grid_columnconfigure(0, weight=1)
        att_tab.grid_rowconfigure(0, weight=1)
        cols = ("filename", "size", "added_at")
        self.attach_tree = ttk.Treeview(att_tab, columns=cols, show="headings", selectmode="browse")
        self.attach_tree.heading("filename", text="File")
        self.attach_tree.heading("size", text="Size")
        self.attach_tree.heading("added_at", text="Added")
        self.attach_tree.column("filename", width=200)
        self.attach_tree.column("size", width=70)
        self.attach_tree.column("added_at", width=120)
        self.attach_tree.grid(row=0, column=0, sticky="nsew", pady=(4, 4))
        ab = ctk.CTkFrame(att_tab, fg_color="transparent")
        ab.grid(row=1, column=0, sticky="ew", pady=(4, 4))
        ctk.CTkButton(ab, text="Attach file", width=100, fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK,
                      command=self._attach_file).pack(side="left", padx=2)
        ctk.CTkButton(ab, text="Open", width=80, command=self._open_attachment).pack(side="left", padx=2)
        ctk.CTkButton(ab, text="Delete", width=80, fg_color="#c0392b", command=self._delete_attachment).pack(side="left", padx=2)
        ctk.CTkButton(ab, text="Refresh", width=80, command=self._load_attachments).pack(side="left", padx=2)

        # History tab
        hist_tab = self.tabview.add("History")
        hist_tab.grid_columnconfigure(0, weight=1)
        hist_tab.grid_rowconfigure(0, weight=1)
        hcols = ("changed_at", "field", "old_value", "new_value")
        self.hist_tree = ttk.Treeview(hist_tab, columns=hcols, show="headings", selectmode="browse")
        self.hist_tree.heading("changed_at", text="When")
        self.hist_tree.heading("field", text="Field")
        self.hist_tree.heading("old_value", text="Old")
        self.hist_tree.heading("new_value", text="New")
        self.hist_tree.column("changed_at", width=120)
        self.hist_tree.column("field", width=90)
        self.hist_tree.column("old_value", width=160)
        self.hist_tree.column("new_value", width=160)
        self.hist_tree.grid(row=0, column=0, sticky="nsew", pady=(4, 4))
        hb = ctk.CTkFrame(hist_tab, fg_color="transparent")
        hb.grid(row=1, column=0, sticky="ew", pady=(4, 4))
        ctk.CTkButton(hb, text="Refresh", width=80, command=self._load_history).pack(side="left", padx=2)
        ctk.CTkButton(hb, text="Clear history", width=100, fg_color="#c0392b",
                      hover_color="#a93226", command=self._clear_history).pack(side="left", padx=2)

    def _build_stacked(self):
        self.tabview = None
        self.sections_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.sections_frame.grid(row=1, column=0, sticky="nsew", padx=theme.PANE_PAD, pady=(0, 8))
        self.sections_frame.grid_columnconfigure(0, weight=1)

        sections = [("diagnostic", "Diagnostic", theme.HEAD_DIAG, "#ffffff"),
                    ("objective", "Obiectiv", theme.HEAD_OBJ, theme.TEXT),
                    ("evaluation", "Evaluare", theme.HEAD_EVAL, "#ffffff"),
                    ("observation", "Observa\u021bie", theme.HEAD_OBS, "#ffffff")]
        self.texts = {}
        self.count_labels = {}
        tooltips = {
            "bold": "Bold: wrap the selection in ** **",
            "italic": "Italic: wrap the selection in * *",
            "bullet": "Insert a bullet (\u2022) at the start of the current line",
            "number": "Insert a numbered item (1.) at the start of the current line",
        }
        for field, title, head_color, text_color in sections:
            card = ctk.CTkFrame(self.sections_frame, fg_color=theme.PANEL, corner_radius=theme.CARD_RADIUS,
                                border_width=1, border_color=theme.BORDER)
            card.pack(fill="x", pady=(0, 12))
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(1, weight=1)

            head = ctk.CTkFrame(card, fg_color=head_color, corner_radius=0, height=30)
            head.grid(row=0, column=0, sticky="ew")
            head.grid_propagate(False)
            head.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(head, text=title, font=theme.FONT_BOLD, text_color=text_color).grid(
                row=0, column=0, sticky="w", padx=12)
            tb = ctk.CTkFrame(head, fg_color="transparent")
            tb.grid(row=0, column=1, sticky="e", padx=8)
            for label, cmd_prefix in [("B", "bold"), ("I", "italic"), ("\u2022", "bullet"), ("1.", "number")]:
                b = ctk.CTkButton(tb, text=label, width=26, height=22, fg_color="transparent",
                                  text_color=text_color, hover_color=theme.ACCENT_LIGHT, font=theme.FONT_BOLD,
                                  command=lambda p=cmd_prefix, f=field: self._toolbar_action(f, p))
                b.pack(side="left", padx=1)
                _attach_tooltip(b, tooltips[cmd_prefix])
            cnt = ctk.CTkLabel(tb, text="", text_color=text_color, font=theme.FONT_SMALL)
            cnt.pack(side="left", padx=6)
            self.count_labels[field] = cnt

            txt = ctk.CTkTextbox(card, corner_radius=0, border_width=0, fg_color=theme.PANEL,
                                 text_color=theme.TEXT, font=theme.FONT_BODY, height=110)
            txt.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
            val = self.patient.get(field, '') or ''
            txt.insert("1.0", val)
            utils._apply_inline_formatting(txt)
            txt.bind("<KeyRelease>", lambda e, f=field, t=txt: (self._on_text_change(f, t), self.mark_dirty(),
                                                               self._schedule_format(t)))
            setattr(self, field + "_text", txt)
            self._update_count(field, txt)
            self.texts[field] = txt

    def _toolbar_action(self, field, action):
        txt = getattr(self, field + "_text")
        try:
            if action == "bold":
                try:
                    sel = txt.get("sel.first", "sel.last")
                    txt.delete("sel.first", "sel.last")
                    txt.insert("insert", "**" + sel + "**")
                except tk.TclError:
                    txt.insert("insert", "****")
                    txt.mark_set("insert", "insert-2c")
            elif action == "italic":
                try:
                    sel = txt.get("sel.first", "sel.last")
                    txt.delete("sel.first", "sel.last")
                    txt.insert("insert", "*" + sel + "*")
                except tk.TclError:
                    txt.insert("insert", "**")
                    txt.mark_set("insert", "insert-1c")
            elif action == "bullet":
                self._insert_line_prefix(txt, "\u2022 ")
            elif action == "number":
                self._insert_line_prefix(txt, "1. ")
        except Exception:
            pass
        try:
            utils._apply_inline_formatting(txt)
        except Exception:
            pass
        self.mark_dirty()

    def _insert_line_prefix(self, txt, prefix):
        try:
            idx = txt.index("insert")
            line_start = idx.split(".")[0] + ".0"
            txt.insert(line_start, prefix)
        except Exception:
            txt.insert("insert", prefix)

    def _on_text_change(self, field, txt):
        self._dirty = True
        self._update_count(field, txt)
        self._update_title_star()

    def _update_count(self, field, txt):
        try:
            content = txt.get("1.0", "end-1c")
            chars = len(content)
            lines = content.count("\n") + (1 if content.strip() else 0)
            if content == "":
                lines = 0
            self.count_labels[field].configure(text=f"{chars} ch \u00b7 {lines} ln")
        except Exception:
            pass

    def _update_title_star(self):
        pass

    # ---- footer ----
    def _build_footer(self):
        row = 2 if theme.layout() == "stacked" else 2
        pad = theme.PANE_PAD if theme.layout() == "stacked" else theme.PADDING
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=pad, pady=(0, pad))
        frame.grid_columnconfigure(0, weight=1)
        self.dirty_label = ctk.CTkLabel(frame, text="", text_color=theme.DANGER, font=theme.FONT_SMALL)
        self.dirty_label.grid(row=0, column=0, sticky="w")
        print_txt = "Print / PDF" if theme.layout() == "stacked" else "\U0001F5A8  Print / PDF"
        save_txt = "Save Patient Record" if theme.layout() == "stacked" else "\U0001F4BE  Save Patient Record"
        ctk.CTkButton(frame, text=print_txt, width=120, height=36,
                      fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK, font=theme.FONT_BOLD,
                      command=self._print_pdf).grid(row=0, column=1, sticky="e", padx=(0, 6))
        ctk.CTkButton(frame, text=save_txt, width=180, height=36,
                      fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK, font=theme.FONT_BOLD,
                      command=self._save_all).grid(row=0, column=2, sticky="e")

    # ---- save ----
    def _save_all(self, silent=False):
        # --- new patient: create row on first save ---
        if getattr(self, "_is_new", False):
            name = ""
            try:
                name = self.name_entry.get().strip()
            except Exception:
                name = ""
            if not name:
                messagebox.showerror(lang.t("app_name"), "Patient name is required.")
                return
            dob = ""
            try:
                dob = self.dob_entry.get().strip()
            except Exception:
                dob = ""
            if dob and not _validate_dob(dob):
                messagebox.showerror(lang.t("app_name"), "Invalid date (use DD.MM.YYYY).")
                return
            sex = ""
            try:
                sex = self.sex_menu.get()
            except Exception:
                sex = ""
            loc = ""
            try:
                loc = self.loc_entry.get().strip()
            except Exception:
                loc = ""
            code = ""
            try:
                code = self.code_entry.get().strip() if hasattr(self, "code_entry") else ""
            except Exception:
                code = ""
            diag = self.diagnostic_text.get("1.0", "end-1c") if hasattr(self, "diagnostic_text") else ""
            obj = self.objective_text.get("1.0", "end-1c") if hasattr(self, "objective_text") else ""
            eva = self.evaluation_text.get("1.0", "end-1c") if hasattr(self, "evaluation_text") else ""
            obs = self.observation_text.get("1.0", "end-1c") if hasattr(self, "observation_text") else ""
            try:
                pid = db.add_patient(name, loc, sex=sex, dob=dob)
                db.update_patient(pid, name=name, localitate=loc, sex=sex, dob=dob,
                                 diagnostic=diag, objective=obj, evaluation=eva, observation=obs)
                self.patient_id = pid
                self._is_new = False
                self.patient = db.get_patient(patient_id=pid)
                # rebuild header as read-only
                self._build_header()
                self._dirty = False
                if not silent:
                    self.dirty_label.configure(text="Saved")
                    self.after(2000, lambda: self.dirty_label.configure(text="") if self.winfo_exists() else None)
                    messagebox.showinfo(lang.t("app_name"), lang.t("msg_saved"))
                else:
                    self.dirty_label.configure(text="Saved")
                    self.after(2000, lambda: self.dirty_label.configure(text="") if self.winfo_exists() else None)
                self._refresh_header_info()
                if theme.layout() != "stacked":
                    self._load_attachments()
                    self._load_history()
                if self.on_close_callback:
                    self.on_close_callback()
                # update app selection
                try:
                    app = self.winfo_toplevel()
                    if hasattr(app, "patient_panels"):
                        app.patient_panels.pop(None, None)
                        app.patient_panels[pid] = self
                    if hasattr(app, "selected_patient_id"):
                        app.selected_patient_id = pid
                    if hasattr(app, "_set_selected_card"):
                        app._set_selected_card(pid)
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror(lang.t("app_name"), str(e))
            return

        try:
            if not silent:
                self.dirty_label.configure(text="Saving...")
            db.update_patient(self.patient_id,
                diagnostic=self.diagnostic_text.get("1.0", "end-1c"),
                objective=self.objective_text.get("1.0", "end-1c"),
                evaluation=self.evaluation_text.get("1.0", "end-1c"),
                observation=self.observation_text.get("1.0", "end-1c"))
            self.patient = db.get_patient(patient_id=self.patient_id)
            self._dirty = False
            if silent:
                self.dirty_label.configure(text="Auto-saved")
                self.after(2000, lambda: self.dirty_label.configure(text="") if self.winfo_exists() else None)
            else:
                self.dirty_label.configure(text="Saved")
                self.after(2000, lambda: self.dirty_label.configure(text="") if self.winfo_exists() else None)
            self._refresh_header_info()
            try:
                self.modified_label.configure(text="Last modified: " + (self.patient.get('updated_at') or ''))
            except Exception:
                pass
            if self.on_close_callback:
                self.on_close_callback()
            if not silent:
                messagebox.showinfo(lang.t("app_name"), lang.t("msg_saved"))
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _print_pdf(self):
        try:
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], title="Save patient PDF")
            if not path:
                return
            p = self.patient
            lines = []
            lines.append("Patient File")
            lines.append("=" * 60)
            lines.append("Name: " + str(p.get('name', '')))
            lines.append("Code: " + str(p.get('patient_code', '') or 'NA'))
            lines.append("DOB: " + str(p.get('dob', '') or 'NA'))
            lines.append("Sex: " + str(p.get('sex', '') or 'NA'))
            lines.append("Locality: " + str(p.get('localitate', '') or 'NA'))
            lines.append("Last modified: " + str(p.get('updated_at', '') or 'NA'))
            lines.append("")
            for fld, title in [("diagnostic", "Diagnostic"), ("objective", "Obiectiv"),
                               ("evaluation", "Evaluare"), ("observation", "Observa\u021bie")]:
                lines.append(title)
                lines.append("-" * 40)
                txt = getattr(self, fld + "_text")
                content = txt.get("1.0", "end-1c")
                for ln in (content or "").split("\n"):
                    lines.append(ln)
                lines.append("")
            atts = db.list_attachments(self.patient_id)
            if atts:
                lines.append("Attachments")
                lines.append("-" * 40)
                for a in atts:
                    lines.append("- " + str(a.get('filename', '')) + " (" + str(a.get('size', 0)) + " bytes)")
                lines.append("")
            text = "\n".join(lines)
            pdf = _make_simple_pdf(text)
            with open(path, "wb") as fh:
                fh.write(pdf)
            try:
                if os.name == "nt":
                    os.startfile(path, "print")
            except Exception:
                pass
            messagebox.showinfo(lang.t("app_name"), "PDF saved:\n" + path)
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _edit_patient_info(self):
        if getattr(self, "_is_new", False):
            return
        dlg = EditPatientDialog(self, self.patient)
        self.wait_window(dlg)
        if dlg.result:
            try:
                db.update_patient(self.patient_id, name=dlg.result['name'], localitate=dlg.result['localitate'], sex=dlg.result.get('sex', ''), dob=dlg.result.get('dob', ''))
                self.patient = db.get_patient(patient_id=self.patient_id)
                self.name_label.configure(text=self.patient['name'])
                self._refresh_header_info()
                try:
                    self.modified_label.configure(text="Last modified: " + (self.patient.get('updated_at') or 'NA'))
                except Exception:
                    pass
                if self.on_close_callback:
                    self.on_close_callback()
            except Exception as e:
                messagebox.showerror(lang.t("app_name"), str(e))

    def mark_dirty(self):
        if getattr(self, "_is_new", False):
            self._dirty = True
            self.dirty_label.configure(text="Unsaved changes *")
            return
        self._dirty = True
        self.dirty_label.configure(text="Unsaved changes *")

    def _schedule_format(self, txt):
        job = getattr(self, "_fmt_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        try:
            self._fmt_job = self.after(250, lambda t=txt: (utils._apply_inline_formatting(t), setattr(self, "_fmt_job", None)))
        except Exception:
            utils._apply_inline_formatting(txt)

    def is_dirty(self):
        return self._dirty

    def save_if_dirty(self, silent=True):
        """Save pending edits; returns True when something was written."""
        if not getattr(self, "_dirty", False):
            return False
        if getattr(self, "_is_new", False):
            return False
        try:
            self._save_all(silent=silent)
            return True
        except Exception:
            return False

    def _cancel_new(self):
        try:
            app = self.winfo_toplevel()
            if hasattr(app, "_show_placeholder"):
                app._show_placeholder()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _schedule_autosave(self):
        try:
            self.after(30000, self._auto_save)
        except Exception:
            pass

    def _auto_save(self):
        try:
            if getattr(self, "_is_new", False):
                return
            if self._dirty and self.winfo_exists():
                self.dirty_label.configure(text="Saving...")
                self._save_all(silent=True)
        except Exception:
            pass
        self._schedule_autosave()

    # ---- attachments ----
    def _load_attachments(self):
        try:
            for r in self.attach_tree.get_children():
                self.attach_tree.delete(r)
        except Exception:
            pass
        try:
            for a in db.list_attachments(self.patient_id):
                size = a.get('size', 0)
                size_str = (str(round(size / 1024, 1)) + " KB") if size >= 1024 else (str(size) + " B")
                self.attach_tree.insert("", "end", iid=str(a['id']),
                                        values=(a.get('filename', ''), size_str, a.get('added_at', '')))
        except Exception:
            pass

    def _attach_file(self):
        path = filedialog.askopenfilename(title="Attach file", filetypes=[("All files", "*.*")])
        if not path:
            return
        try:
            db.add_attachment(self.patient_id, path)
            self._load_attachments()
            messagebox.showinfo(lang.t("app_name"), "File attached.")
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _open_attachment(self):
        sel = self.attach_tree.selection()
        if not sel:
            messagebox.showinfo(lang.t("app_name"), "Select an attachment.")
            return
        att = db.get_attachment(int(sel[0]))
        if not att:
            return
        path = att.get('stored_path', '')
        if not path or not os.path.exists(path):
            messagebox.showerror(lang.t("app_name"), "File not found.")
            return
        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _delete_attachment(self):
        sel = self.attach_tree.selection()
        if not sel:
            messagebox.showinfo(lang.t("app_name"), "Select an attachment.")
            return
        if not messagebox.askyesno(lang.t("app_name"), "Delete this attachment?"):
            return
        try:
            db.delete_attachment(int(sel[0]))
            self._load_attachments()
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    # ---- history ----
    def _load_history(self):
        try:
            for r in self.hist_tree.get_children():
                self.hist_tree.delete(r)
        except Exception:
            pass
        try:
            for h in db.list_history(self.patient_id):
                oldv = h.get('old_value', '') or ''
                newv = h.get('new_value', '') or ''
                if len(oldv) > 40:
                    oldv = oldv[:37] + "..."
                if len(newv) > 40:
                    newv = newv[:37] + "..."
                self.hist_tree.insert("", "end", values=(h.get('changed_at', ''), h.get('field', ''), oldv, newv))
        except Exception:
            pass

    def _clear_history(self):
        if not messagebox.askyesno(lang.t("app_name"), "Delete all history for this patient?"):
            return
        try:
            db.delete_history(self.patient_id)
            self._load_history()
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))


# ---- edit dialog ----
class EditPatientDialog(ctk.CTkToplevel):
    def __init__(self, master, patient):
        super().__init__(master)
        self.title(lang.t("dlg_edit_patient"))
        self.geometry("400x280")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.result = None
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text=lang.t("label_patient_name") + ":").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.entry_name = ctk.CTkEntry(self)
        self.entry_name.insert(0, patient.get('name', ''))
        self.entry_name.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(self, text=lang.t("label_localitate") + ":").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.entry_loc = ctk.CTkComboBox(self, values=db.get_localities())
        self.entry_loc.set(patient.get('localitate', ''))
        self.entry_loc.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self, text="Sex:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.entry_sex = ctk.CTkComboBox(self, values=["NA", "M", "F"])
        self.entry_sex.set(patient.get('sex', '') or "NA")
        self.entry_sex.grid(row=2, column=1, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self, text="Date of birth (DD.MM.YYYY):").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.entry_dob = ctk.CTkEntry(self)
        self.entry_dob.insert(0, patient.get('dob', '') or '')
        self.entry_dob.grid(row=3, column=1, sticky="ew", padx=10, pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, sticky="e", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text=lang.t("btn_ok"), width=80, command=self._ok).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text=lang.t("btn_cancel"), width=80, command=self.destroy).pack(side="left", padx=2)
        self.entry_name.focus()

    def _ok(self):
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showerror(lang.t("app_name"), lang.t("err_patient_name_required"))
            return
        if not _validate_dob(self.entry_dob.get()):
            messagebox.showerror(lang.t("app_name"), "Date of birth must be DD.MM.YYYY (e.g. 12.05.1990)")
            return
        sex = self.entry_sex.get().strip()
        if sex == "NA":
            sex = ""
        self.result = {"name": name, "localitate": self.entry_loc.get().strip(), "sex": sex, "dob": self.entry_dob.get().strip()}
        self.destroy()

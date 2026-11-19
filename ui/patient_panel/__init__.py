"""Embedded patient file panel (dashboard style) with tabbed sections."""

import datetime
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

import lang
import log
import theme
import utils
from error_ui import report_error
from services.attachment_service import get_attachment_service
from services.history_service import get_history_service
from services.patient_service import get_patient_service

from .attachments_section import AttachmentsSection
from .exercises_section import ExercisesSection
from .outcomes_section import OutcomesSection
from .plan_section import PlanSection
from .sessions_section import SessionsSection

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
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
    )
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(
        b"5 0 obj\n<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream\nendobj\n"
    )
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
    out += (
        b"trailer\n<< /Size "
        + str(len(objects) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_pos).encode()
        + b"\n%%EOF\n"
    )
    return out


class PatientFilePanel(ctk.CTkFrame):
    def __init__(self, master, patient_id, on_close=None, new=False):
        super().__init__(master, fg_color=theme.PANEL, corner_radius=theme.PANEL_RADIUS)
        self.patient_id = None if new else patient_id
        self.on_close_callback = on_close
        self._dirty = False
        self._is_new = bool(new) or (patient_id is None)
        self._rebuilding = False
        self._fmt_job: str | None = None
        self.header_frame = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        if self._is_new:
            self.patient = {
                "name": "",
                "patient_code": "",
                "dob": "",
                "sex": "",
                "localitate": "",
                "diagnostic": "",
                "objective": "",
                "evaluation": "",
                "observation": "",
                "updated_at": "",
            }
        else:
            self.patient = get_patient_service().get_patient(patient_id=patient_id)
            if not self.patient:
                self.destroy()
                return

        # Section controllers own one tab each; the panel stays a coordinator.
        self.plan_section = PlanSection(self)
        self.sessions_section = SessionsSection(self)
        self.exercises_section = ExercisesSection(self)
        self.outcomes_section = OutcomesSection(self)
        self.attachments_section = AttachmentsSection(self)

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

        av = ctk.CTkLabel(
            frame,
            text=_initials(self.patient.get("name", "") or "?"),
            width=theme.AVATAR_SIZE,
            height=theme.AVATAR_SIZE,
            corner_radius=theme.AVATAR_SIZE // 2,
            fg_color=theme.ACCENT,
            text_color=theme.ON_ACCENT,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        av.grid(row=0, column=0, rowspan=4, padx=(0, 12))

        if getattr(self, "_is_new", False):
            # inline editable header
            self.name_entry = ctk.CTkEntry(
                frame,
                placeholder_text=lang.t("ui_patient_name_required_ph"),
                font=ctk.CTkFont(size=16, weight="bold"),
            )
            self.name_entry.grid(row=0, column=1, sticky="ew", pady=(0, 2))
            self.name_entry.insert(0, self.patient.get("name", "") or "")

            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.grid(row=1, column=1, sticky="ew", pady=(0, 2))
            ctk.CTkLabel(
                row,
                text=lang.t("ui_code") + ":",
                font=theme.FONT_SMALL,
                text_color=theme.MUTED,
            ).pack(side="left")
            self.code_label = ctk.CTkLabel(
                row, text="auto", font=theme.FONT_SMALL, text_color=theme.MUTED
            )
            self.code_label.pack(side="left", padx=(4, 12))
            ctk.CTkLabel(
                row, text=lang.t("ui_dob_full"), font=theme.FONT_SMALL, text_color=theme.MUTED
            ).pack(side="left")
            self.dob_entry = ctk.CTkEntry(row, width=110, placeholder_text=lang.t("ui_ddmmyyyy"))
            self.dob_entry.pack(side="left", padx=(4, 12))
            self.dob_entry.insert(0, self.patient.get("dob", "") or "")
            ctk.CTkLabel(
                row,
                text=lang.t("ui_sex") + ":",
                font=theme.FONT_SMALL,
                text_color=theme.MUTED,
            ).pack(side="left")
            self.sex_menu = ctk.CTkOptionMenu(row, values=["", "M", "F"], width=70)
            self.sex_menu.pack(side="left", padx=(4, 12))
            self.sex_menu.set(self.patient.get("sex", "") or "")

            loc_row = ctk.CTkFrame(frame, fg_color="transparent")
            loc_row.grid(row=2, column=1, sticky="ew", pady=(0, 2))
            ctk.CTkLabel(
                loc_row,
                text=lang.t("ui_locality") + ":",
                font=theme.FONT_SMALL,
                text_color=theme.MUTED,
            ).pack(side="left")
            self.loc_entry = ctk.CTkEntry(loc_row, placeholder_text=lang.t("ui_locality"))
            self.loc_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
            self.loc_entry.insert(0, self.patient.get("localitate", "") or "")

            diag = self.patient.get("diagnostic", "") or ""
            first_line = diag.split(chr(10))[0].strip() if diag else ""
            main_diag = (
                utils._strip_inline_formatting(first_line)
                if first_line
                else lang.t("ui_not_applicable")
            )
            diag_lbl = ctk.CTkLabel(
                frame,
                text=lang.t("ui_section_diagnostic") + ": " + main_diag,
                font=theme.FONT_BOLD,
                text_color=theme.ACCENT,
            )
            diag_lbl.grid(row=3, column=1, sticky="w")
            self.diag_header_label = diag_lbl

            self.modified_label = ctk.CTkLabel(
                frame,
                text=lang.t("ui_not_saved_yet"),
                font=theme.FONT_SMALL,
                text_color=theme.MUTED,
            )
            self.modified_label.grid(row=4, column=1, sticky="w", pady=(2, 0))

            btns = ctk.CTkFrame(frame, fg_color="transparent")
            btns.grid(row=0, column=2, rowspan=5, sticky="ne")
            ctk.CTkButton(
                btns,
                text=lang.t("ui_cancel"),
                width=70,
                fg_color=theme.MUTED_BTN,
                hover_color=theme.MUTED_BTN_HOVER,
                command=self._cancel_new,
            ).pack(side="top", padx=2, pady=2)
            return

        # existing patient header (unchanged)
        name_lbl = ctk.CTkLabel(
            frame,
            text=self.patient["name"],
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=theme.TEXT,
        )
        name_lbl.grid(row=0, column=1, sticky="w")
        self.name_label = name_lbl

        na = lang.t("ui_not_applicable")
        dob = self.patient.get("dob", "") or na
        sex = self.patient.get("sex", "") or na
        loc = self.patient.get("localitate", "") or na
        code = self.patient.get("patient_code", "") or na
        info_text = (
            f"{lang.t('ui_code')}: {code}   |   {lang.t('ui_dob')}: {dob}"
            f"   |   {lang.t('ui_sex')}: {sex}   |   {lang.t('ui_locality')}: {loc}"
        )
        info_lbl = ctk.CTkLabel(frame, text=info_text, font=theme.FONT_SUB, text_color=theme.MUTED)
        info_lbl.grid(row=1, column=1, sticky="w")
        self.info_label = info_lbl

        diag = self.patient.get("diagnostic", "") or ""
        first_line = diag.split(chr(10))[0].strip() if diag else ""
        main_diag = utils._strip_inline_formatting(first_line) if first_line else na
        diag_lbl = ctk.CTkLabel(
            frame,
            text=lang.t("ui_section_diagnostic") + ": " + main_diag,
            font=theme.FONT_BOLD,
            text_color=theme.ACCENT,
        )
        diag_lbl.grid(row=2, column=1, sticky="w")
        self.diag_header_label = diag_lbl

        self.modified_label = ctk.CTkLabel(
            frame,
            text=lang.t("ui_last_modified") + " " + (self.patient.get("updated_at") or na),
            font=theme.FONT_SMALL,
            text_color=theme.MUTED,
        )
        self.modified_label.grid(row=3, column=1, sticky="w", pady=(2, 0))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.grid(row=0, column=2, rowspan=4, sticky="e")
        ctk.CTkButton(
            btns,
            text=lang.t("ui_edit"),
            width=70,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_DARK,
            command=self._edit_patient_info,
        ).pack(side="left", padx=2)

    def _refresh_header_info(self):
        if getattr(self, "_is_new", False):
            # update diag label from textbox content
            try:
                txt = getattr(self, "diagnostic_text", None)
                if txt is not None:
                    val = txt.get("1.0", "end-1c").split(chr(10))[0].strip()
                    self.diag_header_label.configure(
                        text=lang.t("ui_section_diagnostic")
                        + ": "
                        + (
                            utils._strip_inline_formatting(val)
                            if val
                            else lang.t("ui_not_applicable")
                        )
                    )
            except Exception:
                log.debug_exc(logger)
            return
        na = lang.t("ui_not_applicable")
        code = self.patient.get("patient_code", "") or na
        dob = self.patient.get("dob", "") or na
        sex = self.patient.get("sex", "") or na
        loc = self.patient.get("localitate", "") or na
        try:
            self.info_label.configure(
                text=(
                    f"{lang.t('ui_code')}: {code}   |   {lang.t('ui_dob')}: {dob}"
                    f"   |   {lang.t('ui_sex')}: {sex}   |   {lang.t('ui_locality')}: {loc}"
                )
            )
        except Exception:
            log.debug_exc(logger)
        diag = self.patient.get("diagnostic", "") or ""
        first_line = diag.split(chr(10))[0].strip() if diag else ""
        main_diag = utils._strip_inline_formatting(first_line) if first_line else na
        try:
            self.diag_header_label.configure(
                text=lang.t("ui_section_diagnostic") + ": " + main_diag
            )
        except Exception:
            log.debug_exc(logger)

    # ---- tabs ----
    def _build_tabs(self):
        if theme.layout() == "stacked":
            self._build_stacked()
            return
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=theme.PANEL,
            corner_radius=14,
            border_width=1,
            border_color=getattr(theme, "BORDER", theme.MUTED),
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=theme.PADDING, pady=(0, 8))

        sections = [
            ("diagnostic", lang.t("ui_section_diagnostic"), theme.SEC_DIAG),
            ("objective", lang.t("ui_section_objective"), theme.SEC_OBJ),
            ("evaluation", lang.t("ui_section_evaluation"), theme.SEC_EVAL),
            ("observation", lang.t("ui_section_observation"), theme.SEC_OBS),
        ]
        self.texts = {}
        self.count_labels = {}
        for field, title, color in sections:
            tab = self.tabview.add(title)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(1, weight=1)
            tb = ctk.CTkFrame(tab, fg_color="transparent")
            tb.grid(row=0, column=0, sticky="ew", pady=(4, 4))
            tooltips = {
                "bold": lang.t("tip_bold"),
                "italic": lang.t("tip_italic"),
                "bullet": lang.t("tip_bullet"),
                "number": lang.t("tip_number"),
            }
            for label, cmd_prefix in [
                ("B", "bold"),
                ("I", "italic"),
                ("\u2022", "bullet"),
                ("1.", "number"),
            ]:
                b = ctk.CTkButton(
                    tb,
                    text=label,
                    width=34,
                    height=26,
                    fg_color=theme.ACCENT,
                    hover_color=theme.ACCENT_DARK,
                    font=theme.FONT_BOLD,
                    command=lambda p=cmd_prefix, f=field: self._toolbar_action(f, p),
                )
                b.pack(side="left", padx=2)
                _attach_tooltip(b, tooltips[cmd_prefix])
            cnt = ctk.CTkLabel(tb, text="", text_color=theme.MUTED, font=theme.FONT_SMALL)
            cnt.pack(side="right", padx=6)
            self.count_labels[field] = cnt

            txt = ctk.CTkTextbox(
                tab,
                corner_radius=0,
                border_width=1,
                border_color=theme.BORDER,
                fg_color=theme.PANEL,
                text_color=theme.TEXT,
                font=theme.FONT_BODY,
                undo=True,
                autoseparators=True,
                maxundo=200,
            )
            txt.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
            val = self.patient.get(field, "") or ""
            txt.insert("1.0", val)
            utils._apply_inline_formatting(txt)
            txt.bind(
                "<KeyRelease>",
                lambda e, f=field, t=txt: (
                    self._on_text_change(f, t),
                    self.mark_dirty(),
                    self._schedule_format(t),
                ),
            )
            setattr(self, field + "_text", txt)
            self._update_count(field, txt)
            self.texts[field] = txt

        self._build_physio_tabs_classic()
        self.attachments_section.build(self.tabview)

        # History tab
        hist_tab = self.tabview.add(lang.t("tab_history"))
        hist_tab.grid_columnconfigure(0, weight=1)
        hist_tab.grid_rowconfigure(0, weight=1)
        hcols = ("changed_at", "field", "old_value", "new_value")
        self.hist_tree = ttk.Treeview(hist_tab, columns=hcols, show="headings", selectmode="browse")
        self.hist_tree.heading("changed_at", text=lang.t("hist_col_when"))
        self.hist_tree.heading("field", text=lang.t("hist_col_field"))
        self.hist_tree.heading("old_value", text=lang.t("hist_col_old"))
        self.hist_tree.heading("new_value", text=lang.t("hist_col_new"))
        self.hist_tree.column("changed_at", width=120)
        self.hist_tree.column("field", width=90)
        self.hist_tree.column("old_value", width=160)
        self.hist_tree.column("new_value", width=160)
        self.hist_tree.grid(row=0, column=0, sticky="nsew", pady=(4, 4))
        hb = ctk.CTkFrame(hist_tab, fg_color="transparent")
        hb.grid(row=1, column=0, sticky="ew", pady=(4, 4))
        ctk.CTkButton(hb, text=lang.t("ui_refresh"), width=80, command=self._load_history).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            hb,
            text=lang.t("ui_clear_history"),
            width=100,
            fg_color=theme.DANGER,
            hover_color=theme.DANGER_HOVER,
            command=self._clear_history,
        ).pack(side="left", padx=2)

    def _build_stacked(self):
        self.tabview = None
        self.sections_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.sections_frame.grid(row=1, column=0, sticky="nsew", padx=theme.PANE_PAD, pady=(0, 8))
        self.sections_frame.grid_columnconfigure(0, weight=1)
        try:
            utils._patch_scrollable(self.sections_frame)
        except Exception:
            log.debug_exc(logger)
        # Group the four text sections into a single browser-like tab view.
        sections = [
            ("diagnostic", lang.t("ui_section_diagnostic")),
            ("objective", lang.t("ui_section_objective")),
            ("evaluation", lang.t("ui_section_evaluation")),
            ("observation", lang.t("ui_section_observation")),
        ]
        self.texts = {}
        self.count_labels = {}
        tooltips = {
            "bold": lang.t("tip_bold"),
            "italic": lang.t("tip_italic"),
            "bullet": lang.t("tip_bullet"),
            "number": lang.t("tip_number"),
        }
        self._sections_tabview = ctk.CTkTabview(
            self.sections_frame,
            fg_color=theme.PANEL,
            corner_radius=14,
            border_width=1,
            border_color=getattr(theme, "BORDER", theme.MUTED),
        )
        self._sections_tabview.pack(fill="x", pady=(0, 12))
        for field, title in sections:
            tab = self._sections_tabview.add(title)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(1, weight=1)

            tb = ctk.CTkFrame(tab, fg_color="transparent")
            tb.grid(row=0, column=0, sticky="ew", pady=(4, 4))
            for label, cmd_prefix in [
                ("B", "bold"),
                ("I", "italic"),
                ("\u2022", "bullet"),
                ("1.", "number"),
            ]:
                b = ctk.CTkButton(
                    tb,
                    text=label,
                    width=34,
                    height=26,
                    fg_color=theme.ACCENT,
                    hover_color=theme.ACCENT_DARK,
                    font=theme.FONT_BOLD,
                    command=lambda p=cmd_prefix, f=field: self._toolbar_action(f, p),
                )
                b.pack(side="left", padx=2)
                _attach_tooltip(b, tooltips[cmd_prefix])
            cnt = ctk.CTkLabel(
                tb, text="", text_color=theme.MUTED, font=theme.FONT_SMALL, fg_color="transparent"
            )
            cnt.pack(side="right", padx=6)
            self.count_labels[field] = cnt

            txt = ctk.CTkTextbox(
                tab,
                corner_radius=8,
                border_width=1,
                border_color=theme.BORDER,
                fg_color=theme.PANEL,
                text_color=theme.TEXT,
                font=theme.FONT_BODY,
                height=110,
                undo=True,
                autoseparators=True,
                maxundo=200,
            )
            txt.grid(row=1, column=0, sticky="nsew", padx=8, pady=(2, 8))
            val = self.patient.get(field, "") or ""
            txt.insert("1.0", val)
            utils._apply_inline_formatting(txt)
            txt.bind(
                "<KeyRelease>",
                lambda e, f=field, t=txt: (
                    self._on_text_change(f, t),
                    self.mark_dirty(),
                    self._schedule_format(t),
                ),
            )
            setattr(self, field + "_text", txt)
            self._update_count(field, txt)
            self.texts[field] = txt

        self._build_physio_tabs_classic(parent=self.sections_frame)

    def _build_physio_tabs_classic(self, parent=None):
        if not getattr(self, "tabview", None):
            if parent is not None:
                # stacked layout: the tabview is one more card in the scroll column,
                # styled like the section cards so it blends (no white band)
                self.tabview = ctk.CTkTabview(
                    parent,
                    fg_color=theme.PANEL,
                    corner_radius=14,
                    border_width=1,
                    border_color=getattr(theme, "BORDER", theme.MUTED),
                    height=400,
                )
                self.tabview.pack(fill="x", pady=(0, 12))
            else:
                self.tabview = ctk.CTkTabview(
                    self,
                    fg_color=theme.PANEL,
                    corner_radius=14,
                    border_width=1,
                    border_color=getattr(theme, "BORDER", theme.MUTED),
                )
                self.tabview.grid(row=2, column=0, sticky="nsew", padx=theme.PANE_PAD, pady=(0, 8))
                self.tabview.grid_columnconfigure(0, weight=1)
        # Each tab owns its widgets and behaviour in a dedicated section.
        self.plan_section.build(self.tabview)
        self.sessions_section.build(self.tabview)
        self.exercises_section.build(self.tabview)
        self.outcomes_section.build(self.tabview)

    # ---- section delegation (keeps the historical panel API) ----
    def _edit_outcome(self) -> None:
        self.outcomes_section.edit()

    def _load_plan(self) -> None:
        self.plan_section.load()

    def _save_plan(self) -> None:
        self.plan_section.save()

    def _load_sessions(self) -> None:
        self.sessions_section.load()

    def _add_session(self) -> None:
        self.sessions_section.add()

    def _delete_session(self) -> None:
        self.sessions_section.delete()

    def _edit_session(self) -> None:
        self.sessions_section.edit()

    def _load_exercises(self) -> None:
        self.exercises_section.load()

    def _add_exercise(self) -> None:
        self.exercises_section.add()

    def _delete_exercise(self) -> None:
        self.exercises_section.delete()

    def _edit_exercise(self) -> None:
        self.exercises_section.edit()

    def _load_outcomes(self) -> None:
        self.outcomes_section.load()

    def _add_outcome(self) -> None:
        self.outcomes_section.add()

    def _delete_outcome(self) -> None:
        self.outcomes_section.delete()

    def _show_editor(self, title, fields, values):
        """Small modal form. Returns a dict of the entered values, or None."""
        result: dict[str, dict[str, str] | None] = {"data": None}
        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.transient(self)
        dlg.grab_set()
        entries = {}
        row = 0
        for key, label, kind, options in fields:
            ctk.CTkLabel(
                dlg, text=label + ":", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w"
            ).grid(row=row, column=0, sticky="w", padx=8, pady=2)
            if kind == "choice":
                var = ctk.StringVar(value=str(values.get(key, "") or ""))
                w = ctk.CTkOptionMenu(dlg, values=options, variable=var, width=180)
                w.grid(row=row, column=1, sticky="w", padx=8, pady=2)
                entries[key] = ("choice", var)
            else:
                w = ctk.CTkEntry(dlg, width=220)
                raw = values.get(key, "")
                if raw is None:
                    raw = ""
                w.insert(0, str(raw))
                w.grid(row=row, column=1, sticky="w", padx=8, pady=2)
                entries[key] = ("text", w)
            row += 1

        def _save():
            data = {}
            for key, (kind, w) in entries.items():
                data[key] = w.get() if kind == "text" else w.get()
            result["data"] = data
            dlg.destroy()

        ctk.CTkButton(dlg, text=lang.t("ui_save"), fg_color=theme.ACCENT, command=_save).grid(
            row=row, column=0, padx=8, pady=8
        )
        ctk.CTkButton(dlg, text=lang.t("ui_cancel"), command=dlg.destroy).grid(
            row=row, column=1, padx=8, pady=8
        )
        self.wait_window(dlg)
        return result["data"]

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
            log.debug_exc(logger)
        try:
            utils._apply_inline_formatting(txt)
        except Exception:
            log.debug_exc(logger)
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
            self.count_labels[field].configure(
                text=lang.t("ui_count_format", chars=chars, lines=lines)
            )
        except Exception:
            log.debug_exc(logger)

    def _update_title_star(self):
        pass

    # ---- footer ----
    def _build_footer(self):
        row = 2 if theme.layout() == "stacked" else 2
        pad = theme.PANE_PAD if theme.layout() == "stacked" else theme.PADDING
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=pad, pady=(0, pad))
        frame.grid_columnconfigure(0, weight=1)
        self.dirty_label = ctk.CTkLabel(
            frame, text="", text_color=theme.DANGER, font=theme.FONT_SMALL
        )
        self.dirty_label.grid(row=0, column=0, sticky="w")
        print_txt = (
            lang.t("ui_print_pdf")
            if theme.layout() == "stacked"
            else "\U0001f5a8  " + lang.t("ui_print_pdf")
        )
        save_txt = (
            lang.t("ui_save_record")
            if theme.layout() == "stacked"
            else "\U0001f4be  " + lang.t("ui_save_record")
        )
        ctk.CTkButton(
            frame,
            text=print_txt,
            width=120,
            height=36,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_DARK,
            font=theme.FONT_BOLD,
            command=self._print_pdf,
        ).grid(row=0, column=1, sticky="e", padx=(0, 6))
        ctk.CTkButton(
            frame,
            text=save_txt,
            width=180,
            height=36,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_DARK,
            font=theme.FONT_BOLD,
            command=self._save_all,
        ).grid(row=0, column=2, sticky="e")

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
                report_error(lang.t("ui_name_required"))
                return
            dob = ""
            try:
                dob = self.dob_entry.get().strip()
            except Exception:
                dob = ""
            if dob and not _validate_dob(dob):
                report_error(lang.t("ui_invalid_date"))
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
            try:
                self.code_entry.get().strip() if hasattr(self, "code_entry") else ""
            except Exception:
                pass
            diag = (
                self.diagnostic_text.get("1.0", "end-1c")
                if hasattr(self, "diagnostic_text")
                else ""
            )
            obj = (
                self.objective_text.get("1.0", "end-1c") if hasattr(self, "objective_text") else ""
            )
            eva = (
                self.evaluation_text.get("1.0", "end-1c")
                if hasattr(self, "evaluation_text")
                else ""
            )
            obs = (
                self.observation_text.get("1.0", "end-1c")
                if hasattr(self, "observation_text")
                else ""
            )
            try:
                pid, _validation = get_patient_service().create_patient(
                    name,
                    loc,
                    sex=sex,
                    dob=dob,
                    diagnostic=diag,
                    objective=obj,
                    evaluation=eva,
                    observation=obs,
                )
                self.patient_id = pid
                self._is_new = False
                self.patient = get_patient_service().get_patient(patient_id=pid)
                # rebuild header as read-only
                self._build_header()
                self._dirty = False
                if not silent:
                    self.dirty_label.configure(text=lang.t("ui_saved"))
                    self.after(
                        2000,
                        lambda: (
                            None
                            if getattr(self, "_rebuilding", False)
                            else utils._safe_configure(self.dirty_label, text="")
                        ),
                    )
                    messagebox.showinfo(lang.t("app_name"), lang.t("msg_saved"))
                else:
                    self.dirty_label.configure(text=lang.t("ui_saved"))
                    self.after(
                        2000,
                        lambda: (
                            None
                            if getattr(self, "_rebuilding", False)
                            else utils._safe_configure(self.dirty_label, text="")
                        ),
                    )
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
                    log.debug_exc(logger)
            except Exception as e:
                report_error(str(e))
            return

        try:
            if not silent:
                self.dirty_label.configure(text=lang.t("ui_saving"))
            get_patient_service().update_patient(
                self.patient_id,
                diagnostic=self.diagnostic_text.get("1.0", "end-1c"),
                objective=self.objective_text.get("1.0", "end-1c"),
                evaluation=self.evaluation_text.get("1.0", "end-1c"),
                observation=self.observation_text.get("1.0", "end-1c"),
            )
            self.patient = get_patient_service().get_patient(patient_id=self.patient_id)
            self._dirty = False
            if silent:
                self.dirty_label.configure(text=lang.t("ui_auto_saved"))
                self.after(
                    2000,
                    lambda: self.dirty_label.configure(text="") if utils._exists(self) else None,
                )
            else:
                self.dirty_label.configure(text=lang.t("ui_saved"))
                self.after(
                    2000,
                    lambda: self.dirty_label.configure(text="") if utils._exists(self) else None,
                )
            self._refresh_header_info()
            try:
                self.modified_label.configure(
                    text=lang.t("ui_last_modified")
                    + " "
                    + (self.patient.get("updated_at") or lang.t("ui_not_applicable"))
                )
            except Exception:
                log.debug_exc(logger)
            if self.on_close_callback:
                self.on_close_callback()
            if not silent:
                messagebox.showinfo(lang.t("app_name"), lang.t("msg_saved"))
        except Exception as e:
            report_error(str(e))

    def _print_pdf(self):
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")],
                title=lang.t("dlg_save_patient_pdf"),
            )
            if not path:
                return
            p = self.patient
            na = lang.t("ui_not_applicable")
            lines = []
            lines.append(lang.t("ui_patient_file"))
            lines.append("=" * 60)
            lines.append(lang.t("ui_name") + ": " + str(p.get("name", "")))
            lines.append(lang.t("ui_code") + ": " + str(p.get("patient_code", "") or na))
            lines.append(lang.t("ui_dob") + ": " + str(p.get("dob", "") or na))
            lines.append(lang.t("ui_sex") + ": " + str(p.get("sex", "") or na))
            lines.append(lang.t("ui_locality") + ": " + str(p.get("localitate", "") or na))
            lines.append(lang.t("ui_last_modified") + " " + str(p.get("updated_at", "") or na))
            lines.append("")
            for fld, title in [
                ("diagnostic", lang.t("ui_section_diagnostic")),
                ("objective", lang.t("ui_section_objective")),
                ("evaluation", lang.t("ui_section_evaluation")),
                ("observation", lang.t("ui_section_observation")),
            ]:
                lines.append(title)
                lines.append("-" * 40)
                txt = getattr(self, fld + "_text")
                content = txt.get("1.0", "end-1c")
                for ln in (content or "").split("\n"):
                    lines.append(ln)
                lines.append("")
            atts = get_attachment_service().list(self.patient_id)
            if atts:
                lines.append(lang.t("tab_attachments"))
                lines.append("-" * 40)
                for a in atts:
                    lines.append(
                        "- "
                        + str(a.get("filename", ""))
                        + " ("
                        + lang.t("ui_bytes", n=a.get("size", 0))
                        + ")"
                    )
                lines.append("")
            text = "\n".join(lines)
            pdf = _make_simple_pdf(text)
            with open(path, "wb") as fh:
                fh.write(pdf)
            try:
                if os.name == "nt":
                    os.startfile(path, "print")
            except Exception:
                log.debug_exc(logger)
            messagebox.showinfo(lang.t("app_name"), lang.t("msg_pdf_saved", path=path))
        except Exception as e:
            report_error(str(e))

    def _edit_patient_info(self):
        if getattr(self, "_is_new", False):
            return
        dlg = EditPatientDialog(self, self.patient)
        self.wait_window(dlg)
        if dlg.result:
            try:
                get_patient_service().update_patient(
                    self.patient_id,
                    name=dlg.result["name"],
                    localitate=dlg.result["localitate"],
                    sex=dlg.result.get("sex", ""),
                    dob=dlg.result.get("dob", ""),
                )
                self.patient = get_patient_service().get_patient(patient_id=self.patient_id)
                self.name_label.configure(text=self.patient["name"])
                self._refresh_header_info()
                try:
                    self.modified_label.configure(
                        text=lang.t("ui_last_modified")
                        + " "
                        + (self.patient.get("updated_at") or lang.t("ui_not_applicable"))
                    )
                except Exception:
                    log.debug_exc(logger)
                if self.on_close_callback:
                    self.on_close_callback()
            except Exception as e:
                report_error(str(e))

    def mark_dirty(self):
        if getattr(self, "_is_new", False):
            self._dirty = True
            self.dirty_label.configure(text=lang.t("ui_unsaved"))
            return
        self._dirty = True
        self.dirty_label.configure(text=lang.t("ui_unsaved"))

    def _schedule_format(self, txt):
        job = getattr(self, "_fmt_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                log.debug_exc(logger)
        try:

            def _format_later(t: str = txt) -> None:
                utils._safe_format(t)
                self._fmt_job = None

            self._fmt_job = self.after(250, _format_later)
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
            log.debug_exc(logger)
        try:
            self.destroy()
        except Exception:
            log.debug_exc(logger)

    def _schedule_autosave(self):
        try:
            self.after(
                30000, lambda: None if getattr(self, "_rebuilding", False) else self._auto_save()
            )
        except Exception:
            log.debug_exc(logger)

    def _auto_save(self):
        try:
            if getattr(self, "_is_new", False):
                return
            if self._dirty and self.winfo_exists():
                self.dirty_label.configure(text=lang.t("ui_saving"))
                self._save_all(silent=True)
        except Exception:
            log.debug_exc(logger)
        self._schedule_autosave()

    # ---- attachments ----
    def _load_attachments(self) -> None:
        self.attachments_section.load()

    def _attach_file(self) -> None:
        self.attachments_section.attach_file()

    def _open_attachment(self) -> None:
        self.attachments_section.open_attachment()

    def _preview_attachment(self) -> None:
        self.attachments_section.preview()

    def _show_preview_image(self, img, title=None) -> None:
        self.attachments_section.show_preview_image(img, title)

    def _delete_attachment(self) -> None:
        self.attachments_section.delete()

    # ---- history ----
    def _load_history(self):
        try:
            for r in self.hist_tree.get_children():
                self.hist_tree.delete(r)
        except Exception:
            log.debug_exc(logger)
        try:
            for h in get_history_service().list(self.patient_id):
                oldv = h.get("old_value", "") or ""
                newv = h.get("new_value", "") or ""
                if len(oldv) > 40:
                    oldv = oldv[:37] + "..."
                if len(newv) > 40:
                    newv = newv[:37] + "..."
                self.hist_tree.insert(
                    "", "end", values=(h.get("changed_at", ""), h.get("field", ""), oldv, newv)
                )
        except Exception:
            log.debug_exc(logger)

    def _clear_history(self):
        if not messagebox.askyesno(lang.t("app_name"), lang.t("confirm_clear_history")):
            return
        try:
            get_history_service().clear(self.patient_id)
            self._load_history()
        except Exception as e:
            report_error(str(e))


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
        ctk.CTkLabel(self, text=lang.t("label_patient_name") + ":").grid(
            row=0, column=0, sticky="w", padx=10, pady=10
        )
        self.entry_name = ctk.CTkEntry(self)
        self.entry_name.insert(0, patient.get("name", ""))
        self.entry_name.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(self, text=lang.t("label_localitate") + ":").grid(
            row=1, column=0, sticky="w", padx=10, pady=5
        )
        self.entry_loc = ctk.CTkComboBox(self, values=get_patient_service().get_localities())
        self.entry_loc.set(patient.get("localitate", ""))
        self.entry_loc.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self, text=lang.t("ui_sex") + ":").grid(
            row=2, column=0, sticky="w", padx=10, pady=5
        )
        self.entry_sex = ctk.CTkComboBox(self, values=["NA", "M", "F"])
        self.entry_sex.set(patient.get("sex", "") or "NA")
        self.entry_sex.grid(row=2, column=1, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self, text=lang.t("ui_dob_full")).grid(
            row=3, column=0, sticky="w", padx=10, pady=5
        )
        self.entry_dob = ctk.CTkEntry(self)
        self.entry_dob.insert(0, patient.get("dob", "") or "")
        self.entry_dob.grid(row=3, column=1, sticky="ew", padx=10, pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, sticky="e", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text=lang.t("btn_ok"), width=80, command=self._ok).pack(
            side="left", padx=2
        )
        ctk.CTkButton(btn_frame, text=lang.t("btn_cancel"), width=80, command=self.destroy).pack(
            side="left", padx=2
        )
        self.entry_name.focus()

    def _ok(self):
        name = self.entry_name.get().strip()
        if not name:
            report_error(lang.t("err_patient_name_required"))
            return
        if not _validate_dob(self.entry_dob.get()):
            report_error(lang.t("err_dob_format"))
            return
        sex = self.entry_sex.get().strip()
        if sex == "NA":
            sex = ""
        self.result = {
            "name": name,
            "localitate": self.entry_loc.get().strip(),
            "sex": sex,
            "dob": self.entry_dob.get().strip(),
        }
        self.destroy()

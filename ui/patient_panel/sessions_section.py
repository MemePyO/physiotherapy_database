"""Sessions tab for the patient file panel."""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

import lang
import theme
from error_ui import report_error
from services.physio_service import SESSION_STATUSES, get_physio_service

from .base import EditorField, TabSection

_COLUMNS = (
    ("no", "ses_col_no", 40),
    ("date", "ses_col_date", 90),
    ("dur", "ses_col_min", 50),
    ("vas", "ses_col_vas", 110),
    ("status", "ses_col_status", 90),
    ("modalities", "ses_col_modalities", 120),
    ("notes", "ses_col_notes", 140),
)

_EDITOR_FIELDS = (
    ("session_no", "ses_no", "text", None),
    ("date", "ses_date", "text", None),
    ("duration_min", "ses_duration", "text", None),
    ("pain_before", "ses_pain_before", "text", None),
    ("pain_after", "ses_pain_after", "text", None),
    ("status", "ses_col_status", "choice", SESSION_STATUSES),
    ("modalities", "ses_modalities", "text", None),
    ("exercises", "ses_exercises", "text", None),
    ("notes", "ses_col_notes", "text", None),
)


def _editor_fields() -> tuple[EditorField, ...]:
    return tuple((key, lang.t(label), kind, opts) for key, label, kind, opts in _EDITOR_FIELDS)


class SessionsSection(TabSection):
    """Builds, lists and edits physiotherapy sessions."""

    def build(self, tabview: ctk.CTkTabview) -> None:
        panel = self.panel
        ses_tab = tabview.add(lang.t("tab_sessions"))
        ses_tab.grid_columnconfigure(0, weight=1)
        ses_tab.grid_rowconfigure(0, weight=1)
        panel.ses_tree = ttk.Treeview(
            ses_tab, columns=[c for c, _, _ in _COLUMNS], show="headings", selectmode="browse"
        )
        for c, title_key, w in _COLUMNS:
            panel.ses_tree.heading(c, text=lang.t(title_key))
            panel.ses_tree.column(c, width=w)
        panel.ses_tree.grid(row=0, column=0, sticky="nsew", pady=(4, 4))
        sx = ttk.Scrollbar(ses_tab, orient="horizontal", command=panel.ses_tree.xview)
        panel.ses_tree.configure(xscrollcommand=sx.set)
        sx.grid(row=1, column=0, sticky="ew")
        sb = ctk.CTkFrame(ses_tab, fg_color="transparent")
        sb.grid(row=2, column=0, sticky="ew", pady=4)
        ctk.CTkButton(
            sb,
            text=lang.t("ses_add"),
            width=120,
            fg_color=theme.ACCENT,
            command=self.add,
        ).pack(side="left", padx=2)
        ctk.CTkButton(sb, text=lang.t("ses_edit"), width=90, command=self.edit).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            sb,
            text=lang.t("ui_delete"),
            width=80,
            fg_color=theme.DANGER,
            command=self.delete,
        ).pack(side="left", padx=2)
        self.load()

    def load(self) -> None:
        panel = self.panel
        try:
            for row in panel.ses_tree.get_children():
                panel.ses_tree.delete(row)
            for s in get_physio_service().list_sessions(panel.patient_id):
                vas = "{}→{}".format(s.get("pain_before", 0), s.get("pain_after", 0))
                panel.ses_tree.insert(
                    "",
                    "end",
                    iid=str(s["id"]),
                    values=(
                        s.get("session_no", ""),
                        s.get("date", ""),
                        s.get("duration_min", ""),
                        vas,
                        s.get("status", ""),
                        s.get("modalities", ""),
                        s.get("notes", ""),
                    ),
                )
        except Exception:
            pass

    def add(self) -> None:
        panel = self.panel
        try:
            if not self.require_patient():
                return
            from dialogs.input_dialog import ask_string

            date = ask_string(panel, lang.t("ses_new_title"), lang.t("ses_new_prompt"))
            if not date:
                return
            get_physio_service().add_session(panel.patient_id, date=date, status="done")
            self.load()
            self.info(lang.t("ses_added"))
        except Exception as e:
            report_error(str(e))

    def delete(self) -> None:
        panel = self.panel
        sel = panel.ses_tree.selection()
        if not sel:
            self.info(lang.t("ses_select"))
            return
        if not self.confirm(lang.t("ses_confirm_delete")):
            return
        try:
            get_physio_service().delete_session(int(sel[0]))
            self.load()
        except Exception as e:
            report_error(str(e))

    def edit(self) -> None:
        panel = self.panel
        sel = panel.ses_tree.selection()
        if not sel:
            self.info(lang.t("ses_select"))
            return
        sid = int(sel[0])
        rows = [s for s in get_physio_service().list_sessions(panel.patient_id) if s["id"] == sid]
        if not rows:
            return
        s = rows[0]
        values = {k: s.get(k, "") for k, *_ in _EDITOR_FIELDS}
        raw = self.show_editor(lang.t("ses_edit_title"), _editor_fields(), values)
        if not raw:
            return
        data: dict[str, object] = dict(raw)
        try:
            data["session_no"] = (
                int(str(data["session_no"])) if str(data["session_no"]).strip() else 1
            )
            data["duration_min"] = (
                int(str(data["duration_min"])) if str(data["duration_min"]).strip() else 30
            )
            data["pain_before"] = (
                float(str(data["pain_before"])) if str(data["pain_before"]).strip() else 0
            )
            data["pain_after"] = (
                float(str(data["pain_after"])) if str(data["pain_after"]).strip() else 0
            )
            get_physio_service().update_session(sid, **data)
            self.load()
        except Exception as e:
            report_error(str(e))


__all__ = ["SessionsSection"]

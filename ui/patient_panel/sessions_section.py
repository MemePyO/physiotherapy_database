"""Sessions tab for the patient file panel."""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

import theme
from error_ui import report_error
from services.physio_service import SESSION_STATUSES, get_physio_service

from .base import TabSection

_COLUMNS = (
    ("no", "Nr.", 40),
    ("date", "Data", 90),
    ("dur", "Min", 50),
    ("vas", "VAS înainte→după", 110),
    ("status", "Status", 90),
    ("modalities", "Modalități", 120),
    ("notes", "Note", 140),
)

_EDITOR_FIELDS = (
    ("session_no", "Nr. sesiune", "text", None),
    ("date", "Data (DD.MM.YYYY)", "text", None),
    ("duration_min", "Durată (min)", "text", None),
    ("pain_before", "VAS înainte", "text", None),
    ("pain_after", "VAS după", "text", None),
    ("status", "Status", "choice", SESSION_STATUSES),
    ("modalities", "Modalități", "text", None),
    ("exercises", "Exerciții", "text", None),
    ("notes", "Note", "text", None),
)


class SessionsSection(TabSection):
    """Builds, lists and edits physiotherapy sessions."""

    def build(self, tabview: ctk.CTkTabview) -> None:
        panel = self.panel
        ses_tab = tabview.add("Sesiuni")
        ses_tab.grid_columnconfigure(0, weight=1)
        ses_tab.grid_rowconfigure(0, weight=1)
        panel.ses_tree = ttk.Treeview(
            ses_tab, columns=[c for c, _, _ in _COLUMNS], show="headings", selectmode="browse"
        )
        for c, t, w in _COLUMNS:
            panel.ses_tree.heading(c, text=t)
            panel.ses_tree.column(c, width=w)
        panel.ses_tree.grid(row=0, column=0, sticky="nsew", pady=(4, 4))
        sx = ttk.Scrollbar(ses_tab, orient="horizontal", command=panel.ses_tree.xview)
        panel.ses_tree.configure(xscrollcommand=sx.set)
        sx.grid(row=1, column=0, sticky="ew")
        sb = ctk.CTkFrame(ses_tab, fg_color="transparent")
        sb.grid(row=2, column=0, sticky="ew", pady=4)
        ctk.CTkButton(
            sb, text="Adaugă sesiune", width=120, fg_color=theme.ACCENT, command=self.add
        ).pack(side="left", padx=2)
        ctk.CTkButton(sb, text="Editează", width=90, command=self.edit).pack(side="left", padx=2)
        ctk.CTkButton(sb, text="Șterge", width=80, fg_color="#c0392b", command=self.delete).pack(
            side="left", padx=2
        )
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

            date = ask_string(panel, "Sesiune nouă", "Data (DD.MM.YYYY):")
            if not date:
                return
            get_physio_service().add_session(panel.patient_id, date=date, status="done")
            self.load()
            self.info("Sesiune adăugată.")
        except Exception as e:
            report_error(str(e))

    def delete(self) -> None:
        panel = self.panel
        sel = panel.ses_tree.selection()
        if not sel:
            self.info("Selectați o sesiune.")
            return
        if not self.confirm("Ștergeți sesiunea?"):
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
            self.info("Selectați o sesiune.")
            return
        sid = int(sel[0])
        rows = [s for s in get_physio_service().list_sessions(panel.patient_id) if s["id"] == sid]
        if not rows:
            return
        s = rows[0]
        values = {k: s.get(k, "") for k, *_ in _EDITOR_FIELDS}
        data = self.show_editor("Editează sesiune", _EDITOR_FIELDS, values)
        if not data:
            return
        try:
            data["session_no"] = int(data["session_no"]) if str(data["session_no"]).strip() else 1
            data["duration_min"] = (
                int(data["duration_min"]) if str(data["duration_min"]).strip() else 30
            )
            data["pain_before"] = (
                float(data["pain_before"]) if str(data["pain_before"]).strip() else 0
            )
            data["pain_after"] = float(data["pain_after"]) if str(data["pain_after"]).strip() else 0
            get_physio_service().update_session(sid, **data)
            self.load()
        except Exception as e:
            report_error(str(e))


__all__ = ["SessionsSection"]

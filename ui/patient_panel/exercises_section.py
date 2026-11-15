"""Home exercise programme (HEP) tab for the patient file panel."""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

import theme
from error_ui import report_error
from services.physio_service import get_physio_service

from .base import TabSection

_COLUMNS = (
    ("name", "Exercițiu", 160),
    ("sets", "Serii", 50),
    ("reps", "Repetări", 70),
    ("hold", "Menținere(s)", 90),
    ("freq", "Frecvență", 100),
    ("assigned", "Data", 90),
    ("notes", "Note", 140),
)

_EDITOR_FIELDS = (
    ("name", "Nume exercițiu", "text", None),
    ("sets", "Serii", "text", None),
    ("reps", "Repetări", "text", None),
    ("hold_sec", "Menținere (s)", "text", None),
    ("frequency", "Frecvență", "text", None),
    ("assigned_date", "Data atribuire", "text", None),
    ("notes", "Note", "text", None),
)


class ExercisesSection(TabSection):
    """Builds, lists and edits home exercises."""

    def build(self, tabview: ctk.CTkTabview) -> None:
        panel = self.panel
        hep_tab = tabview.add("Exerciții (HEP)")
        hep_tab.grid_columnconfigure(0, weight=1)
        hep_tab.grid_rowconfigure(0, weight=1)
        panel.hep_tree = ttk.Treeview(
            hep_tab, columns=[c for c, _, _ in _COLUMNS], show="headings", selectmode="browse"
        )
        for c, t, w in _COLUMNS:
            panel.hep_tree.heading(c, text=t)
            panel.hep_tree.column(c, width=w)
        panel.hep_tree.grid(row=0, column=0, sticky="nsew", pady=(4, 4))
        hx = ttk.Scrollbar(hep_tab, orient="horizontal", command=panel.hep_tree.xview)
        panel.hep_tree.configure(xscrollcommand=hx.set)
        hx.grid(row=1, column=0, sticky="ew")
        hb = ctk.CTkFrame(hep_tab, fg_color="transparent")
        hb.grid(row=2, column=0, sticky="ew", pady=4)
        ctk.CTkButton(
            hb,
            text="Adaugă exercițiu",
            width=130,
            fg_color=theme.ACCENT,
            command=self.add,
        ).pack(side="left", padx=2)
        ctk.CTkButton(hb, text="Editează", width=90, command=self.edit).pack(side="left", padx=2)
        ctk.CTkButton(hb, text="Șterge", width=80, fg_color="#c0392b", command=self.delete).pack(
            side="left", padx=2
        )
        self.load()

    def load(self) -> None:
        panel = self.panel
        try:
            for row in panel.hep_tree.get_children():
                panel.hep_tree.delete(row)
            for e in get_physio_service().list_exercises(panel.patient_id):
                panel.hep_tree.insert(
                    "",
                    "end",
                    iid=str(e["id"]),
                    values=(
                        e.get("name", ""),
                        e.get("sets", ""),
                        e.get("reps", ""),
                        e.get("hold_sec", ""),
                        e.get("frequency", ""),
                        e.get("assigned_date", ""),
                        e.get("notes", ""),
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

            name = ask_string(panel, "Exercițiu nou", "Nume exercițiu:")
            if not name:
                return
            get_physio_service().add_exercise(panel.patient_id, name=name)
            self.load()
        except Exception as e:
            report_error(str(e))

    def delete(self) -> None:
        panel = self.panel
        sel = panel.hep_tree.selection()
        if not sel:
            self.info("Selectați un exercițiu.")
            return
        if not self.confirm("Ștergeți exercițiul?"):
            return
        try:
            get_physio_service().delete_exercise(int(sel[0]))
            self.load()
        except Exception as e:
            report_error(str(e))

    def edit(self) -> None:
        panel = self.panel
        sel = panel.hep_tree.selection()
        if not sel:
            self.info("Selectați un exercițiu.")
            return
        eid = int(sel[0])
        rows = [e for e in get_physio_service().list_exercises(panel.patient_id) if e["id"] == eid]
        if not rows:
            return
        e = rows[0]
        values = {k: e.get(k, "") for k, *_ in _EDITOR_FIELDS}
        data = self.show_editor("Editează exercițiu", _EDITOR_FIELDS, values)
        if not data:
            return
        try:
            data["sets"] = int(data["sets"]) if str(data["sets"]).strip() else 3
            data["reps"] = int(data["reps"]) if str(data["reps"]).strip() else 10
            data["hold_sec"] = int(data["hold_sec"]) if str(data["hold_sec"]).strip() else 0
            get_physio_service().update_exercise(eid, **data)
            self.load()
        except Exception as e:
            report_error(str(e))


__all__ = ["ExercisesSection"]

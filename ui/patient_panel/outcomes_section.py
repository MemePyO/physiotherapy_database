"""Outcome measures (VAS/NRS) tab for the patient file panel."""

from __future__ import annotations

import datetime
from tkinter import ttk

import customtkinter as ctk

import theme
from error_ui import report_error
from services.physio_service import get_physio_service

from .base import TabSection

_COLUMNS = (
    ("date", "Data", 90),
    ("measure", "Măsură", 80),
    ("value", "Valoare", 70),
    ("notes", "Note", 160),
)

_EDITOR_FIELDS = (
    ("measure", "Măsură", "choice", ["VAS", "NRS"]),
    ("value", "Valoare", "text", None),
    ("date", "Data (DD.MM.YYYY)", "text", None),
    ("notes", "Note", "text", None),
)


class OutcomesSection(TabSection):
    """Builds, lists and edits outcome measures."""

    def build(self, tabview: ctk.CTkTabview) -> None:
        panel = self.panel
        out_tab = tabview.add("Tests")
        out_tab.grid_columnconfigure(0, weight=1)
        out_tab.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(out_tab, text="VAS", font=theme.FONT_BOLD, text_color=theme.TEXT).grid(
            row=0, column=0, sticky="w", padx=6, pady=(4, 2)
        )
        panel.out_tree = ttk.Treeview(
            out_tab, columns=[c for c, _, _ in _COLUMNS], show="headings", selectmode="browse"
        )
        for c, t, w in _COLUMNS:
            panel.out_tree.heading(c, text=t)
            panel.out_tree.column(c, width=w)
        panel.out_tree.grid(row=1, column=0, sticky="nsew", pady=(2, 4))
        ob = ctk.CTkFrame(out_tab, fg_color="transparent")
        ob.grid(row=2, column=0, sticky="ew", pady=4)
        ctk.CTkButton(
            ob,
            text="Adaugă măsurătoare",
            width=150,
            fg_color=theme.ACCENT,
            command=self.add,
        ).pack(side="left", padx=2)
        ctk.CTkButton(ob, text="Editează", width=90, command=self.edit).pack(side="left", padx=2)
        ctk.CTkButton(ob, text="Șterge", width=80, fg_color="#c0392b", command=self.delete).pack(
            side="left", padx=2
        )
        self.load()

    def load(self) -> None:
        panel = self.panel
        try:
            for row in panel.out_tree.get_children():
                panel.out_tree.delete(row)
            for o in get_physio_service().list_outcomes(panel.patient_id):
                panel.out_tree.insert(
                    "",
                    "end",
                    iid=str(o["id"]),
                    values=(
                        o.get("date", ""),
                        o.get("measure", ""),
                        o.get("value", ""),
                        o.get("notes", ""),
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

            val = ask_string(panel, "Măsurătoare nouă", "Valoare VAS (0-10):")
            if val is None:
                return
            try:
                v = float(val)
            except ValueError:
                report_error("Valoare invalidă.")
                return
            if v < 0 or v > 10:
                report_error("VAS trebuie 0-10.")
                return
            get_physio_service().add_outcome(
                panel.patient_id, "VAS", v, datetime.datetime.now().strftime("%d.%m.%Y")
            )
            self.load()
        except Exception as e:
            report_error(str(e))

    def delete(self) -> None:
        panel = self.panel
        sel = panel.out_tree.selection()
        if not sel:
            self.info("Selectați o măsurătoare.")
            return
        if not self.confirm("Ștergeți măsurătoarea?"):
            return
        try:
            get_physio_service().delete_outcome(int(sel[0]))
            self.load()
        except Exception as e:
            report_error(str(e))

    def edit(self) -> None:
        panel = self.panel
        sel = panel.out_tree.selection()
        if not sel:
            self.info("Selectați o măsurătoare.")
            return
        oid = int(sel[0])
        rows = [o for o in get_physio_service().list_outcomes(panel.patient_id) if o["id"] == oid]
        if not rows:
            return
        o = rows[0]
        values = {k: o.get(k, "") for k, *_ in _EDITOR_FIELDS}
        raw = self.show_editor("Editează măsurătoare", _EDITOR_FIELDS, values)
        if not raw:
            return
        data: dict[str, object] = dict(raw)
        try:
            data["value"] = float(str(data["value"])) if str(data["value"]).strip() else 0
            get_physio_service().update_outcome(oid, **data)
            self.load()
        except Exception as e:
            report_error(str(e))


__all__ = ["OutcomesSection"]

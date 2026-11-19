"""Home exercise programme (HEP) tab for the patient file panel."""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

import lang
import theme
from error_ui import report_error
from services.physio_service import get_physio_service

from .base import EditorField, TabSection

_COLUMNS = (
    ("name", "ex_col_name", 160),
    ("sets", "ex_col_sets", 50),
    ("reps", "ex_col_reps", 70),
    ("hold", "ex_col_hold", 90),
    ("freq", "ex_col_freq", 100),
    ("assigned", "ex_col_assigned", 90),
    ("notes", "ex_col_notes", 140),
)

_EDITOR_FIELDS = (
    ("name", "ex_name", "text", None),
    ("sets", "ex_sets", "text", None),
    ("reps", "ex_reps", "text", None),
    ("hold_sec", "ex_hold", "text", None),
    ("frequency", "ex_frequency", "text", None),
    ("assigned_date", "ex_assigned", "text", None),
    ("notes", "ex_notes", "text", None),
)


def _editor_fields() -> tuple[EditorField, ...]:
    return tuple((key, lang.t(label), kind, opts) for key, label, kind, opts in _EDITOR_FIELDS)


class ExercisesSection(TabSection):
    """Builds, lists and edits home exercises."""

    def build(self, tabview: ctk.CTkTabview) -> None:
        panel = self.panel
        hep_tab = tabview.add(lang.t("tab_exercises"))
        hep_tab.grid_columnconfigure(0, weight=1)
        hep_tab.grid_rowconfigure(0, weight=1)
        panel.hep_tree = ttk.Treeview(
            hep_tab, columns=[c for c, _, _ in _COLUMNS], show="headings", selectmode="browse"
        )
        for c, title_key, w in _COLUMNS:
            panel.hep_tree.heading(c, text=lang.t(title_key))
            panel.hep_tree.column(c, width=w)
        panel.hep_tree.grid(row=0, column=0, sticky="nsew", pady=(4, 4))
        hx = ttk.Scrollbar(hep_tab, orient="horizontal", command=panel.hep_tree.xview)
        panel.hep_tree.configure(xscrollcommand=hx.set)
        hx.grid(row=1, column=0, sticky="ew")
        hb = ctk.CTkFrame(hep_tab, fg_color="transparent")
        hb.grid(row=2, column=0, sticky="ew", pady=4)
        ctk.CTkButton(
            hb,
            text=lang.t("ex_add"),
            width=130,
            fg_color=theme.ACCENT,
            command=self.add,
        ).pack(side="left", padx=2)
        ctk.CTkButton(hb, text=lang.t("ex_edit"), width=90, command=self.edit).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            hb,
            text=lang.t("ui_delete"),
            width=80,
            fg_color=theme.DANGER,
            command=self.delete,
        ).pack(side="left", padx=2)
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

            name = ask_string(panel, lang.t("ex_new_title"), lang.t("ex_new_prompt"))
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
            self.info(lang.t("ex_select"))
            return
        if not self.confirm(lang.t("ex_confirm_delete")):
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
            self.info(lang.t("ex_select"))
            return
        eid = int(sel[0])
        rows = [e for e in get_physio_service().list_exercises(panel.patient_id) if e["id"] == eid]
        if not rows:
            return
        e = rows[0]
        values = {k: e.get(k, "") for k, *_ in _EDITOR_FIELDS}
        raw = self.show_editor(lang.t("ex_edit_title"), _editor_fields(), values)
        if not raw:
            return
        data: dict[str, object] = dict(raw)
        try:
            data["sets"] = int(str(data["sets"])) if str(data["sets"]).strip() else 3
            data["reps"] = int(str(data["reps"])) if str(data["reps"]).strip() else 10
            data["hold_sec"] = int(str(data["hold_sec"])) if str(data["hold_sec"]).strip() else 0
            get_physio_service().update_exercise(eid, **data)
            self.load()
        except Exception as e:
            report_error(str(e))


__all__ = ["ExercisesSection"]

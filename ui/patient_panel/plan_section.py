"""Treatment-plan tab for the patient file panel."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

import lang
import theme
from error_ui import report_error
from services.physio_service import BODY_REGIONS, SIDES, get_physio_service

from .base import TabSection

_PLAN_FIELDS = (
    ("diagnosis_code", "Cod diagnostic (ICD)"),
    ("body_region", "Regiune corporală"),
    ("side", "Laterality"),
    ("prescribed_sessions", "Ședințe prescrise"),
    ("start_date", "Data început"),
    ("end_date", "Data sfârșit"),
)


class PlanSection(TabSection):
    """Builds and persists the treatment plan tab."""

    def build(self, tabview: ctk.CTkTabview) -> None:
        panel = self.panel
        plan_tab = tabview.add("Plan tratament")
        plan_tab.grid_columnconfigure(1, weight=1)
        panel.plan_entries = {}
        r = 0
        for key, label in _PLAN_FIELDS:
            ctk.CTkLabel(
                plan_tab, text=label + ":", font=theme.FONT_SMALL, text_color=theme.MUTED
            ).grid(row=r, column=0, sticky="w", padx=6, pady=2)
            w: ctk.CTkBaseClass
            if key == "body_region":
                w = ctk.CTkOptionMenu(plan_tab, values=BODY_REGIONS, width=180)
            elif key == "side":
                w = ctk.CTkOptionMenu(plan_tab, values=SIDES, width=120)
            else:
                w = ctk.CTkEntry(plan_tab, width=180)
            w.grid(row=r, column=1, sticky="w", padx=6, pady=2)
            panel.plan_entries[key] = w
            r += 1
        ctk.CTkLabel(
            plan_tab, text="Obiective:", font=theme.FONT_SMALL, text_color=theme.MUTED
        ).grid(row=r, column=0, sticky="nw", padx=6, pady=2)
        panel.plan_goals = ctk.CTkTextbox(plan_tab, height=60, font=theme.FONT_BODY)
        panel.plan_goals.grid(row=r, column=1, sticky="ew", padx=6, pady=2)
        r += 1
        ctk.CTkLabel(
            plan_tab, text="Contraindicații:", font=theme.FONT_SMALL, text_color=theme.MUTED
        ).grid(row=r, column=0, sticky="nw", padx=6, pady=2)
        panel.plan_contra = ctk.CTkTextbox(plan_tab, height=40, font=theme.FONT_BODY)
        panel.plan_contra.grid(row=r, column=1, sticky="ew", padx=6, pady=2)
        r += 1
        ctk.CTkLabel(plan_tab, text="Note:", font=theme.FONT_SMALL, text_color=theme.MUTED).grid(
            row=r, column=0, sticky="nw", padx=6, pady=2
        )
        panel.plan_notes = ctk.CTkTextbox(plan_tab, height=40, font=theme.FONT_BODY)
        panel.plan_notes.grid(row=r, column=1, sticky="ew", padx=6, pady=2)
        r += 1
        ctk.CTkButton(
            plan_tab, text="Salvează planul", fg_color=theme.ACCENT, command=self.save
        ).grid(row=r, column=1, sticky="w", padx=6, pady=6)

        self.load()

    def load(self) -> None:
        panel = self.panel
        try:
            plan = get_physio_service().get_plan(panel.patient_id)
            if not plan:
                return
            for key, w in getattr(panel, "plan_entries", {}).items():
                val = plan.get(key)
                if val is None:
                    val = ""
                if isinstance(w, ctk.CTkOptionMenu):
                    w.set(str(val))
                else:
                    w.delete(0, "end")
                    w.insert(0, str(val))
            panel.plan_goals.delete("1.0", "end")
            panel.plan_goals.insert("1.0", plan.get("goals", "") or "")
            panel.plan_contra.delete("1.0", "end")
            panel.plan_contra.insert("1.0", plan.get("contraindications", "") or "")
            panel.plan_notes.delete("1.0", "end")
            panel.plan_notes.insert("1.0", plan.get("notes", "") or "")
        except Exception:
            pass

    def save(self) -> None:
        panel = self.panel
        try:
            fields = {}
            for key, w in getattr(panel, "plan_entries", {}).items():
                if isinstance(w, ctk.CTkOptionMenu):
                    fields[key] = w.get()
                else:
                    fields[key] = w.get().strip()
            fields["goals"] = panel.plan_goals.get("1.0", "end-1c")
            fields["contraindications"] = panel.plan_contra.get("1.0", "end-1c")
            fields["notes"] = panel.plan_notes.get("1.0", "end-1c")
            # prescribed_sessions int
            try:
                fields["prescribed_sessions"] = int(fields.get("prescribed_sessions") or 0)
            except ValueError:
                fields["prescribed_sessions"] = 0
            get_physio_service().upsert_plan(panel.patient_id, **fields)
            messagebox.showinfo(lang.t("app_name"), "Plan salvat.")
        except Exception as e:
            report_error(str(e))


__all__ = ["PlanSection"]

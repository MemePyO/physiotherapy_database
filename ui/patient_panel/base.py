"""Shared infrastructure for the patient-file panel sections.

Each section owns one tab (plan, sessions, exercises, outcomes, attachments)
and receives the :class:`~ui.patient_panel.PatientFilePanel` coordinator.  The
panel keeps thin delegation methods so existing call sites and tests continue
to work unchanged.
"""

from __future__ import annotations

import typing as t

import customtkinter as ctk

if t.TYPE_CHECKING:
    from . import PatientFilePanel

# Editor field description: (key, label, kind, options)
EditorField = tuple[str, str, str, t.Sequence[str] | None]
EditorValues = t.Mapping[str, t.Any]


class PanelSection:
    """Base class for a single patient-panel tab.

    The base only holds the coordinator reference and the few helpers that
    every section needs.  It deliberately does not create widgets: layout is
    owned by each concrete section so the visual structure stays explicit.
    """

    def __init__(self, panel: PatientFilePanel) -> None:
        self.panel = panel

    @property
    def patient_id(self) -> int | None:
        return self.panel.patient_id

    def show_editor(
        self,
        title: str,
        fields: t.Sequence[EditorField],
        values: EditorValues,
    ) -> dict[str, str] | None:
        """Open the shared modal editor owned by the coordinator."""
        return self.panel._show_editor(title, fields, values)

    # Common confirmation helper used by destructive section actions.
    def confirm(self, question: str) -> bool:
        from tkinter import messagebox

        import lang

        return bool(messagebox.askyesno(lang.t("app_name"), question))

    # Common information helper.
    def info(self, message: str) -> None:
        from tkinter import messagebox

        import lang

        messagebox.showinfo(lang.t("app_name"), message)

    def require_patient(self) -> bool:
        """Return ``False`` (after informing the user) for an unsaved record."""
        if self.patient_id is None:
            self.info("Salvați mai întâi pacientul.")
            return False
        return True


class TabSection(PanelSection):
    """A section that renders itself into a ``CTkTabview`` page."""

    def build(self, tabview: ctk.CTkTabview) -> None:  # pragma: no cover - interface
        raise NotImplementedError


__all__ = ["EditorField", "EditorValues", "PanelSection", "TabSection"]
